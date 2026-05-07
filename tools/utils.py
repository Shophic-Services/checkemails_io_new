# utils.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from tools.api_base.serializers import DataSourceJobSerializer


def push_bulk_job_update(job):
    channel_layer = get_channel_layer()

    payload = {
        "response": [DataSourceJobSerializer(job).data],
        "status": 200,
    }

    async_to_sync(channel_layer.group_send)(
        'bulk_validation_updates',
        {
            'type': 'bulk_status_update',
            'data': payload,
        }
    )



def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]
