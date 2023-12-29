'''
definition for exception handler
'''
from django.conf import settings
import redis

def is_redis_available():
    # ... get redis connection here, or pass it in. up to you.
    rs = redis.Redis(host=settings.REDIS_DB_IP, port=6379, db=0)
    try:
        rs.client_list() 
    except (redis.exceptions.ConnectionError, 
            redis.exceptions.BusyLoadingError):
        return False
    return True