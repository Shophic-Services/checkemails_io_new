"""
scraper/tasks/finalize.py

Chord callback — runs after ALL scrape_url_batch_task workers complete.
Marks the job COMPLETED, deducts credits, pushes a final WebSocket update.

Mirrors tools/tasks/finalize.py from the email-verifier pipeline.

Fixes carried over:
  • credit_reserved is re-read after save() so push_scraper_job_update
    receives the real value (was always None before the fix).
  • Guard against negative balances.
  • Job re-fetched before final WS push so counts reflect all worker writes.
"""

from celery import shared_task
from django.utils import timezone

from tools.models import DataSourceJob
from tools.websocket import push_scraper_job_update
from subscription.models import ClientCreditSubscription   # reuse your existing model


@shared_task(queue="scraper_finalize")
def finalize_scraper_job_task(results, job_id: str, user_id: int):
    job = DataSourceJob.objects.get(uuid=job_id)

    job.status          = DataSourceJob.COMPLETED
    job.completed_at    = timezone.now()
    job.finalize_task_id = finalize_scraper_job_task.request.id
    job.save(update_fields=["status", "completed_at", "finalize_task_id"])

    credit_balance  = None
    credit_reserved = None

    active_subscription = (
        ClientCreditSubscription.objects
        .filter(client_id=user_id, is_activated=True)
        .order_by("-create_date")
        .first()
    )

    if active_subscription:
        # Deduct: charge only for URLs where we actually found something
        # (ok_count). Adjust the formula to match your billing policy.
        active_subscription.credit_reserved -= job.total_items
        active_subscription.credit_balance  -= job.ok_count

        active_subscription.credit_balance  = max(0, active_subscription.credit_balance)
        active_subscription.credit_reserved = max(0, active_subscription.credit_reserved)
        active_subscription.save()

        credit_balance  = active_subscription.credit_balance
        credit_reserved = active_subscription.credit_reserved   # FIX: read back after save

    # Re-fetch to get final aggregated counts from all workers
    job = DataSourceJob.objects.get(uuid=job_id)
    push_scraper_job_update(job, credit_balance, credit_reserved)
    return {
        "job_id":    job_id,
        "completed": True,
        "processed": job.valid_count + job.invalid_count + job.unknown_count,
    }