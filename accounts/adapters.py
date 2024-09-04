from django.utils import timezone
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from subscription.models import ClientCreditSubscription, SubscriptionPackage
from subscription.stripe_utils import StripeSubscriptionHelper
from dateutil.relativedelta import relativedelta


class AccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        return False


class SocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_open_for_signup(self, request, sociallogin):
        return bool(sociallogin)

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login. In case of auto-signup,
        the signup form is not available.
        """
        
        from allauth.account.adapter import get_adapter as get_account_adapter
        from accounts.models import UserRole
        u = sociallogin.user
        u.set_unusable_password()
        if form:
            get_account_adapter().save_user(request, u, form)
        else:
            get_account_adapter().populate_username(request, u)
        sociallogin.user.is_active = True
        sociallogin.user.google_user = True        
        sociallogin.user.user_role = UserRole.objects.filter(
            role=UserRole.CLIENT).first()
        sociallogin.user.plan_id = request.session.get('plan')
        sociallogin.user.save()
        if request.session.get('plan'):
            del request.session['plan']
        plan = SubscriptionPackage.objects.filter(can_change=False, subscription_period=SubscriptionPackage.SUBSCRIPTION_ONE_WEEK).first()
        helper_class = StripeSubscriptionHelper(sociallogin.user, request)
        helper_class.create_customer()
        helper_class.create_offline_data(plan) 
        if sociallogin.user.plan_id and sociallogin.user.plan_id != str(plan.id):
            ClientCreditSubscription.objects.filter(client=sociallogin.user).update(is_activated=False, is_current=False, expire_date=timezone.now())
            sociallogin.user.has_plan=False
            sociallogin.user.save()
        sociallogin.save(request)        
        sociallogin.user.send_email_to_admins(request)
        
        return u
        