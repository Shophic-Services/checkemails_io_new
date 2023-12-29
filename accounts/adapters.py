from django.utils import timezone
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from subscription.models import ClientCreditSubscription, SubscriptionPackage
from subscription.utils import CreateSubscriptionData
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
        sociallogin.user.save()
        plan = SubscriptionPackage.objects.filter(can_change=False, subscription_period=SubscriptionPackage.SUBSCRIPTION_ONE_WEEK).first()
        obj = ClientCreditSubscription.objects.create(client=sociallogin.user, plan=plan)
        if obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_TWELVE_MONTH:
            obj.expire_date = timezone.now() + relativedelta(months=12)
        if obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_ONE_MONTH:
            obj.expire_date = timezone.now() + relativedelta(months=1)
        if obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_ONE_WEEK:
            obj.expire_date = timezone.now() + timezone.timedelta(days=6)
        obj.is_activated = True
        ClientCreditSubscription.objects.filter(client=obj.client).update(is_activated=False, expire_date=timezone.now())
        helper_class = CreateSubscriptionData(obj, request)
        obj = helper_class.create_data()    
        obj.save()
        helper_class.create_sub_transactions()
        sociallogin.save(request)        
        sociallogin.user.send_email_to_admins(request)
        
        return u
        