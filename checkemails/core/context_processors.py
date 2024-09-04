from django.conf import settings
from accounts.models import UserRole, User
from checkemails.core import constants

def load_user_data(request):
    return {
        'request': request,
        'UserRole': UserRole,
        'User': User,
        'current_user_role': request.user.user_role.role if 
            request.user.is_authenticated and request.user.user_role else None,
        'WEBAPP_NOCACHE_TOKEN': settings.WEBAPP_NOCACHE_TOKEN,
        'PAYPAL_CLIENT_ID': settings.PAYPAL_CLIENT_ID
    }
