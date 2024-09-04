'''
tasks.py for log
'''
import requests, json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from celery import shared_task

from log.models import Log

from checkemails.celery import app

from datetime import datetime, timedelta


@app.task()
def remove_logs():
    try:
        logs = Log.objects.filter(request_datetime__lte=datetime.now() - timedelta(days=7)).delete()
    except:
        pass
