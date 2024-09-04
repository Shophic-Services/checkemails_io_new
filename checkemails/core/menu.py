try:
    # we use django.urls import as version detection as it will fail on django 1.11 and thus we are safe to use
    # gettext_lazy instead of ugettext_lazy instead
    from django.urls import reverse
    from django.utils.translation import gettext_lazy as _
except ImportError:
    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext_lazy as _
from admin_tools.menu import items, Menu

from accounts.models import UserRole

# to activate your custom menu add the following to your settings.py:
#
# ADMIN_TOOLS_MENU = 'test_proj.menu.CustomMenu'

class CustomMenu(Menu):
    """
    Custom Menu for test_proj admin site.
    """

    def __init__(self, **kwargs):
        Menu.__init__(self, **kwargs)
        self.children += [
            items.MenuItem(_('Dashboard'), reverse('admin:index')),
            items.AppList(
                _('Applications'),
                exclude=('django.contrib.*',)
            ),
        ]

    def init_with_context(self, context):
        """
        Use this method if you need to access the request context.
        """
        pass


def get_menus_by_user(request):
    user_type = request.user.user_role.role
    if user_type == UserRole.TEAM:
         return [
                    {
        "title": "Dashboard",
        "icon": "fa fa-home",
        "url": "/console-admin/",
    },{
                        "title": "Accounts",
                        "icon": "fa fa-cogs",
                        "children": [
                            {
                                "title": "Teams",
                                "icon": "fas fa-user",
                                "model": "accounts.teamuser",
                                "permissions": ["accounts.view_teamuser",],
                            }
                        ]
                    }
                ]
    else:
        return [
    {
        "title": "Dashboard",
        "icon": "fa fa-home",
        "url": "/console-admin/",
    },{
        "title": "Accounts",
        "icon": "fa fa-cogs",
        "children": [
            {
                "title": "Mangers",
                "icon": "fas fa-user",
                "model": "accounts.manageruser",
                "permissions": ["accounts.view_manageruser",],
            },
            {
                "title": "Teams",
                "icon": "fas fa-user",
                "model": "accounts.teamuser",
                "permissions": ["accounts.view_teamuser",],
            },
            {
                "title": "Clients",
                "icon": "fas fa-user",
                "model": "accounts.clientuser",
                "permissions": ["accounts.view_clientuser",],
            }
        ]
    },
   
   {
                        "title": "Master Records",
                        "icon": "fa fa-bars",
                        "children": [
                            
                            {
                                "title": "Spam Categories",
                                "icon": "far fa-file-alt",
                                "model": "emailtool.spamcategory",
                                "permissions": ["app.view_spamcategory",],
                            },
                            {
                                "title": "Email Search Data",
                                "icon": "far fa-file-alt",
                                "model": "emailtool.emailsearch",
                                "permissions": ["app.view_emailsearch",],
                            }
                        ]
                    },
                    {
        "title": "Credits",
        "icon": "fas fa-chart-line",
        "children": [
            {
                "title": "Plans",
                "icon": "fas fa-dollar-sign",
                "model": "subscription.subscriptionpackage",
                "permissions": ["subscription.view_subscriptionpackage",],
            },
            {
                "title": "Credit",
                "icon": "fas fa-dollar-sign",
                "model": "subscription.clientcreditsubscription",
                "permissions": ["subscription.view_clientcreditsubscription",],
            },
            # {
            #     "title": "Referral Code",
            #     "icon": "fas fa-qrcode",
            #     "model": "subscription.referralcode",
            #     "permissions": ["subscription.view_referralcode",],
            # }
        ]
    },
    
]