'''
for middleware
'''
from __future__ import absolute_import, division, print_function
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from log.models import Log
from accounts.models import UserRole
from django.contrib import admin

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()

def get_current_request():
    return getattr(_thread_locals, "request", None)

def get_current_user():
    request = get_current_request()
    if request:
        return getattr(request, "user", None)
        


class AppMiddleware(MiddlewareMixin):
    '''
    app middleware
    '''
    def process_request(self, request):
        '''
        process request
        '''
        _ = self
        models_list = [Log, ]
        if request.user.is_authenticated and request.user.user_role and request.user.user_role.role != UserRole.SUPERADMIN:
            [admin.site.unregister(model) for model in models_list if admin.site.is_registered(model)]




class ThreadLocalMiddleware(MiddlewareMixin):

    def process_request(self, request):
        _ = self
        _thread_locals.request = request

    def process_response(self, request, response):
        _ = self
        if hasattr(_thread_locals, 'request'):
            del _thread_locals.request
        return response
    