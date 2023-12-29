from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import forms as auth_forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.core.validators import RegexValidator
from django.contrib.sites.shortcuts import get_current_site

from accounts.proxy_models import ClientUser, TeamUser
from checkemails.core.widgets import CustomReadOnlyPasswordHashWidget
from .models import User, UserRole
from checkemails.core.validators import REGEX_MOBILE_NUMBER
from checkemails.core.email import Email
from app.middleware import get_current_user
from django.contrib.auth.forms import UserChangeForm, ReadOnlyPasswordHashField, UsernameField, UserCreationForm



class LoginAuthenticationForm(AdminAuthenticationForm):
    '''
    Form for implementing remember me on django admin login page
    '''
    remember_me = forms.BooleanField(
        label="Remember me", required=False, widget=forms.CheckboxInput())
    
    def clean(self):
        remember_me = self.cleaned_data.get('remember_me')
        self.cleaned_data['email'] = self.cleaned_data['username'].lower()
        if not remember_me:
            self.request.session.set_expiry(0)
        super(LoginAuthenticationForm, self).clean()

    

class UserCreationForm(UserCreationForm):
    
    class Meta:
        model = User
        fields = ('email','first_name', 'last_name','user_role','is_active')
        # field_classes = {'username': UsernameField}

    def __init__(self, *args, **kwargs):
        '''
        Makes user_role a mandatory field for staff creation
        '''
        super(UserCreationForm, self).__init__(*args, **kwargs)
        limitchoices = (
        ('','Select Role'),
        (UserRole.MANAGER, 'Manager')
        )
        if self.fields.get('user_role'):
            self.fields['user_role'].required = True
            self.fields['user_role'].choices = limitchoices

            
class ClientCreationForm(UserCreationForm):
    
    class Meta:
        model = ClientUser
        fields = '__all__'
        # field_classes = {'username': UsernameField}
        
    def __init__(self, *args, **kwargs):
        '''
        Makes user_role a mandatory field for staff creation
        '''
        super(ClientCreationForm, self).__init__(*args, **kwargs)
        limitchoices = (
        ('','Select Role'),
        (UserRole.CLIENT, 'Client'),
        )
        
        if self.fields.get('user_role'):
            self.fields['user_role'].required = True
            self.fields['user_role'].choices = limitchoices

class ReadOnlyPasswordHashField(ReadOnlyPasswordHashField):    
    widget = CustomReadOnlyPasswordHashWidget

class UserChangeForm(UserChangeForm):  
    password = ReadOnlyPasswordHashField(label=("Password"),
        help_text=(""
                    "<a class='changelink' href=\"{}\">Change password</a>"))  
    def __init__(self, *args, **kwargs):
        '''
        Makes user_role a mandatory field for staff creation
        '''
        super(UserChangeForm, self).__init__(*args, **kwargs)
        limitchoices = (
        ('','Select Role'),
        (UserRole.MANAGER, 'Manager')
        )
        if self.fields.get('user_role'):
            self.fields['user_role'].required = True
            self.fields['user_role'].choices = limitchoices

class ClientChangeForm(UserChangeForm):  

    class Meta:
        model = ClientUser
        fields = '__all__'
        field_classes = {'username': UsernameField}
    def __init__(self, *args, **kwargs):
        '''
        Makes user_role a mandatory field for staff creation
        '''
        super(ClientChangeForm, self).__init__(*args, **kwargs)
        limitchoices = (
        ('','Select Role'),
        (UserRole.CLIENT, 'Client')
        )
        if self.fields.get('user_role'):
            self.fields['user_role'].required = True
            self.fields['user_role'].choices = limitchoices

class TeamCreationForm(UserCreationForm):
    
    class Meta:
        model = TeamUser
        fields = ('email','first_name', 'last_name','user_role','is_active')
        # field_classes = {'username': UsernameField}
        
    def __init__(self, *args, **kwargs):
        '''
        Makes user_role a mandatory field for staff creation
        '''
        super(TeamCreationForm, self).__init__(*args, **kwargs)
        limitchoices = (
        ('','Select Role'),
        (UserRole.TEAM, 'Team'),
        )
        if self.fields.get('user_role'):
            self.fields['user_role'].required = True
            self.fields['user_role'].choices = limitchoices

class TeamChangeForm(UserChangeForm):  

    class Meta:
        model = TeamUser
        fields = '__all__'
        field_classes = {'username': UsernameField}
    def __init__(self, *args, **kwargs):
        '''
        Makes user_role a mandatory field for staff creation
        '''
        super(TeamChangeForm, self).__init__(*args, **kwargs)
        limitchoices = (
        ('','Select Role'),
        (UserRole.TEAM, 'Team')
        )
        self.fields['phone'].widget = forms.HiddenInput()
        if self.fields.get('user_role'):
            self.fields['user_role'].required = True
            self.fields['user_role'].choices = limitchoices


class AdminPasswordResetForm(PasswordResetForm):

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Sends a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        _ = self
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        # first send the email to original recipient
        Email(to_email, subject).message_from_template(email_template_name,
         context).send()
        # send the copy to Super admins too
        super_admins = User.objects.filter(is_staff=True, is_superuser=True,
                user_role__role=UserRole.SUPERADMIN,
                 is_active=True,).exclude(email=to_email).values('email', 'first_name' )
        super_admins_email = [super_admin['email'] for super_admin in super_admins]
        email_template_name = 'accounts/admin/os_admin_reset_notify.html'
        if super_admins:
            context['name'] = super_admins[0]['first_name']
            Email(super_admins_email, subject).message_from_template(
                email_template_name,context).send()
