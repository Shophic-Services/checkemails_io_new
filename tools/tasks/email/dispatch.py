from celery import shared_task, chord
from django.utils import timezone

from tools.models import DataSourceJob, DataSourceItem
from tools.tasks.email.validate_batch import validate_email_batch_task
from tools.tasks.email.finalize import finalize_job_task


BATCH_SIZE = 5


def chunked_queryset(qs, size):
    batch = []
    for obj in qs:
        batch.append(obj)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


@shared_task(queue="email_ingest")
def dispatch_validation_batches_task(job_id, user_id):
    job = DataSourceJob.objects.get(uuid=job_id)

    job.status = DataSourceJob.INPROGRESS
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    items_qs = (
        DataSourceItem.objects
        .filter(source_job=job, status=DataSourceItem.PENDING)
        .values_list("id", flat=True)
    )

    batches = list(chunked_queryset(items_qs, BATCH_SIZE))

    if not batches:
        finalize_job_task.apply_async(
            args=([], job.uuid, user_id),
            queue="job_finalize"
        )
        return None

    tasks = []
    for batch_ids in batches:
        sig = validate_email_batch_task.s(
            job.uuid, list(batch_ids), user_id
        ).set(queue="email_validation")
        tasks.append(sig)

    # FIX: Set the queue on the callback signature directly, not on chord().
    # chord(tasks).apply_async(queue=...) applies the queue to the chord
    # infrastructure task, NOT the callback — the callback must carry its
    # own queue via .set(queue=...).
    callback = finalize_job_task.s(job.uuid, user_id).set(queue="job_finalize")
    chord_result = chord(tasks)(callback)

    # FIX: Save the chord/finalize task ID so reconcile_jobs can track whether
    # the finalize step actually completed, rather than checking dispatch_task_id
    # (which goes SUCCESS immediately after dispatch, causing false error marking).
    DataSourceJob.objects.filter(uuid=job.uuid).update(
        finalize_task_id=chord_result.id
    )

    return chord_result.id