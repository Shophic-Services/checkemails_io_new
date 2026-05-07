'''
Api requests for assessments module
'''
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from tools import constants
from rest_framework.renderers import TemplateHTMLRenderer
from tools.models import DataSourceJob, EmailData, DataSourceJob, DataSourceItem, ScraperResult
from tools.api_base.serializers import BulkStatusRequestSerializer, DataSourceJobSerializer, ScraperJobSerializer, ScraperResultSerializer, SingleValidationHistorySerializer, SingleValidationSerializer
from subscription.models import ClientCreditSubscription
from rest_framework.pagination import PageNumberPagination, CursorPagination
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import F
from django.contrib.contenttypes.models import ContentType

class SingleValidationAPIView(views.APIView):

    permission_classes = [permissions.IsAuthenticated]

    def create_single_job_and_item(self, email: str):
        job = DataSourceJob.objects.create(
            name=f"Single verification – {email}",

            source_type=constants.SINGLE, 
            source_format="single email",

            status=DataSourceJob.STARTED,

            total_items=1,
            upload_completed=True,

            started_at=timezone.now(),
            input_references=[email],
            added_by=self.request.user,
            belongs_to=self.request.user,
        )

        item = DataSourceItem.objects.create(
            source_job=job,
            input_value=email,

            status=DataSourceItem.STARTED,
            added_by=self.request.user,
            belongs_to=self.request.user,
        )

        return job, item
    
    def mark_item_inprogress(self, item: DataSourceItem):
        item.status = DataSourceItem.INPROGRESS
        item.save(update_fields=["status"])

    def save_failure(self, job, item):
        item.status = DataSourceItem.FAILED
        item.save(update_fields=["status"])

        DataSourceJob.objects.filter(pk=job.pk).update(
            status=DataSourceJob.ERROR,
            completed_at=timezone.now(),
        )

    def save_success(self, job, item, result):
        email, is_role_based, has_domain_mx, has_spf, has_dmarc, status, quality, email_result, valid, email_source, catch_all, email_type, code, message, errors, retry_later, permanent_failure, needs_manual_review, has_smtp = result
        result_data = {
            'email': email, 
            'is_role_based': is_role_based, 
            'has_domain_mx': has_domain_mx, 
            'has_spf': has_spf, 
            'has_smtp': has_smtp,
            'has_dmarc': has_dmarc, 
            'status': status, 
            'quality': quality, 
            'email_result': email_result,
            'valid': valid, 
            'email_source': email_source, 
            'catch_all': catch_all, 
            'email_type': email_type,
            'code': code, 'message': str(message), 'errors': str(errors),  
            'retry_later': retry_later, 
            'permanent_failure': permanent_failure, 
            'needs_manual_review': needs_manual_review
            }
        result = {
                "email": item.input_value,
                "result": email_result,
                "quality": quality,
                "check": {
                    "catch_all":  {
                        "message":'',
                        "valid": catch_all
                        },
                    "role_based":  {
                        "message":'',
                        "valid": is_role_based
                        },
                    "domain": {
                        "message":'',
                        "valid": has_domain_mx
                        },
                    "type":  {
                        "message":'',
                        "code": email_type
                        }
                }
            }
        item.status = DataSourceItem.COMPLETED
        item.result_data = result_data
        item.save(update_fields=["status", "result_data"])

        valid_count = invalid_count = role_count = catch_all_count = 0
        disposable_count = unknown_count = syntax_invalid_count = 0
        risky_count = 0

        if quality == EmailData.RISKY:
            risky_count +=1
        elif valid:
            valid_count += 1
        elif quality == EmailData.UNKNOWN:
            unknown_count += 1
        else:
            invalid_count += 1

        if catch_all:
            catch_all_count += 1
        if is_role_based:
            role_count += 1

        if email_type == EmailData.DISPOSABLE:
            disposable_count += 1
        elif email_type == EmailData.SYNTAX_ERROR:
            syntax_invalid_count += 1

        DataSourceJob.objects.filter(pk=job.pk).update(
        completed_count=F("completed_count") + 1,
        status=DataSourceJob.COMPLETED,
        completed_at=timezone.now(),
        valid_count=F("valid_count") + valid_count,
        risky_count=F("risky_count") + risky_count,
        invalid_count=F("invalid_count") + invalid_count,
        role_based_count=F("role_based_count") + role_count,
        catch_all_count=F("catch_all_count") + catch_all_count,
        disposable_count=F("disposable_count") + disposable_count,
        unknown_count=F("unknown_count") + unknown_count,
        syntax_invalid_count=F("syntax_invalid_count") + syntax_invalid_count)

        return result

    def post(self, request, format=None):

        job, item = self.create_single_job_and_item(request.data.get('email'))

        self.mark_item_inprogress(item)

        try:
            active_subscription = ClientCreditSubscription.objects.filter(client=request.user, is_activated=True).order_by("-create_date").first()
            if active_subscription:
                active_subscription_credit = active_subscription.credit_balance or 0
                if (active_subscription_credit - active_subscription.credit_reserved) < 1: 
                    self.save_failure(job, item)
                    return Response(
                        {
                            "status": status.HTTP_400_BAD_REQUEST,
                            "message": 'Error validating'
                        },
                        status=400
                    )

            serializer = SingleValidationSerializer(data=request.data, context={'request': self.request})
            serializer.is_valid(raise_exception=True)
            result = serializer.save()
            result = self.save_success(job, item, result)
            
            credit_balance = None
            credit_reserved = None
            check = result.get('check') or {}

            type_code = check.get('type', {}).get('code')
            is_valid = result.get('valid')
            credit_detuct = False
            if type_code == EmailData.RISKY:
                credit_detuct = True
            elif is_valid:
                credit_detuct = True
            elif type_code == EmailData.UNKNOWN:
                credit_detuct = False
            else:
                credit_detuct = True
                
            if active_subscription: 
                active_subscription.credit_balance -=  1 if credit_detuct else 0
                active_subscription.save()
                credit_balance = active_subscription.credit_balance
                credit_reserved = active_subscription.credit_reserved
            result.update({
                'credit_balance': credit_balance,
                'credit_reserved': credit_reserved,
            })
            return Response(result, status=status.HTTP_200_OK)

        except ValidationError as e:
            error = next(iter(e.detail.values()))[0]
            self.save_failure(job, item)
            return Response(
                {
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": error
                },
                status=400
            )
    

