
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView, View

from django.db.models import Q
from accounts.models import UserToken
from checkemails.core.utils import SubscriptionValidations
from subscription.models import ClientCreditSubscription, SubscriptionPackage
from subscription.forms import SubscriptionBuyForm
from django.shortcuts import render
from subscription.paypal_utils import CreateOrder, CaptureOrder, GetOrder

from django.http import HttpResponseRedirect, JsonResponse
import json

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import authenticate, login

class PlanRequiredView(LoginRequiredMixin, TemplateView):
    template_name = "subscription/plan_required.html"


class SubscriptionBuyView(FormView):
    template_name = "subscription/plan_buy.html"
    form_class = SubscriptionBuyForm
    success_url = reverse_lazy(
        'subscription:payment-success')
    
    
    def get_context_data(self, **kwargs):
        context = super(SubscriptionBuyView, self).get_context_data(**kwargs)
        package = SubscriptionPackage.objects.get(id=self.kwargs.get('uuid'))
        context['package'] = package
        context["publishable_key"] = settings.STRIPE_PUBLISHABLE_KEY
        return context
    
    def get_form_kwargs(self):
        data = super(SubscriptionBuyView, self).get_form_kwargs()
        data.update({'request': self.request})
        return data
    
    def get_success_url(self):
        url = self.success_url
        token = UserToken.objects.filter(uuid=self.request.session.get('token')).first()
        if token:
            del self.request.session['token']
            login(self.request, token.user, backend='django.contrib.auth.backends.ModelBackend')
            update_session_auth_hash(self.request, token.user)
            
        self.request.session['plan_buy'] = True
        return url 
    
    

class PlanListView(LoginRequiredMixin, TemplateView):
    template_name = "subscription/plan_list.html"
    
    def get_context_data(self, **kwargs):
        context = super(PlanListView, self).get_context_data(**kwargs)
        filter_set = Q(is_custom=False, is_active=True)
        if self.request.user.is_authenticated:
            filter_set &= ~Q(subscription_period=SubscriptionPackage.SUBSCRIPTION_ONE_WEEK)
        packages = SubscriptionPackage.objects.filter(Q(filter_set)).order_by('subscription_period')
        context['packages'] = packages
        context["publishable_key"] = settings.STRIPE_PUBLISHABLE_KEY
        return context
    
class PlanBuyView(LoginRequiredMixin, SubscriptionBuyView):
    template_name = "subscription/subs_plan_buy.html"

    
    success_url = reverse_lazy(
        'accounts:credit')


class CreatePaypalOrderView(View):
    
    def post(self, request, *args, **kwargs):
        package = SubscriptionPackage.objects.get(id=kwargs.get('uuid'))
        plan_price=package.price
        if package.subscription_period == 3:
                plan_price = package.price * 12
        curr_donor=request.user
        Responsee=CreateOrder().create_order(package=package,amt_value=plan_price,present_donor=curr_donor)

        return JsonResponse(Responsee)
    
class GetPaypalTransactionDetailsView(View):
    
    def get(self, request, *args, **kwargs):
        orderid = None
        order=GetOrder().get_order(orderid)
        return JsonResponse(order)
    
class CapturePaypalOrderView(View):
    
    def post(self, request, *args, **kwargs):
        data=json.loads(request.body.decode("utf-8"))
        ordrid=data['orderID']
        package = SubscriptionPackage.objects.get(id=kwargs.get('uuid'))
        plan_price=package.price
        if package.subscription_period == 3:
                plan_price = package.price * 12
        curr_donor=request.user
        capture=CaptureOrder().capture_order(ordrid,package=package,amt_value=plan_price,present_donor=curr_donor)
        
        curr_donor.plan_id=package.id
        curr_donor.has_plan=True
        curr_donor.save()
        request.session['plan_buy'] = True
        return JsonResponse(capture)


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'subscription/payment-success.html'

    
    def get(self, request, *args, **kwargs):
        if self.request.session.get('plan_buy'):
            del self.request.session['plan_buy']
            return super(PaymentSuccessView, self).get(request, *args, **kwargs)
        return HttpResponseRedirect(reverse_lazy('app:home'))

    def get_context_data(self, **kwargs):
        context = super(PaymentSuccessView, self).get_context_data(**kwargs)
        subscription = ClientCreditSubscription.objects.filter(client=self.request.user, is_activated=True).first()
        context['subscription'] = subscription
        return context

class PaymentFailureView(TemplateView):
    template_name = 'subscription/payment-failed.html'
     

    def get_context_data(self, **kwargs):
        context = super(PaymentFailureView, self).get_context_data(**kwargs)
        return context
    

class PlanPaymentView(LoginRequiredMixin, TemplateView):
    template_name = 'subscription/payment-plan.html'
    
    def get(self, request, *args, **kwargs):
        get_plans = SubscriptionValidations(request, user=request.user).get_active_plans()
        if not get_plans and request.user.plan_id and not request.user.has_plan:
            return super(PlanPaymentView, self).get(request, *args, **kwargs)
        return HttpResponseRedirect(reverse_lazy('emailtool:app_dashboard'))
    
    def get_context_data(self, **kwargs):
        context = super(PlanPaymentView, self).get_context_data(**kwargs)
        filter_set = Q(is_custom=False, is_active=True)
        filter_set &= ~Q(subscription_period=SubscriptionPackage.SUBSCRIPTION_ONE_WEEK)
        packages = SubscriptionPackage.objects.filter(Q(filter_set)).order_by('subscription_period')
        context['packages'] = packages
        context["publishable_key"] = settings.STRIPE_PUBLISHABLE_KEY
        return context
    
    
    
class PlanCheckView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        get_plans = SubscriptionValidations(request, user=request.user).get_active_plans()
        if not get_plans and request.user.plan_id and not request.user.has_plan:
            return HttpResponseRedirect(reverse_lazy('subscription:plan-payment', kwargs={'uuid': request.user.plan_id}))
        return HttpResponseRedirect(reverse_lazy('emailtool:app_dashboard'))