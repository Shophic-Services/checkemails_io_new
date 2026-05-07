
import json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from accounts.models import UserRole
from accounts.proxy_models import ClientUser, ManagerUser, TeamUser
from tools import constants
from tools.models import DataSourceItem, DataSourceJob, EmailData, ScraperResult, SpamKeyword, DataSourceJob
from tools.api_base.serializers import DataSourceJobSerializer, ScraperResultSerializer, SingleValidationHistorySerializer
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.functions import Cast
from django.db.models import DateTimeField, Max, Min, Sum, FloatField, F, CharField, Count, Q, DateField

from subscription.models import ClientCreditSubscription, SubscriptionPackage

class DashBoard(LoginRequiredMixin, TemplateView):
    template_name = 'tools/dashboard.html'

    def get_overall_breakdown(self, user):
        qs = DataSourceJob.objects.filter(
            added_by=user
        ).distinct()

        return qs.aggregate(
            total=Count('uuid'),

            deliverable=Sum('valid_count'),
            invalid=Sum('invalid_count'),
            disposable=Sum('disposable_count'),
            unknown=Sum('unknown_count'),
            syntax=Sum('syntax_invalid_count'),
            catch_all=Sum('catch_all_count'),
        )


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        overall_breakdown = self.get_overall_breakdown(self.request.user)

        overall_breakdown_data = {
            "total": overall_breakdown["total"],
            "items": [
                {
                    "key": "deliverable",
                    "label": "Deliverable",
                    "count": overall_breakdown["deliverable"],
                    "color": "#82ca9d",
                },
                {
                    "key": "catch_all",
                    "label": "Catch All",
                    "count": overall_breakdown["catch_all"],
                    "color": "#8884d8",
                },
                {
                    "key": "invalid",
                    "label": "Invalid",
                    "count": overall_breakdown["invalid"],
                    "color": "#ff8042",
                },
                {
                    "key": "unknown",
                    "label": "Unknown",
                    "count": overall_breakdown["unknown"],
                    "color": "#333333",
                },
                {
                    "key": "disposable",
                    "label": "Disposable",
                    "count": overall_breakdown["disposable"],
                    "color": "#ffbb28",
                },
                {
                    "key": "syntax",
                    "label": "Syntax",
                    "count": overall_breakdown["syntax"],
                    "color": "#d542ce",
                },
            ],
        }

        context = {
            'overall_breakdown': {
                    "total": overall_breakdown["total"],
                    "items": [
                        ("Deliverable", overall_breakdown["deliverable"], "#82ca9d"),
                        ("Invalid", overall_breakdown["invalid"], "#ff8042"),
                        ("Disposable", overall_breakdown["disposable"], "#ffbb28"),
                        ("Catch All", overall_breakdown["catch_all"], "#8884d8"),
                        ("Unknown", overall_breakdown["unknown"], "#333333"),
                        ("Syntax", overall_breakdown["syntax"], "#d542ce"),
                    ]
                },
            'overall_breakdown_data': overall_breakdown_data,
            'total_bulk': DataSourceJob.without_user.filter(source_type=constants.BULK, belongs_to=self.request.user).count(),
            'total_single': DataSourceJob.without_user.filter(source_type=constants.SINGLE, belongs_to=self.request.user).count(),
            'total_websites': DataSourceJob.without_user.filter(source_type=constants.WEBSITE, belongs_to=self.request.user).count(),
            'total_leads': DataSourceJob.without_user.filter(source_type=constants.LEAD, belongs_to=self.request.user).count(),
        }

        return context


class SingleValidationView(LoginRequiredMixin, TemplateView):
    template_name = 'tools/single-validation.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_number = self.request.GET.get('page', 1)

        queryset = (
            DataSourceItem.objects
            .filter(source_job__source_type=constants.SINGLE, added_by=self.request.user)
            .order_by('-id')
        )

        paginator = Paginator(queryset, self.paginate_by)

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = SingleValidationHistorySerializer(
            page_obj.object_list,
            many=True
        )

        current = page_obj.number
        total_pages = paginator.num_pages

        start_page = max(current - 2, 1)
        end_page = min(current + 2, total_pages)

        page_range = range(start_page, end_page + 1)

        context.update({
            'single_verification_history': serializer.data,
            'page_obj': page_obj,
            'paginator': paginator,
            'page_range': page_range,
            'total_count': paginator.count,
        })

        return context

