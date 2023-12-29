"""Project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.urls import path, include, re_path
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

from accounts.admin_forms import AdminPasswordResetForm, LoginAuthenticationForm

admin.site.site_title = 'Check Emails Data Management'
admin.site.site_header = 'Check Emails Data Management'
admin.site.index_title = 'Check Emails Data Management'
admin.site.login_form = LoginAuthenticationForm
admin.site.login_template = 'accounts/admin/admin_login.html'
# admin.site.site_url = None
# from accounts.views.web import DashboardView

urlpatterns = [
    # path('', RedirectView.as_view(pattern_name=settings.LOGIN_REDIRECT_URL)),
    path('console-admin/login/', RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)),
    path('console-admin/logout/', RedirectView.as_view(pattern_name=settings.DEFAULT_LOGOUT)),
    # path(
    #     'console-admin/password_reset/',
    #     auth_views.PasswordResetView.as_view(
    #         email_template_name='accounts/admin/admin_password_reset_email.html',
    #         subject_template_name='accounts/admin/admin_password_reset_subject.txt',
    #         form_class=AdminPasswordResetForm), name='admin_password_reset'
    # ),
    # path(
    #     'console-admin/password_reset/done/',
    #     auth_views.PasswordResetDoneView.as_view(),
    #     name='password_reset_done',
    # ),
    path('console-admin/', admin.site.urls),
    path('admin_tools/', include('admin_tools.urls')),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    # path(
    #     'reset/done/',
    #     auth_views.PasswordResetCompleteView.as_view(),
    #     name='password_reset_complete',
    # ),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('accounts/inactive/', RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)),
    path(
        "accounts/password/change/", RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)
    ),
    path("accounts/password/set/", RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)),
    # E-mail
    path("accounts/email/", RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)),
    path(
        "accounts/confirm-email/", RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)
    ),
    re_path(
        r"^accounts/confirm-email/(?P<key>[-:\w]+)/$", RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)
    ),
    # password reset
    path("accounts/password/reset/", RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)),
    path(
        "accounts/password/reset/done/", RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)
    ),
    re_path(
        r"^accounts/password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$", RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)
    ),
    path(
        "accounts/password/reset/key/done/", RedirectView.as_view(pattern_name=settings.DEFAULT_LOGIN)
    ),
    path('accounts/', include('allauth.urls')),
    path('', include('app.urls', namespace='app', )),
    
    path('check/', include('emailtool.urls', namespace='emailtool', )),    
    path('subscriptions/', include('subscription.urls', namespace='subscription')),
    path("ckeditor5/", include('django_ckeditor_5.urls'), name="ck_editor_5_upload_file"),
    
]


if settings.DEBUG:
    import debug_toolbar
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) +\
        static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

