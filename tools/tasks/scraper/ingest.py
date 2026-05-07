"""
scraper/tasks/ingest.py

Entry-point task.  Reads URLs from job.input_references, bulk-creates
DataSourceItems (one per URL), then hands off to dispatch.

Mirrors tools/tasks/ingest.py from the email-verifier pipeline.
"""

from celery import shared_task
from django.utils import timezone

from tools.models import DataSourceItem, DataSourceJob
from tools.tasks.scraper.dispatch import dispatch_scrape_batches_task


@shared_task(queue="scraper_ingest")
def create_scraper_items_task(job_id: str, user_id: int, batch_size: int = 1000):
    job = DataSourceJob.objects.get(uuid=job_id)

    items = [
        DataSourceItem(
            source_job=job,
            input_value=str(url).strip(),
            belongs_to_id=user_id,
        )
        for url in job.input_references   # list/queryset of raw URLs stored on the job
    ]

    DataSourceItem.objects.bulk_create(
        items,
        batch_size=batch_size,
        ignore_conflicts=True,  # deduplicate if same URL submitted twice
    )

    # FIX (mirrors email verifier): use DB count, not len(items), because
    # bulk_create with ignore_conflicts=True silently skips duplicates.
    actual_count = DataSourceItem.objects.filter(source_job=job).count()

    job.total_items = actual_count
    job.status      = DataSourceJob.INPROGRESS
    job.started_at  = timezone.now()
    job.save(update_fields=["total_items", "status", "started_at"])

    result = dispatch_scrape_batches_task.delay(job.uuid, user_id)

    job.dispatch_task_id = result.id
    job.dispatched_at    = timezone.now()
    job.save(update_fields=["dispatch_task_id", "dispatched_at"])