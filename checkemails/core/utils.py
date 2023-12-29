from django.utils import timezone
from subscription.models import ClientCreditSubscription


class SubscriptionValidations(object):
    ''' 
    Subscription validations helper class
    '''

    def __init__(self, request, user=None,**kwargs):
        self.request = request
        self.kwargs = kwargs
        self.auth_user = user


    def client_plans(self):
        # get all the plans
        user = self.auth_user or self.request.user
        plan_user = user 
        if user.is_authenticated:
            plans = plan_user.client_credits.all()
            return plans
        return

    def get_plans(self, **kwargs):
        # A call to customer plans and filters as required 
        user = self.auth_user or self.request.user
        if user.is_authenticated and self.client_plans():
            query = kwargs if kwargs else {}
            plans = self.client_plans().filter(
                is_activated=True, is_current=True, expire_date__gt=timezone.now()
            ).filter(**query).order_by('activated_on', '-id')
            return plans
        return

    

    def get_current_plan(self, **kwargs):
        # return the current plan of user
        plans = self.get_plans(**kwargs)
        current_plan = plans.first() if plans else None
        return current_plan