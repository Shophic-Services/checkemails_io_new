'''
for middleware
'''
import sys
import traceback
import logging
import time
import re
import json

from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from log.models import Log


class LoggingMiddleware(MiddlewareMixin):
    '''
    logging middleware
    '''
    def process_request(self, request):
        '''
        process request
        '''
        self.start_time = timezone.now()
        if not request.content_type == 'multipart/form-data':
            self.request_body = request.body
        self.request_get_params = request.GET

    def process_response(self, request, response):
        '''
        process response
        '''
        try:
            lst_app_for_logging = settings.LST_APP_FOR_LOGGING
            str_token = request.META.get('HTTP_AUTHORIZATION', None)
            app_name = self._get_app_namespace(resolve(request.path).namespace)
            if app_name in lst_app_for_logging and response['Content-Type'].split(';')[0] != 'text/javascript':
                if request.method == 'GET' and 'api' not in request.get_full_path():
                    return response
                full_stack_trace = ''
                exception_short_value = ''
                user_email = '-'
                extra_log = ''

                log = Log()
                type_exc, value, tb = sys.exc_info()

                log.request_datetime = self.start_time
                log.response_datetime = timezone.now()
                total_time_taken = timezone.now() - self.start_time
                log.total_time_taken = total_time_taken.total_seconds()

                remote_addr = request.META.get('REMOTE_ADDR')
                log.access_token = str_token

                if remote_addr in getattr(settings, 'INTERNAL_IPS', []):
                    remote_addr = request.META.get(
                        'HTTP_X_FORWARDED_FOR') or remote_addr

                log.remote_address = remote_addr

                if hasattr(request, 'user'):
                    user_email = getattr(request.user, 'email', '-')
                log.user_email = user_email

                pattern = settings.LOG_PATTERN
                request_content = None
                
                if self.request_body:
                    request_content = self.request_body.decode('utf-8')
                    passwords = re.findall(pattern, request_content)
                    for password in passwords:
                        request_content = request_content.replace(password, '"******"')
                if request_content:
                    request_content = json.loads(request_content)
                    log.request_content_length = len(request_content)
                    log.request_content = request_content

                log.response_content = response.content

                log.response_content_length = sys.getsizeof(
                    response.content) / float(1000)
                # Return the size of object in bytes.

                if str(response.status_code) == '500' or str(
                        response.status_code) == '401' and type_exc:
                    full_stack_trace = ' '.join(
                        traceback.format_exception(type_exc, value, tb))
                    exception_short_value = str(value)
                    log.exception_full_stack_trace = full_stack_trace
                    log.exception_short_value = exception_short_value
                    log.response_content = None
                    log.response_content_length = None

                sql_time = sum(float(q['time'])
                               for q in connection.queries) * 1000
                extra_log += " (%s SQL queries, %s ms)" % (
                    len(connection.queries), sql_time)
                log.extra_log = extra_log

                log.method_type = request.method
                log.method_name = request.get_full_path()
                log.response_status_type = response.status_code
                log.save()
        except Exception as e:
            logging.error("LoggingMiddleware Error: %s" % e)
        return response

    @staticmethod
    def _get_app_namespace(app_first_name):
        try:
            app_namespace = app_first_name.split(':')[1]
            app_name = app_namespace.split('_')[1]
        except IndexError:
            app_name = app_first_name
        return app_name
