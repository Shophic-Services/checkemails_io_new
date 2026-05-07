from django.urls import path, include
from tools.views.web import (SingleValidationView, DashBoard, BulkValidationView, 
                            SpamCheckView, WebsiteFetcherDetailView, BulkValidationDetailView,
                            ReverseLookupView, WebsiteFetcherView, LeadFinderView)
from tools.views.ajax import (FileUploadView, ProcessEmailView, ValidationInitiateView, 
                              ReportExportView, ExtractionInitiateView, ProcessWebsiteView,
                              WebsiteExportView)

app_name = 'tools'
urlpatterns = [
    path('dashboard/', DashBoard.as_view(), name='dashboard'),
    path('tools/single-validation/', SingleValidationView.as_view(), name='single_validation'),
    path('tools/bulk-validation/', BulkValidationView.as_view(), name='bulk_validation'),
    path('tools/bulk-validation/<uuid:list_id>/', BulkValidationDetailView.as_view(), name='bulk_validation_detail'),
    path('tools/spam-check/', SpamCheckView.as_view(), name='spam_check'),
    path('tools/reverse-lookup/', ReverseLookupView.as_view(), name='reverse_lookup'),
    path('tools/website-fetcher/', WebsiteFetcherView.as_view(), name='website_fetcher'),
    path('tools/website-fetcher/<uuid:website_id>/', WebsiteFetcherDetailView.as_view(), name='website_fetcher_detail'),
    path('tools/lead-finder/', LeadFinderView.as_view(), name='lead_finder'),
    path('ajax/file-upload/', FileUploadView.as_view(), name='file_upload'),
    path('ajax/process-emails/', ProcessEmailView.as_view(), name='process_emails'),
    path('ajax/process-websites/', ProcessWebsiteView.as_view(), name='process_websites'),
    path('ajax/initiate-validation/', ValidationInitiateView.as_view(), name='initiate-validation'),
    path('ajax/initiate-extraction/', ExtractionInitiateView.as_view(), name='initiate-extraction'),
    path('ajax/report-export/', ReportExportView.as_view(), name='report-export'),
    path('ajax/website-export/', WebsiteExportView.as_view(), name='website-export'),
    
    
]