class BulkValidationAPIView(generics.GenericAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # 1️⃣ Validate request payload
        request_serializer = BulkStatusRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        job_ids = request_serializer.validated_data['job_ids']

        # 2️⃣ Query only required records
        jobs = (
            DataSourceJob.objects
            .filter(uuid__in=job_ids, source_type=constants.BULK)
            .only(
                'uuid',
                'name',
                'status',
                'total_items',
                'completed_count',
                'valid_count',
                'invalid_count',
                'unknown_count',
                'role_based_count',
                'disposable_count',
                'catch_all_count',
                'total_duplicate',
                'source_format',
                'started_at',
                'completed_at',
            )
        )

        # 3️⃣ Serialize response
        serializer = DataSourceJobSerializer(jobs, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "current": self.page.number,
            "total_pages": self.page.paginator.num_pages,
            "next": self.page.next_page_number() if self.page.has_next() else None,
            "previous": self.page.previous_page_number() if self.page.has_previous() else None,
            "results": data,
        })

class SingleValidationHistoryView(generics.ListAPIView):
    serializer_class = SingleValidationHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        
        qs = (
            DataSourceItem.objects
            .filter(source_job__source_type=constants.SINGLE, added_by=self.request.user)
            .order_by('-id')
        )

        data = self.request.data

        search = data.get('search')
        if search:
            qs = qs.filter(content_object__email__icontains=search)

        sort_field = data.get('sort_field', 'id')
        sort_order = data.get('sort_order', 'desc')

        if sort_order == 'desc':
            sort_field = f"-{sort_field}"

        qs = qs.order_by(sort_field)

        return qs

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
    
class BulkValidationListAPIView(generics.ListAPIView):
    serializer_class = DataSourceJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "components/bulk-list.html"

    PAGE_SIZE = 10

    def get_queryset(self):
        qs = (
            DataSourceJob.objects
            .filter(source_type=constants.BULK, added_by=self.request.user)
            .order_by("-create_date")
        )

        status = self.request.GET.get("status", "ALL")

        status_map = DataSourceJob.STATUS_MAP

        if status in status_map and status_map[status]:
            qs = qs.filter(status__in=status_map[status])

        return qs

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        paginator = Paginator(queryset, self.PAGE_SIZE)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # limit page numbers to max 5
        current = page_obj.number
        start = max(current - 2, 1)
        end = min(current + 2, paginator.num_pages)

        page_range = range(start, end + 1)
        serializer = self.get_serializer(page_obj, many=True)

        return Response({
            "verification_list": serializer.data,  # iterable
            "page_obj": page_obj,
            "paginator": paginator,
            "page_range": page_range,
            "total_count": paginator.count,
            "current_status": status,
        })
    

