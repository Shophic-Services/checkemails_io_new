from datetime import datetime, timezone
from logging import exception
from django.utils.deprecation import MiddlewareMixin
from django.http.response import Http404, HttpResponseRedirect, JsonResponse
from django.urls.base import reverse_lazy
from checkemails.core.utils import SubscriptionValidations
from django.urls import resolve

class SubscriptionMiddleware(MiddlewareMixin):
    '''
    Middleware to check plans
    '''

    include_urls=[
        'single_check',
        'multi_check',
        'spam_check'
    ]


    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        plan = SubscriptionValidations(request, user=request.user).get_current_plan()
        if request.user.is_authenticated and not plan and not request.user.is_superuser and\
            resolve(request.path).url_name in self.include_urls:
            return HttpResponseRedirect(reverse_lazy('subscription:plan-required'))




