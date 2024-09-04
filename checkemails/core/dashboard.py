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
    columns = 3


    def __init__(self, **kwargs):

        Dashboard.__init__(self, **kwargs)


        total_managers = User.objects.filter(user_role__role=UserRole.MANAGER, is_deleted=False).count()
        total_clients = User.objects.filter(user_role__role=UserRole.CLIENT, is_deleted=False).count()
        total_team = User.objects.filter(user_role__role=UserRole.TEAM, is_deleted=False).count()
        
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
        from django.db.models.functions import Trunc
        from django.db.models.functions import Cast
        from django.db.models import DateTimeField, Max, Min, Sum, FloatField, F, CharField, Count, Q, DateField

        from subscription.models import ClientCreditSubscription, SubscriptionPackage
        qs = ClientCreditSubscription.objects.filter(~Q(plan__subscription_period=SubscriptionPackage.SUBSCRIPTION_ONE_WEEK) & ~Q( amount=None))
        metrics = {
            'total': Count('id'),
            'total_sales': Sum(Cast('amount', output_field=FloatField())),
        }
        
        self.summary = list(
            qs
            .values('plan__name')
            .annotate(**metrics)
            .order_by('-total_sales')
        )


        # List view summary

        self.summary_total = dict(qs.aggregate(**metrics))
        # period = get_next_in_date_hierarchy(request, self.date_hierarchy)
        # self.period = period
        summary_over_time = qs.annotate(
            period=Trunc(
                'activated_on',
                'day',
                output_field=DateField(),
            ),
        ).values('period').annotate(total=Sum(Cast('amount', output_field=FloatField()))).order_by('period')
        summary_range = summary_over_time.aggregate(
            low=Min('total'),
            high=Max('total'),
        )
        high = summary_range.get('high', 0)
        low = summary_range.get('low', 0)
        self.summary_over_time =  [{
            'period': x['period'],
            'total': x['total'] or 0,
            'pct': \
               ((x['total'] or 0) - low) / (high - low) * 100
               if high > low else 0,
        } for x in summary_over_time]
        
        

