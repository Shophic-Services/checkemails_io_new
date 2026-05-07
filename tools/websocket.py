from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from tools.models import DataSourceJob
from tools.api_base.serializers import DataSourceJobSerializer, ScraperJobSerializer
from django.db.models import F

def push_job_update(job: DataSourceJob, credit_balance=None, credit_reserved=None):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "bulk_dashboard",
        {
            "type": "job_update",
            "data": DataSourceJobSerializer(job).data,
            "credit_balance":credit_balance,
            "credit_reserved":credit_reserved
        }
    )



def push_scraper_job_update(
    job: DataSourceJob,
    credit_balance=None,
    credit_reserved=None,
):
    channel_layer = get_channel_layer()
    DataSourceJob.objects.filter(uuid=job.uuid).update(
        completed_count=F("valid_count") + F("invalid_count") + F("unknown_count")
    )
    async_to_sync(channel_layer.group_send)(
        "scraper_dashboard",
        {
            "type":             "job_update",
            "data":             ScraperJobSerializer(job).data,
            "credit_balance":   credit_balance,
            "credit_reserved":  credit_reserved,
        },
    )
