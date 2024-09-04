from django.urls import include, path, re_path

from subscription.views import (PlanRequiredView, SubscriptionBuyView, PlanListView, 
                                PlanBuyView, CreatePaypalOrderView, CapturePaypalOrderView, 
                                PaymentSuccessView, PaymentFailureView, PlanPaymentView,
                                PlanCheckView)

app_name = 'subscription'

urlpatterns = [
    path('plan-required/', PlanRequiredView.as_view(), name='plan-required'),
    path('plan-check/', PlanCheckView.as_view(), name='plan_check'),
    path('plan-payment/<uuid:uuid>/', PlanPaymentView.as_view(), name='plan-payment'),
    path('plans/', PlanListView.as_view(), name='plans'),
    path('plans/<uuid:uuid>/buy/', PlanBuyView.as_view(), name='plans-buy'),
    path("plan-buy/<uuid:uuid>/", SubscriptionBuyView.as_view(), name="plan-buy"),
    path('plan-paypal-create/<uuid:uuid>/',CreatePaypalOrderView.as_view(), name="paypal-plan-create"),
    path('plan-paypal-buy/<uuid:uuid>/',CapturePaypalOrderView.as_view(), name="paypal-plan-buy"),
    path('payment-success/',PaymentSuccessView.as_view(), name="payment-success"),
    path('payment-failure/',PaymentFailureView.as_view(), name="payment-failure")
]