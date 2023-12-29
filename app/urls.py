from django.urls import path, include
from app.views.web import (CheckEmailsHome, PrivacyPolicyView, TNCView, ContactUsView, ConactUsSentView)

app_name = 'app'
urlpatterns = [
    path('', CheckEmailsHome.as_view(), name='home'),
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy'),
    path('tnc/', TNCView.as_view(), name='tnc'),
    path('contact-us/', ContactUsView.as_view(), name='contact_us'),
    path('contact-us/sent/', ConactUsSentView.as_view(), name='contact_us_sent'),
    
]