"""
tools/tasks/validate_batch.py

soft_time_limit=60  fires SoftTimeLimitExceeded — we catch it, mark the
                    in-progress item + ALL remaining unprocessed items in
                    this batch as Unknown, flush everything to DB, push a
                    WebSocket update, then return cleanly.

time_limit=90       hard kill — intentionally 30s ABOVE soft so the soft
                    signal always fires first and the graceful save can
                    complete before the process is killed.
                    Never set time_limit == soft_time_limit or the hard
                    kill can race the soft handler.
"""

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.db.models import F

from tools.models import DataSourceItem, DataSourceJob, EmailData
from tools.helper import EmailCheckHelper
from tools import constants
from tools.websocket import push_job_update


@shared_task(
    queue="email_validation",
    bind=True,
    acks_late=True,
    soft_time_limit=82800,   # raises SoftTimeLimitExceeded → graceful save
    time_limit=86400,        # hard kill — must be > soft_time_limit
)
def validate_email_batch_task(self, job_id, item_ids, user_id):

    DataSourceItem.objects.filter(
        id__in=item_ids,
        status=DataSourceItem.PENDING,
    ).update(status=DataSourceItem.INPROGRESS)

    items = list(
        DataSourceItem.objects
        .filter(
            id__in=item_ids,
            status=DataSourceItem.INPROGRESS,
        ).exclude(
            source_job__status=DataSourceJob.ERROR,
        )
        .only("id", "input_value")
    )

    if not items:
        return 0

    completed            = 0
    valid_count          = 0
    invalid_count        = 0
    role_count           = 0
    catch_all_count      = 0
    disposable_count     = 0
    unknown_count        = 0
    syntax_invalid_count = 0
    risky_count          = 0

    # IDs that have been fully processed (success or per-item exception).
    # Used by _flush() to identify items that were never reached.
    processed_ids = set()

    # ------------------------------------------------------------------
    # _flush — single exit point that always saves everything
    # ------------------------------------------------------------------
    def _flush(timed_out_item=None):
        """
        1. If timed_out_item is provided, stamp it as Unknown (it was
           mid-flight when the soft limit fired).
        2. Stamp every item that was never reached as Unknown.
        3. bulk_update all items.
        4. Atomically increment all job counters.
        5. Push a WebSocket update so the frontend reflects progress.
        """
        nonlocal unknown_count, completed

        if timed_out_item is not None:
            timed_out_item.result_data = {
                'email':        timed_out_item.input_value,
                'status':       EmailData.UNKNOWN,
                'quality':      EmailData.UNKNOWN,
                'email_result': 'Do Not Send - Timed Out',
                'valid':        False,
                'code':         408,
                'message':      'Task time limit exceeded during verification',
            }
            timed_out_item.status = DataSourceItem.COMPLETED
            unknown_count        += 1
            completed            += 1
            processed_ids.add(timed_out_item.id)

        # Mark every item not yet reached as Unknown
        for remaining in items:
            if remaining.id not in processed_ids:
                remaining.result_data = {
                    'email':        remaining.input_value,
                    'status':       EmailData.UNKNOWN,
                    'quality':      EmailData.UNKNOWN,
                    'email_result': 'Do Not Send - Timed Out',
                    'valid':        False,
                    'code':         408,
                    'message':      'Batch timed out before this email was reached',
                }
                remaining.status = DataSourceItem.COMPLETED
                unknown_count   += 1
                completed       += 1

        # Persist all items in a single DB round-trip
        DataSourceItem.objects.bulk_update(items, ["status", "result_data"])

        # Atomically update job counters
        DataSourceJob.objects.filter(uuid=job_id).update(
            completed_count=F("completed_count")           + completed,
            valid_count=F("valid_count")                   + valid_count,
            risky_count=F("risky_count")                   + risky_count,
            invalid_count=F("invalid_count")               + invalid_count,
            role_based_count=F("role_based_count")         + role_count,
            catch_all_count=F("catch_all_count")           + catch_all_count,
            disposable_count=F("disposable_count")         + disposable_count,
            unknown_count=F("unknown_count")               + unknown_count,
            syntax_invalid_count=F("syntax_invalid_count") + syntax_invalid_count,
        )

        job = DataSourceJob.objects.get(uuid=job_id)
        push_job_update(job)

    # ------------------------------------------------------------------
    # Main per-item verification loop
    # ------------------------------------------------------------------
    for item in items:
        try:
            email_helper = EmailCheckHelper(user_id=user_id)
            result = email_helper.validate_email(
                item.input_value, action=constants.BULK
            )

            (
                email, is_role_based, has_domain_mx, has_spf, has_dmarc,
                status, quality, email_result, valid, email_source,
                catch_all, email_type, code, message, errors,
                retry_later, permanent_failure, needs_manual_review, has_smtp,
            ) = result

            item.result_data = {
                'email':               email,
                'is_role_based':       is_role_based,
                'has_domain_mx':       has_domain_mx,
                'has_spf':             has_spf,
                'has_smtp':            has_smtp,
                'has_dmarc':           has_dmarc,
                'status':              status,
                'quality':             quality,
                'email_result':        email_result,
                'valid':               valid,
                'email_source':        email_source,
                'catch_all':           catch_all,
                'email_type':          email_type,
                'code':                code,
                'message':             str(message),
                'errors':              str(errors),
                'retry_later':         retry_later,
                'permanent_failure':   permanent_failure,
                'needs_manual_review': needs_manual_review,
            }
            item.status = DataSourceItem.COMPLETED
            completed  += 1
            processed_ids.add(item.id)

            # Counters
            if quality == EmailData.RISKY:
                risky_count += 1
            elif valid:
                valid_count += 1
            elif quality == EmailData.UNKNOWN:
                unknown_count += 1
            else:
                invalid_count += 1

            if catch_all:
                catch_all_count += 1
            if is_role_based:
                role_count += 1
            if email_type == EmailData.DISPOSABLE:
                disposable_count += 1
            elif email_type == EmailData.SYNTAX_ERROR:
                syntax_invalid_count += 1

        except SoftTimeLimitExceeded:
            # Soft limit fired while verifying `item`.
            # Save everything — processed items with real results,
            # current item + all remaining items as Unknown — then exit.
            _flush(timed_out_item=item)
            return completed

        except Exception as exc:
            # Single-item failure — mark Unknown and continue the batch
            item.result_data = {
                'email':        item.input_value,
                'error':        str(exc),
                'status':       EmailData.UNKNOWN,
                'quality':      EmailData.UNKNOWN,
                'email_result': 'Do Not Send - Unable to Confirm',
                'valid':        False,
            }
            item.status    = DataSourceItem.COMPLETED
            unknown_count += 1
            completed     += 1
            processed_ids.add(item.id)

    # Normal completion path
    _flush()
    return completed