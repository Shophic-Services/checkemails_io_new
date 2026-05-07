from celery import shared_task
from django.utils import timezone

from tools.models import DataSourceJob, DataSourceItem
from tools.tasks.email.dispatch import dispatch_validation_batches_task


@shared_task(queue="email_ingest")
def create_datasource_items_task(job_id, user_id, batch_size=1000):
    job = DataSourceJob.objects.get(uuid=job_id)

    items = [
        DataSourceItem(
            source_job=job,
            input_value=value.strip().lower(),
            belongs_to_id=user_id
        )
        for value in job.input_references
    ]

    DataSourceItem.objects.bulk_create(
        items,
        batch_size=batch_size,
        ignore_conflicts=True
    )

    # FIX: Use actual DB count instead of len(items) — bulk_create with
    # ignore_conflicts=True silently skips duplicates, so len(items) overstates
    # the real row count and corrupts progress tracking.
    actual_count = DataSourceItem.objects.filter(source_job=job).count()

    job.total_items = actual_count
    job.status = DataSourceJob.INPROGRESS
    job.started_at = timezone.now()
    job.save(update_fields=["total_items", "status", "started_at"])

    result = dispatch_validation_batches_task.delay(job.uuid, user_id)

    job.dispatch_task_id = result.id
    job.dispatched_at = timezone.now()
    job.save(update_fields=["dispatch_task_id", "dispatched_at"])