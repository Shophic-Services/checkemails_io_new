from django.conf import settings
from django.urls import path
from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import (
    AdminPasswordChangeForm, 
)
from django.utils.html import format_html
from accounts.proxy_models import ClientUser, ManagerUser, TeamUser
from app.models import EmailMessage

from checkemails.core.admin import CheckEmailsBaseModelAdmin
from checkemails.core.admin_list_filters import UserRoleListFilter
from subscription.models import SubscriptionPackage
from .models import User, UserToken
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from accounts.admin_forms import ClientChangeForm, ClientCreationForm, TeamChangeForm, TeamCreationForm, UserCreationForm, UserChangeForm


from .models import *


# @admin.register(User)
# class UserAdmin(VersionAdmin):
#     pass

csrf_protect_m = method_decorator(csrf_protect)
sensitive_post_parameters_m = method_decorator(sensitive_post_parameters())


class UserAdmin(CheckEmailsBaseModelAdmin):
    def action_button(self, obj):
        change_url = reverse(
                'admin:%s_%s_change' % (self.model._meta.app_label, self.model._meta.model_name), 
                args=[force_str(obj.pk)]
            )
        delete_url = reverse(
                'admin:%s_%s_delete' % (self.model._meta.app_label, self.model._meta.model_name), 
                args=[force_str(obj.pk)]
            )
        return format_html('<a class="changelink" href="{}"></a> <a class="deletelink" href="{}"></a>', change_url, delete_url)

    action_button.short_description = 'Action'
    add_form_template = 'admin/auth/user/add_form.html'
    change_user_password_template = None
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name','user_role','referral_code')}),
        (_('Permissions'), {'fields': ('is_active',)}),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        (_('Personal info'), {'fields': ('first_name', 'last_name','user_role')}),
        (_('Permissions'), {'fields': ('is_active',)}),
    )
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ( 'email', 'first_name', 'last_name', 'is_active','action_button')
    list_filter = ('is_active',)
    search_fields = ( 'first_name', 'last_name', 'email')
    readonly_fields = ('last_login','google_user')
    list_display_links = None

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(UserAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super(UserAdmin, self).get_form(request, obj, **defaults)

    def get_urls(self):
        return [
            path(
                "<id>/password/",
                self.admin_site.admin_view(self.user_change_password),
                name="auth_user_password_change",
            ),
        ] + super().get_urls()

    def lookup_allowed(self, lookup, value):
        # See #20078: we don't want to allow any lookups involving passwords.
        if lookup.startswith('password'):
            return False
        return super(UserAdmin, self).lookup_allowed(lookup, value)

    @sensitive_post_parameters_m
    @csrf_protect_m
    @transaction.atomic
    def add_view(self, request, form_url='', extra_context=None):
        # It's an error for a user to have add permission but NOT change
        # permission for users. If we allowed such users to add users, they
        # could create superusers, which would mean they would essentially have
        # the permission to change users. To avoid the problem entirely, we
        # disallow users from adding users if they don't have change
        # permission.
        if not self.has_change_permission(request):
            if self.has_add_permission(request) and settings.DEBUG:
                # Raise Http404 in debug mode so that the user gets a helpful
                # error message.
                raise Http404(
                    'Your user does not have the "Change user" permission. In '
                    'order to add users, Django requires that your user '
                    'account have both the "Add user" and "Change user" '
                    'permissions set.')
            raise PermissionDenied
        if extra_context is None:
            extra_context = {}
        username_field = self.model._meta.get_field(self.model.USERNAME_FIELD)
        defaults = {
            'auto_populated_fields': (),
            'username_help_text': username_field.help_text,
        }
        extra_context.update(defaults)
        return super(UserAdmin, self).add_view(request, form_url,
                                               extra_context)

    @sensitive_post_parameters_m
    def user_change_password(self, request, id, form_url=''):
        if not self.has_change_permission(request):
            raise PermissionDenied
        user = self.get_object(request, unquote(id))
        if user is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {
                'name': force_str(self.model._meta.verbose_name),
                'key': escape(id),
            })
        if request.method == 'POST':
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                change_message = self.construct_change_message(
                    request, form, None)
                self.log_change(request, user, change_message)
                msg = _('Password changed successfully.')
                messages.success(request, msg)
                update_session_auth_hash(request, form.user)
                return HttpResponseRedirect('..')
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {'fields': list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            'title': _('Change password: %s') % escape(user.get_username()),
            'adminForm': adminForm,
            'form_url': form_url,
            'form': form,
            'is_popup': (IS_POPUP_VAR in request.POST or
                         IS_POPUP_VAR in request.GET),
            'add': True,
            'change': False,
            'has_delete_permission': True,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': user,
            'save_as': False,
            'show_save': True,
        }
        context.update(admin.site.each_context(request))

        request.current_app = self.admin_site.name

        return TemplateResponse(request,
                                self.change_user_password_template or
                                'admin/auth/user/change_password.html',
                                context)

    def response_add(self, request, obj, post_url_continue=None):
        """
        Determines the HttpResponse for the add_view stage. It mostly defers to
        its superclass implementation but is customized because the User model
        has a slightly different workflow.
        """
        # We should allow further modification of the user just added i.e. the
        # 'Save' button should behave like the 'Save and continue editing'
        # button except in two scenarios:
        # * The user has pressed the 'Save and add another' button
        # * We are adding a user in a popup
        if '_addanother' not in request.POST and IS_POPUP_VAR not in request.POST:
            _mutable = request.POST._mutable
            request.POST._mutable = True
            request.POST['_continue'] = 1
            request.POST._mutable = _mutable
        return super(UserAdmin, self).response_add(request, obj,
                                                   post_url_continue)

    def save_model(self, request, obj, form, change):
        """
        Save Model method for model admin
        """
        obj.is_staff = True
        if obj and obj.user_role and obj.user_role.role == UserRole.CLIENT:
            obj.is_staff = False
            
        result = super(UserAdmin, self).save_model(request, obj, form, change)
        return result

    def get_queryset(self, request):
        initial_queryset = super(UserAdmin, self).get_queryset(request)
        # All staff who belong to the current reseller or direct model
        final_queryset = initial_queryset.filter(user_role__role__in=[UserRole.MANAGER], is_deleted=False)   
        return final_queryset

