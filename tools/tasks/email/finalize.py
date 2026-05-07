from celery import shared_task
from django.utils import timezone

from tools.websocket import push_job_update
from tools.models import DataSourceJob
from subscription.models import ClientCreditSubscription


@shared_task(queue="job_finalize")
def finalize_job_task(results, job_id, user_id):
    job = DataSourceJob.objects.get(uuid=job_id)

    job.status = DataSourceJob.COMPLETED
    job.completed_at = timezone.now()
    job.finalize_task_id = finalize_job_task.request.id
    job.save(update_fields=["status", "completed_at", "finalize_task_id"])

    credit_balance = None
    credit_reserved = None

    active_subscription = (
        ClientCreditSubscription.objects
        .filter(client_id=user_id, is_activated=True)
        .order_by("-create_date")
        .first()
    )

    if active_subscription:
        # FIX 1: Only deduct credits for valid + risky emails. Charging for
        # invalid emails was draining users' balances for undeliverable results.
        #
        # FIX 2: credit_reserved was never read back after save(), so
        # push_job_update always received None — the frontend credit_reserved
        # field never updated in real-time.
        active_subscription.credit_reserved -= job.total_items
        active_subscription.credit_balance -= (job.valid_count + job.risky_count + job.invalid_count)

        # Guard against going negative
        active_subscription.credit_balance = max(0, active_subscription.credit_balance)
        active_subscription.credit_reserved = max(0, active_subscription.credit_reserved)

        active_subscription.save()

        credit_balance = active_subscription.credit_balance
        credit_reserved = active_subscription.credit_reserved  # FIX: was always None before

    # Re-fetch to get final aggregated counts written by all validate tasks
    job = DataSourceJob.objects.get(uuid=job_id)
    push_job_update(job, credit_balance, credit_reserved)

    return {
        "job_id": job_id,
        "completed": True,
        "processed_items": job.completed_count,
    }