from django.urls import path

from tools.api_base.api import (BulkValidationDeleteAPIView, SingleValidationAPIView, 
                                BulkValidationAPIView, SingleValidationHistoryView, 
                                BulkValidationListAPIView, WebsiteValidationDetailAPIView, 
                                WebsiteValidationListAPIView, WebsiteValidationDeleteAPIView,
                                WebsiteValidationAPIView, BulkValidationDetailAPIView)

# Base is current version v6

''' Tools version urls '''

app_name = 'tools_api'

urlpatterns = [
    path('single-validation/', SingleValidationAPIView.as_view(), name="single_validation"),
    path('single-validation-history/', SingleValidationHistoryView.as_view(), name="single_validation_history"),
    path('bulk-validation/', BulkValidationAPIView.as_view(), name="bulk_validation"),
    path('bulk-validation-list/', BulkValidationListAPIView.as_view(), name="bulk_validation_list"),
    path('bulk-detail-list/', BulkValidationDetailAPIView.as_view(), name="bulk_validation_detail_list"),
    path(
        "bulk-validation/<uuid:uuid>/delete/",
        BulkValidationDeleteAPIView.as_view(),
        name="bulk-validation-delete"
    ),
    path('website-validation-list/', WebsiteValidationListAPIView.as_view(), name="website_validation_list"),
    path('website-detail-list/', WebsiteValidationDetailAPIView.as_view(), name="website_validation_detail_list"),
    path('website-validation/', WebsiteValidationAPIView.as_view(), name="website_validation"),
    path(
        "website-validation/<uuid:uuid>/delete/",
        WebsiteValidationDeleteAPIView.as_view(),
        name="website-validation-delete"
    ),

]