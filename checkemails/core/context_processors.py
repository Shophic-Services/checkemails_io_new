from django.conf import settings
from accounts.models import UserRole, User
from checkemails.core import constants
from subscription.models import ClientCreditSubscription

def load_user_data(request):
    active_subscription = None
    if request.user.is_authenticated:
        active_subscription = (
                ClientCreditSubscription.objects
                .filter(client=request.user)
                .order_by("-create_date")
            )
    return {
        'request': request,
        'UserRole': UserRole,
        'User': User,
        'current_user_role': request.user.user_role.role if 
            request.user.is_authenticated and request.user.user_role else None,
        # 'WEBAPP_NOCACHE_TOKEN': settings.WEBAPP_NOCACHE_TOKEN,
        'PAYPAL_CLIENT_ID': settings.PAYPAL_CLIENT_ID,
        'active_subscription': active_subscription.first() if active_subscription else None
    }
