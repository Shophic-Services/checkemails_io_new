from django.urls import path, include
from emailtool.views.web import (BackupEmailSearchDeleteView, DashBoard, SingleEmailCheckView, 
                            MultiEmailCheckView, SpamEmailCheckView,
                            BulkEmailCheckView, ProcessEmailCheckView,
                            GenerateEmailCheckView, EmailCheckListView,
                            BulkProcessEmailCheckView, BulkProcessEmailListView,
                            FetchEmailCheckListView, GenerateFetchEmailCheckView, BackupEmailSearchView,
                            ProcessFetchEmailCheckView, BulkProcessFetchEmailListView)

app_name = 'emailtool'
urlpatterns = [
    path('', DashBoard.as_view(), name='app_dashboard'),
    path('single-email-check/', SingleEmailCheckView.as_view(), name='single_check'),
    path('multi-email-check/', MultiEmailCheckView.as_view(), name='multi_check'),
    path('spam-email-check/', SpamEmailCheckView.as_view(), name='spam_check'),
    path('bulk-email-check/', BulkEmailCheckView.as_view(), name='bulk_check'),
    path('bulk-process-email-check/<uuid:uuid>/', BulkProcessEmailCheckView.as_view(), name='bulk_process_check'),
    path('email-list/', EmailCheckListView.as_view(), name='email_check_list'),
    path('generate-email-list/', GenerateEmailCheckView.as_view(), name='generate_email_list'),
    path('process-email-list/<uuid:uuid>/', ProcessEmailCheckView.as_view(), name='process_list'),
    path('bulk-process-email-list/', BulkProcessEmailListView.as_view(), name='bulk_process_list'),
    path('bulk-process-email-list/<uuid:uuid>/', BulkProcessEmailListView.as_view(), name='bulk_process_list'),
    path('fetch-email-web-address/', FetchEmailCheckListView.as_view(), name='fetch_email_web_list'),
    path('generate-fetch-email-web/', GenerateFetchEmailCheckView.as_view(), name='generate_fetch_email_web'),
    path('process-fetch-email-web/<uuid:uuid>/', ProcessFetchEmailCheckView.as_view(), name='process_fetch_email_web'),
    path('bulk-process-fetch-email-list/', BulkProcessFetchEmailListView.as_view(), name='bulk_process_fetch_list'),
    path('bulk-process-fetch-email-list/<uuid:uuid>/', BulkProcessFetchEmailListView.as_view(), name='bulk_process_fetch_list'),
    path('backup-email-search-with-delete/', BackupEmailSearchDeleteView.as_view(), name='backup-email-search-delete'),
    path('backup-email-search/', BackupEmailSearchView.as_view(), name='backup-email-search'),
    
]