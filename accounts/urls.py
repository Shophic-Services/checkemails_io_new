'''
Url for web views
'''
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path, reverse_lazy

from accounts.views.web import (ChangePasswordRequestView, AccountUpdateView, 
                                ForgotPasswordRequestView, UserSignupView,
                                ForgotPasswordTemplateView, HomeView, UserOTPView,
                                PasswordResetView, SetPasswordTemplateView,
                                SetPasswordView, UserLoginView)

app_name = 'accounts'

urlpatterns = [
    path('home/', HomeView.as_view(), name='home'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('signup/', UserSignupView.as_view(), name='signup'),
    path('otp/<uuid:token>/', UserOTPView.as_view(), name='otp'),
    path('otp/', UserOTPView.as_view(), name='otp'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page=reverse_lazy('accounts:login'),
    ), name='logout'),
    re_path(
        r'^set-password/(?P<template_type>expired|done)/$',
        SetPasswordTemplateView.as_view(), name="set_password_template"
    ),
    path('set-password/<uuid:token>/', SetPasswordView.as_view(), name='set_password'),
    re_path(
        r'^forgot-password/(?P<template_type>expired|done|email-sent)/$',
        ForgotPasswordTemplateView.as_view(), name="forgot_password_template"
    ),
    path('forgot-password/reset/<uuid:token>/', PasswordResetView.as_view(), name='forgot_password_reset'),
    path('forgot-password/', ForgotPasswordRequestView.as_view(), name='forgotpassword'),
    path('profile/', AccountUpdateView.as_view(), name='account-update'),
    path('change-password/', ChangePasswordRequestView.as_view(), name='changepassword'),
]
