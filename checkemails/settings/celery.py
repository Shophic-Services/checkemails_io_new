'''
Celery settings
'''
import os
from celery.schedules import crontab

REDIS_DB = 1
CHECK_EMAILS_LOCAL_IP = 'localhost'
REDIS_DB_IP = os.environ.get('REDIS_SERVER_IP', CHECK_EMAILS_LOCAL_IP)

BROKER_URL = 'redis://{0}:6379/{1}'.format(REDIS_DB_IP, REDIS_DB)
BROKER_BACKEND = "redis"
BROKER_CONNECTION_TIMEOUT = 5.0

CELERY_ENABLED = True

CELERY_BROKER_URL = 'redis://{0}:6379/{1}'.format(REDIS_DB_IP, REDIS_DB)
CELERY_RESULT_BACKEND = 'redis://{0}:6379'.format(REDIS_DB_IP)
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'

CELERY_BEAT_SCHEDULE = {
    
    'remove_logs': {
        'task': 'log.tasks.remove_logs',
        'schedule': crontab(minute=0, hour=0),
    },
    'emailsearch_send_data':{
        'task': 'emailtool.tasks.emailsearch_send_data',
        'schedule': crontab(minute=0, hour=9),
    }
}
