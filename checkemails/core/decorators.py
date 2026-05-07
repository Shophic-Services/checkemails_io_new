from django.conf import settings
from optisolve.core.middleware import get_current_db_name, set_db_for_router
from celery.contrib import rdb


def task_decorator(func):
    def inner(*args, **kwargs):
        # rdb.set_trace()
        db = kwargs.get('db')
        set_db_for_router(db)
        func(*args, **kwargs)
        #close connection
    return inner

def beat_decorator(func):
    def inner(*args, **kwargs):
        for db in settings.DATABASES:
            set_db_for_router(db)
            func(*args, **kwargs)
    return inner

