from checkemails.core.email import Email
from subscription.models import ClientCreditSubscription,ClientRecord, SubscriptionPackage
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Value, BooleanField, Q
from django.http.response import HttpResponseRedirect
from django.urls import reverse_lazy
from django.conf import settings
from accounts.models import User, UserRole

class CheckEmailsHome(TemplateView):
    template_name = 'app/dashboard.html'

    
    def get_context_data(self, **kwargs):
        context = super(CheckEmailsHome, self).get_context_data(**kwargs)
        filter_set = Q(is_custom=False, is_active=True)
        if self.request.user.is_authenticated:
            filter_set &= ~Q(subscription_period=SubscriptionPackage.SUBSCRIPTION_ONE_WEEK)
        packages = SubscriptionPackage.objects.filter(Q(filter_set)).order_by('subscription_period')
        context['packages'] = packages
        return context

class PrivacyPolicyView(TemplateView):
    template_name = 'app/privacy_policy.html'
    
class TNCView(TemplateView):
    template_name = 'app/tnc.html'

class ConactUsSentView(TemplateView):
    template_name = 'app/contact-us-submit.html'

class ContactUsView(TemplateView):
    template_name = 'app/contact-us.html'

    def post(self, request, *args, **kwargs):

        data = request.POST
        admins = User.objects.filter(is_staff=True, is_superuser=True,
                user_role__role=UserRole.SUPERADMIN,
                 is_active=True,).first()
        email = Email(admins.email, data.get('subject'))
        template_name = 'accounts/email/contact_us_template.html'
        context = {
            'name': data.get('name'),
            'message': data.get('message'),
            'email': data.get('email')
        }
        email.message_from_template(template_name, context, request).send()
        return HttpResponseRedirect(reverse_lazy('app:contact_us_sent'))