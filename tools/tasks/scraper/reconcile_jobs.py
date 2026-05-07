"""
scraper/tasks/reconcile_scraper_jobs.py

Periodic maintenance task: marks stale INPROGRESS ScraperJobs as ERROR.

Strategy mirrors reconcile_jobs.py from the email-verifier pipeline:

  Case 1 — finalize_task_id is set:
    • FAILURE / REVOKED → mark ERROR
    • SUCCESS but job still INPROGRESS → finalize ran but never updated the
      job (e.g. an exception after the DB write was skipped) → mark ERROR

  Case 2 — finalize_task_id is NULL and dispatch is old:
    • dispatch_task_id is SUCCESS (chord was submitted) but no finalize
      task was ever registered → chord was lost → mark ERROR

Why NOT check dispatch_task_id for Case 1:
  dispatch goes to Celery SUCCESS immediately after chord() is called,
  so every job would be incorrectly marked ERROR within seconds of starting.
  finalize_task_id only reaches SUCCESS / FAILURE when the actual callback
  finishes — that's the right signal.
"""

from celery import shared_task
from celery.result import AsyncResult
from django.utils import timezone
from datetime import timedelta

from tools import constants
from tools.models import DataSourceJob

BATCH_LIMIT       = 1000
ORPHAN_THRESHOLD  = timedelta(minutes=60)


def _chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


@shared_task(
    bind=True,
    acks_late=True,
    queue="scraper_maintenance",
)
def reconcile_scraper_jobs(self):
    """Returns {"checked": N, "marked_error": M}."""
    now           = timezone.now()
    error_job_ids = []

    # ----------------------------------------------------------------
    # Case 1: finalize_task_id is set — check its Celery state
    # ----------------------------------------------------------------
    qs_finalize = (
        DataSourceJob.objects
        .filter(
            source_type=constants.WEBSITE,
            status=DataSourceJob.INPROGRESS, finalize_task_id__isnull=False)
        .only("uuid", "finalize_task_id")
    )
    total_checked = qs_finalize.count()

    for job in qs_finalize.iterator(chunk_size=BATCH_LIMIT):
        state = AsyncResult(job.finalize_task_id).state
        if state in ("FAILURE", "REVOKED"):
            error_job_ids.append(job.uuid)
        elif state == "SUCCESS":
            # Finalize completed but job is still INPROGRESS — treat as error
            error_job_ids.append(job.uuid)

    # ----------------------------------------------------------------
    # Case 2: no finalize_task_id but dispatch was long ago (orphaned chord)
    # ----------------------------------------------------------------
    qs_orphan = (
        DataSourceJob.objects
        .filter(
            source_type=constants.WEBSITE,
            status=DataSourceJob.INPROGRESS,
            finalize_task_id__isnull=True,
            dispatch_task_id__isnull=False,
            dispatched_at__lt=now - ORPHAN_THRESHOLD,
        )
        .only("uuid", "dispatch_task_id")
    )
    total_checked += qs_orphan.count()

    for job in qs_orphan.iterator(chunk_size=BATCH_LIMIT):
        if AsyncResult(job.dispatch_task_id).state == "SUCCESS":
            error_job_ids.append(job.uuid)

    # ----------------------------------------------------------------
    # Bulk-update stale jobs to ERROR
    # ----------------------------------------------------------------
    for batch_ids in _chunked(error_job_ids, BATCH_LIMIT):
        DataSourceJob.objects.filter(
            uuid__in=batch_ids,
        ).exclude(
            status=DataSourceJob.ERROR,
        ).update(
            status=DataSourceJob.ERROR,
            modify_date=now,
        )

    return {"checked": total_checked, "marked_error": len(error_job_ids)}