class BulkValidationDetailView(LoginRequiredMixin, TemplateView):

    template_name = 'tools/email-list-detail.html'

    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        list_id = self.kwargs.get('list_id')

        try:
            job = DataSourceJob.objects.get(uuid=list_id, source_type=constants.BULK, added_by=self.request.user)
            context['job'] = DataSourceJobSerializer(job).data
        except DataSourceJob.DoesNotExist:
            job = DataSourceJob.objects.none()
            context['error'] = "Website fetcher job not found."

        page_number = self.request.GET.get('page', 1)
        queryset = (
            DataSourceItem.objects
            .filter(source_job=job)
            .order_by('create_date')
        )

        paginator = Paginator(queryset, self.paginate_by)

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = SingleValidationHistorySerializer(
            page_obj.object_list,
            many=True
        )

        current = page_obj.number
        total_pages = paginator.num_pages

        start_page = max(current - 2, 1)
        end_page = min(current + 2, total_pages)

        page_range = range(start_page, end_page + 1)
        context.update({

            'page_obj': page_obj,
            'paginator': paginator,
            'page_range': page_range,
            'total_count': paginator.count,
            'bulk_report_data': serializer.data
        })


        return context


class BulkValidationView(LoginRequiredMixin, TemplateView):
    template_name = 'tools/bulk-validation.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_number = self.request.GET.get('page', 1)

        queryset = (
            DataSourceJob.objects
            .filter(source_type=constants.BULK, added_by=self.request.user)
            .order_by('-create_date')
        )

        paginator = Paginator(queryset, self.paginate_by)

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = DataSourceJobSerializer(
            page_obj.object_list,
            many=True
        )

        current = page_obj.number
        total_pages = paginator.num_pages

        start_page = max(current - 2, 1)
        end_page = min(current + 2, total_pages)

        page_range = range(start_page, end_page + 1)
        TABS = [
            "ALL",
            "COMPLETED",
            "PROCESSING",
            "UNPROCESSED",
            "FAILED",
        ]
        context.update({
            'verification_list': serializer.data,
            'page_obj': page_obj,
            'paginator': paginator,
            'page_range': page_range,
            'total_count': paginator.count,
            "current_status":'ALL',
            "status_tabs": TABS,
        })

        return context

class SpamCheckView(LoginRequiredMixin, TemplateView):
    template_name = 'tools/spam-checker.html'

    def get_context_data(self, **kwargs):
        context = super(SpamCheckView, self).get_context_data(**kwargs)
        spamcategory = list(SpamKeyword.objects.all().values('keyword',category_title=F('category__title'), highlight=F('regex_pattern')))
        spamcategory_json_array = json.dumps(spamcategory)
        
        context.update({
            
            'spamcategory':spamcategory_json_array,
        })
            
        return context


class ReverseLookupView(LoginRequiredMixin, TemplateView):
    template_name = 'tools/reverse-lookup.html'

class WebsiteFetcherDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'tools/website-fetcher-detail.html'

    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        website_id = self.kwargs.get('website_id')

        try:
            job = DataSourceJob.objects.get(uuid=website_id, source_type=constants.WEBSITE, added_by=self.request.user)
            context['job'] = DataSourceJobSerializer(job).data
        except DataSourceJob.DoesNotExist:
            job = DataSourceJob.objects.none()
            context['error'] = "Website fetcher job not found."
        page_number = self.request.GET.get('page', 1)

        queryset = (
            ScraperResult.objects.filter(
                    source_job=job,
                )
            .order_by('create_date')
        )

        paginator = Paginator(queryset, self.paginate_by)

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)


        current = page_obj.number
        total_pages = paginator.num_pages

        start_page = max(current - 2, 1)
        end_page = min(current + 2, total_pages)

        page_range = range(start_page, end_page + 1)
        
        website_report_data = ScraperResultSerializer(
            page_obj.object_list,
            many=True
        )
        context.update({

            'page_obj': page_obj,
            'paginator': paginator,
            'page_range': page_range,
            'total_count': paginator.count,
            'website_report_data': website_report_data.data
        })


        return context

class WebsiteFetcherView(LoginRequiredMixin, TemplateView):
    template_name = 'tools/website-fetcher.html'
    
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_number = self.request.GET.get('page', 1)

        queryset = (
            DataSourceJob.objects
            .filter(source_type=constants.WEBSITE, added_by=self.request.user)
            .order_by('-create_date')
        )

        paginator = Paginator(queryset, self.paginate_by)

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = DataSourceJobSerializer(
            page_obj.object_list,
            many=True
        )

        current = page_obj.number
        total_pages = paginator.num_pages

        start_page = max(current - 2, 1)
        end_page = min(current + 2, total_pages)

        page_range = range(start_page, end_page + 1)
        TABS = [
            "ALL",
            "COMPLETED",
            "PROCESSING",
            "UNPROCESSED",
            "FAILED",
        ]
        context.update({
            'verification_list': serializer.data,
            'page_obj': page_obj,
            'paginator': paginator,
            'page_range': page_range,
            'total_count': paginator.count,
            "current_status":'ALL',
            "status_tabs": TABS,
        })

        return context

    
class LeadFinderView(LoginRequiredMixin, TemplateView):
    template_name = 'tools/lead-finder.html'

