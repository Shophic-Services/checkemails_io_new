try:
    # we use django.urls import as version detection as it will fail on django 1.11 and thus we are safe to use
    # gettext_lazy instead of ugettext_lazy instead
    from django.urls import reverse
    from django.utils.translation import gettext_lazy as _
except ImportError:
    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext_lazy as _
from admin_tools.dashboard import Dashboard, AppIndexDashboard
from admin_tools.dashboard import modules
from accounts.models import User, UserRole
from django.urls import reverse_lazy


# to activate your index dashboard add the following to your settings.py:
#
# ADMIN_TOOLS_INDEX_DASHBOARD = 'test_proj.dashboard.CustomIndexDashboard'

class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard.
    """
    columns = 5


    def __init__(self, **kwargs):

        Dashboard.__init__(self, **kwargs)


        total_managers = User.objects.filter(user_role__role=UserRole.MANAGER).count()
        total_clients = User.objects.filter(user_role__role=UserRole.CLIENT).count()
        total_team = User.objects.filter(user_role__role=UserRole.TEAM).count()
        
        self.children.append(modules.LinkList(
            _('Total Managers'),
            layout='inline',
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                [_(str(total_managers)), reverse_lazy('admin:accounts_manageruser_changelist')],
            ]
        ))
        self.children.append(modules.LinkList(
            _('Total Teams'),
            layout='inline',
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                [_(str(total_team)), reverse_lazy('admin:accounts_teamuser_changelist')],
            ]
        ))
        self.children.append(modules.LinkList(
            _('Total Clients'),
            layout='inline',
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                [_(str(total_clients)), reverse_lazy('admin:accounts_clientuser_changelist')],
            ]
        ))
        

