from __future__ import absolute_import, unicode_literals

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'checkemails.settings')

app = Celery('checkemails')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


class ScopeBasedTask(app.Task):
    abstract = True
    ignore_result = False

    def __init__(self, *args, **kwargs):
        super(ScopeBasedTask, self).__init__(*args, **kwargs)

