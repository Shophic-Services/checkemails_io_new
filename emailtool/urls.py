from django.urls import path, include
from emailtool.views.web import (DashBoard, SingleEmailCheckView, 
                            MultiEmailCheckView, SpamEmailCheckView,
                            BulkEmailCheckView, ProcessEmailCheckView,
                            GenerateEmailCheckView, EmailCheckListView,
                            BulkProcessEmailCheckView)

app_name = 'emailtool'
urlpatterns = [
    path('', DashBoard.as_view(), name='app_dashboard'),
    path('single-email-check/', SingleEmailCheckView.as_view(), name='single_check'),
    path('multi-email-check/', MultiEmailCheckView.as_view(), name='multi_check'),
    path('spam-email-check/', SpamEmailCheckView.as_view(), name='spam_check'),
    path('bulk-email-check/', BulkEmailCheckView.as_view(), name='bulk_check'),
    path('bulk-process-email-check/<uuid:uuid>/', BulkProcessEmailCheckView.as_view(), name='bulk_process_check'),
    path('email-list/', EmailCheckListView.as_view(), name='email_check_list'),
    path('process-email-list/<uuid:uuid>/', ProcessEmailCheckView.as_view(), name='process_check'),
    path('generate-email-list/', GenerateEmailCheckView.as_view(), name='generate_email_list'),
    
]