"""
scraper/tasks/dispatch.py

Reads all PENDING ScraperItem IDs for the job, slices them into
BATCH_SIZE chunks, then fires a Celery chord:

    chord([scrape_batch(ids_0), scrape_batch(ids_1), ...])(finalize_job)

Mirrors tools/tasks/dispatch.py from the email-verifier pipeline.

Key fixes carried over:
  • callback queue set on the signature (.set(queue=...)), NOT on chord().
  • finalize_task_id stored on the job so reconcile_scraper_jobs can tell
    whether the finalize step actually finished (dispatch goes SUCCESS
    immediately after the chord is created — useless for health-checking).
"""

from celery import shared_task, chord
from django.utils import timezone

from tools.models import DataSourceJob, DataSourceItem
from tools.tasks.scraper.scrape_batch import scrape_url_batch_task
from tools.tasks.scraper.finalize import finalize_scraper_job_task


BATCH_SIZE = 50   # URLs per worker task — tune to taste


def chunked_queryset(qs, size):
    batch = []
    for obj in qs:
        batch.append(obj)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


@shared_task(queue="scraper_ingest")
def dispatch_scrape_batches_task(job_id: str, user_id: int):
    job = DataSourceJob.objects.get(uuid=job_id)

    job.status     = DataSourceJob.INPROGRESS
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    items_qs = (
        DataSourceItem.objects
        .filter(source_job=job, status=DataSourceItem.PENDING)
        .values_list("id", flat=True)
    )

    batches = list(chunked_queryset(items_qs, BATCH_SIZE))

    if not batches:
        # Nothing to process — jump straight to finalize
        finalize_scraper_job_task.apply_async(
            args=([], job.uuid, user_id),
            queue="scraper_finalize",
        )
        return None
    tasks = []
    for batch_ids in batches:
        sig = scrape_url_batch_task.s(
            job.uuid, list(batch_ids), user_id
        ).set(queue="scraper_worker")
        tasks.append(sig)

    # FIX: queue goes on the callback *signature*, not on chord() itself.
    callback     = finalize_scraper_job_task.s(job.uuid, user_id).set(queue="scraper_finalize")
    chord_result = chord(tasks)(callback)

    # Store so reconcile task can track real completion (not dispatch completion).
    DataSourceJob.objects.filter(uuid=job.uuid).update(
        finalize_task_id=chord_result.id
    )

    return chord_result.id