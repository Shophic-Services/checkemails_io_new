from django.urls import include, path, re_path

from subscription.views import (PlanRequiredView,)


app_name = 'subscription'

urlpatterns = [
    path('plan-required/', PlanRequiredView.as_view(), name='plan-required'),
]