class BulkValidationDetailAPIView(generics.ListAPIView):
    serializer_class = SingleValidationHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "components/bulk-detailed-list.html"

    PAGE_SIZE = 10

    def get_queryset(self):
        bulk_id = self.request.data.get('bulk_id')
        qs = (
            DataSourceItem.objects
            .filter(source_job__uuid=bulk_id, source_job__source_type=constants.BULK)
            .order_by("create_date")
        )

        return qs
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        page_number = request.GET.get("page", 1)

        paginator = Paginator(queryset, self.PAGE_SIZE)
        page_obj = paginator.get_page(page_number)

        serializer = self.get_serializer(page_obj, many=True)

        # page range (max 5 pages)
        current = page_obj.number
        total_pages = paginator.num_pages

        start = max(current - 2, 1)
        end = min(current + 2, total_pages)

        page_range = range(start, end + 1)

        return Response({
            "bulk_report_data": serializer.data,
            "page_obj": page_obj,
            "total_count": paginator.count,
            "page_range": page_range,
        })

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
    


class WebsiteValidationDetailAPIView(generics.ListAPIView):
    serializer_class = ScraperResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "components/website-detailed-list.html"

    PAGE_SIZE = 10

    def get_queryset(self):
        bulk_id = self.request.data.get('website_id')
        qs = (
            ScraperResult.objects
            .filter(source_job__uuid=bulk_id, source_job__source_type=constants.WEBSITE)
            .order_by("create_date")
        )

        return qs
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        page_number = request.GET.get("page", 1)

        paginator = Paginator(queryset, self.PAGE_SIZE)
        page_obj = paginator.get_page(page_number)

        serializer = self.get_serializer(page_obj, many=True)

        # page range (max 5 pages)
        current = page_obj.number
        total_pages = paginator.num_pages

        start = max(current - 2, 1)
        end = min(current + 2, total_pages)

        page_range = range(start, end + 1)

        return Response({
            "website_report_data": serializer.data,
            "page_obj": page_obj,
            "total_count": paginator.count,
            "page_range": page_range,
        })

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
    
class WebsiteValidationListAPIView(generics.ListAPIView):
    serializer_class = DataSourceJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "components/website-list.html"

    PAGE_SIZE = 10

    def get_queryset(self):
        qs = (
            DataSourceJob.objects
            .filter(source_type=constants.WEBSITE, added_by=self.request.user)
            .order_by("-create_date")
        )

        status = self.request.GET.get("status", "ALL")

        status_map = DataSourceJob.STATUS_MAP

        if status in status_map and status_map[status]:
            qs = qs.filter(status__in=status_map[status])

        return qs

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        paginator = Paginator(queryset, self.PAGE_SIZE)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # limit page numbers to max 5
        current = page_obj.number
        start = max(current - 2, 1)
        end = min(current + 2, paginator.num_pages)

        page_range = range(start, end + 1)
        serializer = self.get_serializer(page_obj, many=True)

        return Response({
            "verification_list": serializer.data,  # iterable
            "page_obj": page_obj,
            "paginator": paginator,
            "page_range": page_range,
            "total_count": paginator.count,
            "current_status": status,
        })
    
class WebsiteValidationAPIView(generics.GenericAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # 1️⃣ Validate request payload
        request_serializer = BulkStatusRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        job_ids = request_serializer.validated_data['job_ids']

        # 2️⃣ Query only required records
        jobs = (
            DataSourceJob.objects
            .filter(uuid__in=job_ids, source_type=constants.WEBSITE)
            .only(
                'uuid',
                'name',
                'status',
                'total_items',
                'completed_count',
                'valid_count',
                'invalid_count',
                'unknown_count',
                'role_based_count',
                'disposable_count',
                'catch_all_count',
                'total_duplicate',
                'source_format',
                'started_at',
                'completed_at',
            )
        )

        # 3️⃣ Serialize response
        serializer = DataSourceJobSerializer(jobs, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

class BulkValidationDeleteAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, uuid, *args, **kwargs):
        job = get_object_or_404(
            DataSourceJob,
            uuid=uuid,
            source_type=constants.BULK
        )
        job.delete()
        return Response(
            {"message": "Bulk validation job deleted successfully"},
            status=status.HTTP_200_OK
        )
    

class WebsiteValidationDeleteAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, uuid, *args, **kwargs):
        job = get_object_or_404(
            DataSourceJob,
            uuid=uuid,
            source_type=constants.WEBSITE
        )
        job.delete()
        return Response(
            {"message": "Website validation job deleted successfully"},
            status=status.HTTP_200_OK
        )
    

