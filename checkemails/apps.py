from django.contrib.admin.apps import AdminConfig

class CheckEmailsAdminConfig(AdminConfig):
    default_site = 'checkemails.admin.CheckEmailsAdminSite'