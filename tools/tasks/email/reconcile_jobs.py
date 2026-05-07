from celery import shared_task
from celery.result import AsyncResult
from django.utils import timezone
from datetime import timedelta

from tools import constants
from tools.models import DataSourceJob

BATCH_LIMIT = 1000
ORPHAN_THRESHOLD = timedelta(minutes=60)


def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


@shared_task(
    bind=True,
    acks_late=True,
    queue="maintenance",
)
def reconcile_bulk_jobs(self):
    """
    Marks stale INPROGRESS jobs as ERROR.

    Strategy:
      - If finalize_task_id is set and its Celery state is FAILURE → mark ERROR.
      - If finalize_task_id is set and its state is SUCCESS but job is still
        INPROGRESS → mark ERROR (finalize ran but didn't update the job).
      - If finalize_task_id is NULL and dispatch completed more than
        ORPHAN_THRESHOLD ago → dispatch chord was lost; mark ERROR.

    FIX: Previously this checked dispatch_task_id state. dispatch_task_id goes
    to SUCCESS immediately after the chord is created, so every in-progress job
    would be incorrectly marked ERROR within seconds of starting.
    We now check finalize_task_id instead, which only reaches SUCCESS/FAILURE
    when the actual finalize step completes.
    """
    now = timezone.now()
    error_job_ids = []

    # --- Case 1: finalize task present, check its state ---
    jobs_with_finalize = (
        DataSourceJob.objects
        .filter(
            source_type=constants.BULK,
            status=DataSourceJob.INPROGRESS,
            finalize_task_id__isnull=False,
        )
        .only("uuid", "finalize_task_id")
    )

    # FIX: Count before consuming the iterator so the return value is accurate.
    total_checked = jobs_with_finalize.count()

    for job in jobs_with_finalize.iterator(chunk_size=BATCH_LIMIT):
        result = AsyncResult(job.finalize_task_id)
        if result.state in ("FAILURE", "REVOKED"):
            error_job_ids.append(job.uuid)
        elif result.state == "SUCCESS":
            # Finalize ran but job status was never updated — treat as error
            error_job_ids.append(job.uuid)

    # --- Case 2: no finalize_task_id but dispatch is old (orphaned chord) ---
    orphan_jobs = (
        DataSourceJob.objects
        .filter(
            source_type=constants.BULK,
            status=DataSourceJob.INPROGRESS,
            finalize_task_id__isnull=True,
            dispatch_task_id__isnull=False,
            dispatched_at__lt=now - ORPHAN_THRESHOLD,
        )
        .only("uuid", "dispatch_task_id")
    )

    total_checked += orphan_jobs.count()

    for job in orphan_jobs.iterator(chunk_size=BATCH_LIMIT):
        result = AsyncResult(job.dispatch_task_id)
        # Dispatch task finished but chord never registered a finalize task id
        if result.state == "SUCCESS":
            error_job_ids.append(job.uuid)

    # --- Bulk-update all stale jobs ---
    for batch_ids in chunked(error_job_ids, BATCH_LIMIT):
        DataSourceJob.objects.filter(
            uuid__in=batch_ids
        ).exclude(
            status=DataSourceJob.ERROR
        ).update(
            status=DataSourceJob.ERROR,
            modify_date=now,
        )

    return {
        "checked": total_checked,
        "marked_error": len(error_job_ids),
    }