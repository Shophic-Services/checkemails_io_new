'''
Celery settings
'''
from datetime import timedelta
import os
from celery.schedules import crontab
from kombu import Queue, Exchange

REDIS_DB = 1
CHECK_EMAILS_LOCAL_IP = 'localhost'
REDIS_DB_IP = os.environ.get('REDIS_SERVER_IP', CHECK_EMAILS_LOCAL_IP)

BROKER_URL = 'redis://{0}:6379/{1}'.format(REDIS_DB_IP, REDIS_DB)
BROKER_BACKEND = "redis"
BROKER_CONNECTION_TIMEOUT = 5.0

CELERY_ENABLED = True

CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_SOFT_TIME_LIMIT = 82800
CELERY_TASK_TIME_LIMIT      = 86400
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

CELERY_BROKER_URL = 'redis://{0}:6379/{1}'.format(REDIS_DB_IP, REDIS_DB)
CELERY_RESULT_BACKEND = 'redis://{0}:6379'.format(REDIS_DB_IP)
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'

CELERY_TASK_DEFAULT_QUEUE = 'default'

# define the separate queues for load tasks.
CELERY_TASK_QUEUES = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('email_ingest', Exchange('email_ingest'), routing_key='email_ingest'),
    Queue('email_validation', Exchange('email_validation'), routing_key='email_validation'),
    Queue('job_finalize', Exchange('job_finalize'), routing_key='job_finalize'),
)

# define queue specific tasks others go to default.
CELERY_TASK_ROUTES = {
    'tools.tasks.email.verify_single.verify_single_email_task': {
        'queue': 'email_single'
    },
    'tools.tasks.email.ingest.create_datasource_items_task': {
        'queue': 'email_ingest',
    },
    'tools.tasks.email.validate_batch.validate_email_batch_task': {
        'queue': 'email_validation',
    },
    'tools.tasks.email.finalize.finalize_job_task': {
        'queue': 'job_finalize',
    },
    "tools.tasks.scraper.ingest.create_scraper_items_task":            {"queue": "scraper_ingest"},
    "tools.tasks.scraper.dispatch.dispatch_scrape_batches_task":        {"queue": "scraper_ingest"},
    "tools.tasks.scraper.scrape_batch.scrape_url_batch_task":           {"queue": "scraper_worker"},
    "tools.tasks.scraper.finalize.finalize_scraper_job_task":           {"queue": "scraper_finalize"},
    "tools.tasks.scraper.reconcile_scraper_jobs.reconcile_scraper_jobs": {"queue": "scraper_maintenance"},
    
}

CELERY_BEAT_SCHEDULE = {
    
    'remove_logs': {
        'task': 'log.tasks.remove_logs',
        'schedule': crontab(minute=0, hour=0),
    },
    "retry-failed-bulk-validation-every-30-min": {
        "task": "tools.tasks.email.reconcile_jobs.reconcile_bulk_jobs",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "maintenance"},
    },
        "reconcile-scraper-jobs-every-15-min": {
        "task":     "tools.tasks.scraper.reconcile_scraper_jobs.reconcile_scraper_jobs",
        "schedule": timedelta(minutes=15),
    },
}
