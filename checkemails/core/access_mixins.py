from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http.response import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from accounts.models import UserRole, User
from functools import update_wrapper
from django.conf import settings
from django.urls import path
from django.contrib import admin
from django.contrib.auth import login, load_backend
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy
from django.utils.html import format_html

class AdminRoleRequiredMixin(LoginRequiredMixin):
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if not (user.is_authenticated and user.is_staff):
            return HttpResponseRedirect(reverse_lazy(self.get_login_url()))
        else:
            return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)



class StaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if not (user.is_authenticated and (user.user_role or user.is_staff)):
            return HttpResponseRedirect(reverse_lazy(self.get_login_url()))
        else:
            return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)
