from django.utils import timezone
from subscription.models import ClientCreditSubscription
from django.db.models import Q

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
            if not self.request.user.plan_id:
                user_current_plan = ClientCreditSubscription.objects.filter(client=user, expire_date__gte=timezone.now()).filter(Q(is_activated=True)|Q(is_current=True)).order_by('activated_on').first()
                self.request.user.plan_id = str(user_current_plan.plan_id) if user_current_plan else None
                self.request.user.save()
            plans = self.client_plans().filter(plan_id=self.request.user.plan_id,
                is_activated=True, is_current=True, expire_date__gt=timezone.now()
            ).filter(**query).order_by('activated_on', '-id')
            return plans
        return
    
    def get_active_plans(self, **kwargs):
        # A call to customer plans and filters as required 
        user = self.auth_user or self.request.user
        if user.is_authenticated:
            ClientCreditSubscription.objects.filter(client=self.request.user, expire_date__lte=timezone.now()).filter(Q(is_activated=True)|Q(is_current=True)).update(is_activated=False, is_current=False, expire_date=timezone.now())
        if user.is_authenticated and self.client_plans():
            plans = self.client_plans().filter(
                is_current=True, expire_date__gt=timezone.now()
            )
            return plans
        return

    

    def get_current_plan(self, **kwargs):
        # return the current plan of user
        plans = self.get_plans(**kwargs)
        current_plan = plans.first() if plans else None
        return current_plan