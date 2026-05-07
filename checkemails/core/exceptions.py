'''
definition for exception handler
'''
from django.conf import settings
from rest_framework import status
from rest_framework.views import exception_handler
import redis

def is_redis_available():
    # ... get redis connection here, or pass it in. up to you.
    rs = redis.Redis(host=settings.REDIS_DB_IP, port=6379, db=settings.REDIS_DB_CACHE)
    if not hasattr(settings, 'CACHEOPS'):
        return False
    try:
        rs.client_list() 
    except (redis.exceptions.ConnectionError, 
            redis.exceptions.BusyLoadingError):
        return False
    return True

def error_dict(arry_dict, errors, error_response):
    for field, value in arry_dict.items():
        if field != 'non_field_errors':
            if isinstance(value, dict):                    
                value = "".join(["{}_{} : {}".format(field, key, " ".join(data)) for key, data in value.items()])
                errors.append("{}".format(value))
            else:
                errors.append("{} : {}".format(field, " ".join(value)))
        else:
            errors.append("{}".format(" ".join(value)))
        error_response['error'] = {'message': arry_dict.get(
            'detail') if arry_dict.get('detail', None) else ', '.join(errors)}

def api_exception_handler(exc, context):
    '''
    custom exception handler
    '''
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None and response.template_name is None:
        error_response = {}
        errors = []
        if isinstance(response.data, list):
            for data in response.data:
                error_dict(data, errors, error_response)
        else:
            error_dict(response.data, errors, error_response)
        
        error_response['status'] = exc.status_code
        response.data = error_response
    return response
