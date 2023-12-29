'''
Forms for web view
'''
import re
from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import (AuthenticationForm, PasswordChangeForm,
                                       SetPasswordForm, UsernameField)
from django.core.validators import EmailValidator
from django.utils import timezone

from accounts import message
from accounts.models import User, UserProfile, UserRole, UserToken
from checkemails.core.email import Email
from django.contrib.auth import get_user_model


from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from django.utils.encoding import force_text
from django.contrib.auth.forms import (
    AdminPasswordChangeForm, UserChangeForm, UserCreationForm,
)

alnum_re = re.compile(r"^\w+$")

class UserAuthenticationForm(AuthenticationForm):
    '''
    Authentication form for user login
    '''
    username = UsernameField(
        max_length=254,
        widget=forms.EmailInput(attrs={'autofocus': True}),
        error_messages={
            'required': message.EMAIL_REQUIRED
        }
    )
    password = forms.CharField(
        label='Password', strip=False,
        widget=forms.PasswordInput,
        error_messages={'required': message.PASSWORD_REQUIRED}
    )
    remember_me = forms.BooleanField(
        label="Remember me", required=False, widget=forms.CheckboxInput())

    error_messages = {
        'invalid_login': message.INVALID_LOGIN,
        'inactive': message.INVALID_ACCOUNT,
    }

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username is not None and password:
            try:
                user = User.objects.get(email__iexact=username)
                self.user_cache = user if user.check_password(password) else None
            except User.DoesNotExist:
                self.user_cache = None
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)
        remember_me = self.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
        return self.cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        EmailValidator(message=message.INVALID_EMAIL).__call__(username)
        return username


class UserForgotPasswordForm(forms.Form):
    '''
    Password reset form for user
    '''
    email = forms.EmailField(
        label="Email", max_length=254, required=True,
        widget=forms.EmailInput(attrs={'autofocus': True}),
        error_messages={
            'required': message.EMAIL_REQUIRED,
            'invalid': message.INVALID_EMAIL
        }
    )

    def __init__(self, request=None, *args, **kwargs):
        self._user_cache = None
        self.request = request
        super(UserForgotPasswordForm, self).__init__(*args, **kwargs)
    
    def clean_email(self):
        user_model = get_user_model()
        email = self.cleaned_data['email']
        try:
            self._user_cache = user_model.objects.get(
                email__iexact=email, is_active=True, google_user=False, is_deleted=False)
        except user_model.DoesNotExist:
            self._user_cache = None
        return email

    def save(self):
        if self._user_cache:
            token_link = UserToken.create_token(
                UserToken.RANDOM_LINK_WEB, 
                user=self._user_cache, 
                extras=self._user_cache.email
            )
            token_link.send_forgot_password_email(self.request)
        return self


class UserResetPasswordForm(forms.Form):
    '''
    Reset password form after forgot password
    '''
    error_messages = {
        'password_mismatch': message.PASSWORD_MISMATCH_FIELDS,
    }
    new_password1 = forms.CharField(
        widget=forms.PasswordInput, strip=False
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput, strip=False,
    )

    def __init__(self, token=None, *args, **kwargs):
        self.token = token
        self.user = None
        if token:
            self.user = self.token.user
        super().__init__(*args, **kwargs)

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        password_validation.validate_password(password2, self.user)
        return password2

    def save(self):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        self.user.is_active = True
        self.user.save()
        self.token.expire_date = timezone.now()
        self.token.is_active = False
        self.token.save()
        return self.user


class UserSetPasswordForm(PasswordChangeForm):
    '''
    Reset password form
    '''
    error_messages = {
        'password_mismatch': message.PASSWORD_MISMATCH_FIELDS,
        'password_incorrect': message.OLD_PASSWORD_MISMATCH,
        'newpassword_error': message.SAME_PASSWORD_MISMATCH
    }

    def clean_new_password1(self):
        old_password = self.cleaned_data.get('old_password')
        new_password = self.cleaned_data.get('new_password1')
        if new_password and self.user.check_password(old_password) and new_password == old_password:
                raise forms.ValidationError(
                    self.error_messages['newpassword_error'],
                    code='newpassword_error',
                )
        return new_password

    def save(self):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        self.user.is_active = True
        self.user.save()
        return self.user

