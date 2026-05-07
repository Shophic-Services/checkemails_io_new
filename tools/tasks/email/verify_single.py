"""
tools/tasks/verify_single.py

Celery task for single-email verification with hard timeout guards
so it can never trigger the billiard 600s hard limit.
"""

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from tools.models import EmailData


@shared_task(
    queue="email_single",
    bind=True,
    max_retries=1,
    acks_late=True,
    soft_time_limit=60,   # raises SoftTimeLimitExceeded → clean shutdown
    time_limit=60,        # hard kill — well under billiard's 600s default
)
def verify_single_email_task(self, email: str, user_id: int):
    """
    Verify a single email address and return the result dict.
    Dispatched immediately from the view; result delivered via
    GET /verify/result/<task_id>/ or the existing WebSocket channel.
    """
    from tools.helper import EmailCheckHelper   # local import avoids circular

    try:
        helper = EmailCheckHelper(user_id=user_id)
        result = helper.validate_email(email)

        (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        ) = result

        return {
            'email':               email,
            'status':              status,
            'quality':             quality,
            'email_result':        email_result,
            'valid':               valid,
            'code':                code,
            'message':             str(message),
            'catch_all':           catch_all,
            'is_role_based':       is_role_based,
            'has_domain_mx':       has_domain_mx,
            'has_spf':             has_spf,
            'has_dmarc':           has_dmarc,
            'email_source':        email_source,
            'email_type':          email_type,
            'retry_later':         retry_later,
            'permanent_failure':   permanent_failure,
            'needs_manual_review': needs_manual_review,
            'has_smtp':            has_smtp,
        }

    except SoftTimeLimitExceeded:
        return {
            'email':        email,
            'status':       EmailData.UNKNOWN,
            'quality':      EmailData.UNKNOWN,
            'email_result': 'Do Not Send - Timed Out',
            'valid':        False,
            'code':         408,
            'message':      'Verification timed out',
        }

    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)