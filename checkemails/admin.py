from celery.result import AsyncResult
from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path
from django.template.response import TemplateResponse
from accounts.models import UserRole
from accounts.proxy_models import ClientUser, ManagerUser, TeamUser
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from tools import constants
from tools.models import DataSourceJob


# Override admin index
class CheckEmailsAdminSite(admin.AdminSite):
    site_header = "Checkemails"
    site_title = "Checkemails"
    index_template = "admin/index.html"

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)

        APP_ORDER = {
            "Accounts": [
                "ManagerUser",
                "TeamUser",
                "ClientUser",
            ],

            "Tools": [
                "EmailData",
                "LeadFinder",
                "DataSourceJob",
                "SpamCategory",
            ],

            "Subscription": [
                "ClientRecord",
                "ClientCreditSubscription",
                "SubscriptionTransaction",
                "ReferralCode",
                "SubscriptionPackage",
            ],

            "Flat Pages": [
                "FlatPage",
            ],

            "Impersonate": [
                "ImpersonationLog",
            ],

            "Import Export Celery": [
                "ExportJob",
                "ImportJob",
            ],

            "Log": [
                "Log",
            ],
        }

        ordered_apps = []

        for app_name, model_order in APP_ORDER.items():
            for app in app_list:
                if app["name"] == app_name:
                    app["models"].sort(
                        key=lambda m: (
                            model_order.index(m["object_name"])
                            if m["object_name"] in model_order
                            else 999
                        )
                    )
                    ordered_apps.append(app)
                    break
                
        return ordered_apps
    

    @method_decorator(never_cache)
    def index(self, request, extra_context=None):
        """
        Display the main admin index page, which lists all of the installed
        apps that have been registered in this site.
        """
        extra_context = extra_context or {}

        from django.db.models.functions import Cast
        from django.db.models import DateTimeField, Max, Min, Sum, FloatField, F, CharField, Count, Q, DateField

        from subscription.models import ClientCreditSubscription, SubscriptionPackage
        sales_summary_queryset = ClientCreditSubscription.objects.filter(~Q(plan__subscription_period=SubscriptionPackage.SUBSCRIPTION_ONE_WEEK) & ~Q( amount=None))
        metrics = {
            'total': Count('id'),
            'total_sales': Sum(Cast('amount', output_field=FloatField())),
        }
        
        sales_summary = list(
            sales_summary_queryset
            .values('plan__name')
            .annotate(**metrics)
            .order_by('-total_sales')
        )
        sales_summary_total = dict(sales_summary_queryset.aggregate(**metrics))
        context = {
            **self.each_context(request),
            'manager_count': ManagerUser.objects.filter(user_role_id=UserRole.MANAGER).count(),
            'team_count': TeamUser.objects.filter(user_role_id=UserRole.TEAM).count(),
            'client_count': ClientUser.objects.filter(user_role_id=UserRole.CLIENT).count(),
            # 'recent_actions': [str(a) for a in self.get_recent_actions()],
            'sales_summary': sales_summary,
            'sales_summary_total': sales_summary_total,
            'total_bulk': DataSourceJob.without_user.filter(source_type=constants.BULK).count(),
            'total_single': DataSourceJob.without_user.filter(source_type=constants.SINGLE).count(),
            'total_websites': DataSourceJob.without_user.filter(source_type=constants.WEBSITE).count(),
            'total_leads': DataSourceJob.without_user.filter(source_type=constants.LEAD).count(),
            **extra_context,
            'is_nav_sidebar_enabled': True,
        }
        # context['app_list'] = context['available_apps']
        return TemplateResponse(request, self.index_template or 'admin/index.html', context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "task-status/<str:task_id>/",
                self.admin_view(self.admin_task_status_view),
                name="task_status",
            )
        ]
        return custom_urls + urls

    def admin_task_status_view(self, request, task_id):
        task = AsyncResult(task_id)
        task_data = {
            "id": task.id,
            "name": task.name,
            "args": task.args,
            "kwargs": task.kwargs,
            "state": task.state,
        }

        # Return JSON response if requested
        if request.headers.get("Accept", "").startswith("application/json"):
            return JsonResponse(task_data)

        # Otherwise, render HTML response
        return render(
            request,
            "admin/task_status.html",
            {
                "title": "Task Status",
                "task": task_data,
            },
        )
    

admin_site = CheckEmailsAdminSite(name='myadmin')