class UserProfileForm(forms.ModelForm):

    error_messages = {
        'password_mismatch': message.PASSWORD_MISMATCH_FIELDS,
        'password_incorrect': message.OLD_PASSWORD_MISMATCH,
        'newpassword_error': message.SAME_PASSWORD_MISMATCH
    }

    first_name = forms.CharField(
        label='First Name', required=True,
        widget=forms.TextInput(attrs={'class':'form-control'})
    )
    last_name = forms.CharField(
        label='Last Name', required=True,
        widget=forms.TextInput(attrs={'class':'form-control'})
    )
    phone = forms.CharField(
        label='Contact Number', required=True,
        widget=forms.TextInput(attrs={'class':'form-control'})
    )
    old_password = forms.CharField(
        label="Old password",
        strip=False,
        required=False,
        widget=forms.PasswordInput(attrs={'autofocus': True}),
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput, strip=False,
        required=False,
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput, strip=False,
        required=False,
    )
    change_password = forms.BooleanField(
        label='Change password?', required=False,
        widget=forms.CheckboxInput
    )

    class Meta(object):
        model = UserProfile
        fields = ('user',
                'balance_notify')

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UserProfileForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if self.cleaned_data.get('change_password') and not self.user.check_password(old_password):
            raise forms.ValidationError(
                    self.error_messages['password_incorrect'],
                    code='password_incorrect',
                )
        return old_password


    def clean_change_password(self):
        old_password = self.cleaned_data.get('old_password')
        new_password = self.cleaned_data.get('new_password1')
        confirm_password = self.cleaned_data.get('new_password2')
        change_password = self.cleaned_data.get('change_password')
        if change_password:
            if new_password != confirm_password:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
            if new_password and self.user.check_password(old_password) and new_password == old_password:
                raise forms.ValidationError(
                    self.error_messages['newpassword_error'],
                    code='newpassword_error',
                )
        return change_password



class PasswordField(forms.CharField):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", forms.PasswordInput(render_value=False))
        self.strip = kwargs.pop("strip", True)
        super(PasswordField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return ""
        value = force_text(value)
        if self.strip:
            value = value.strip()
        return value

class CreateUserForm(UserCreationForm):
    email = forms.CharField(
        label=_("Email"),
        max_length=256,
        widget=forms.TextInput(),
        required=True
    )
    first_name = forms.CharField(label=_("First name"), max_length=30,
        widget=forms.TextInput(), required=True
    )
    last_name = forms.CharField(label=_("Last name"), max_length=30,
        widget=forms.TextInput(), required=True
    )
    
    phone = forms.CharField(label=_("Contact Number"), max_length=10,
        widget=forms.NumberInput(), required=True
    )
    password1 = PasswordField(
        label=_("Password"),
    )
    
    password2 = PasswordField(
        label=_("Confirm Password"),
    )
    agree = forms.BooleanField(label=_("Agree"),
        widget=forms.CheckboxInput(), required=False
    )
    class Meta:
        model = get_user_model()
        
        fields = ('email','first_name', 'last_name','phone','password1','password2','agree')


    def clean_email(self):
        value = self.cleaned_data["email"]
        qs = User.objects.filter(email__iexact=value)
        if not qs.exists():
            return value
        raise forms.ValidationError(
            _("A user is registered with this email address."))

    def clean_agree(self):
        value = self.cleaned_data["agree"]
        if not value:
            raise forms.ValidationError(
            _("Kindly agree with Terms and Privacy Policy."))

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        password_validation.validate_password(password2)
        return password2


class OTPUserForm(forms.Form):
    token = forms.UUIDField(
        label=_("Token"),
        required=True
    )
    otp = forms.CharField(
        label=_("OTP"),
        max_length=1,
        widget=forms.TextInput(),
        required=True
    )

    def get_token(self, uuid):
        try:
            token = UserToken.objects.get(
                uuid=uuid, is_active=True, 
                expire_date__gte=timezone.now(),
                user__is_deleted=False
            )
        except UserToken.DoesNotExist:
            token = None
        return token

    def clean_token(self):
        token = self.cleaned_data.get('token')
        token_obj = self.get_token(token)
        if not token_obj:
            raise forms.ValidationError(message.OTP_TOKEN_ENCRYPTION_NOT_MATCH)
        return self.cleaned_data.get('token')

    def clean_otp(self):
        token = self.data.get('token')
        otp = "".join(self.data.getlist('otp'))
        token_obj = self.get_token(token)
        
        if self.data.getlist('otp'):
            if not token_obj or token_obj.expire_date < timezone.now():
                raise forms.ValidationError(
                message.OTP_EXPIRED
            )
            if token_obj.token != otp:
                raise forms.ValidationError(
                    message.OTP_NOT_VALIDATED
                )
        else:
            raise forms.ValidationError(
                message.OTP_INVALID
            )

        
        return self.cleaned_data.get('otp')