class ClientAdmin(UserAdmin):
    
    list_filter = ('is_active',)
    form = ClientChangeForm
    add_form = ClientCreationForm
    
    list_display = ( 'email', 'first_name', 'last_name', 'is_active','google_user','get_impersonate','action_button')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name','user_role','phone','referral_code')}),
        (_('Plan info'), {'fields': ('get_plan_name',)}),
        (_('Permissions'), {'fields': ('is_active','google_user')}),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        (_('Personal info'), {'fields': ('first_name', 'last_name','user_role','phone', )}),
        (_('Permissions'), {'fields': ('is_active',)}),
    )
    def get_queryset(self, request):
        initial_queryset = User.objects.filter(user_role__role__in=[UserRole.CLIENT], is_deleted=False)   
        return initial_queryset

    def get_readonly_fields(self, request, obj=None):
        _ = self
        if obj: 
            if obj.socialaccount_set.all():
                return self.readonly_fields + ('email','get_plan_name','referral_code')
            return self.readonly_fields + ('get_plan_name','referral_code')
        else:
            return self.readonly_fields
    
    
    def get_plan_name(self, obj):
        _ = self
        return SubscriptionPackage.objects.filter(id=obj.plan_id).first()
    get_plan_name.short_description = 'Plan'
    get_plan_name.allow_tags = True

    
    def get_impersonate(self, obj):
        _ = self
        if obj.is_active:
            return format_html('<a class="loginlink" href="/impersonate/stop/?next=/impersonate/{}/"></a>', obj.pk)
    get_impersonate.short_description = 'Login'
    get_impersonate.allow_tags = True

class TeamAdmin(UserAdmin):
    
    list_filter = ('is_active',)
    form = TeamChangeForm
    add_form = TeamCreationForm
    
    def get_queryset(self, request):
        initial_queryset = User.objects.filter(user_role__role__in=[UserRole.TEAM], is_deleted=False)    
        return initial_queryset

admin.site.register(ManagerUser, UserAdmin)
admin.site.register(ClientUser, ClientAdmin)
admin.site.register(TeamUser, TeamAdmin)
admin.site.register(EmailMessage)
# admin.site.register(User, UserAdmin)
