import random
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from accounts import constant, message
from checkemails.core import constants
from checkemails.core.base_models import (CheckEmailsBaseModel,)
from checkemails.core.email import Email
from checkemails.core.validators import MOBILE_NUMBER_VALIDATOR
from django.contrib.auth.models import Group, PermissionsMixin


class UserRole(CheckEmailsBaseModel):
    '''
    User Role Model
    '''
    SUPERADMIN = constant.SUPERADMIN
    MANAGER = constant.MANAGER
    TEAM = constant.TEAM
    CLIENT = constant.CLIENT

    USER_ROLE_CHOICES = (
        (SUPERADMIN, 'Admin'),
        (MANAGER, 'Manager'),
        (TEAM, 'Team'),
        (CLIENT, 'Client'),
    )
    USER_ROLE_DICT = {
        SUPERADMIN: 'Admin',
        MANAGER: 'Manager',
        TEAM: 'Team',
        CLIENT: 'Client',
    }
    role = models.SmallIntegerField(choices=USER_ROLE_CHOICES)

    def __str__(self):
        return self.get_role_display()


class UserManager(BaseUserManager):
    '''
    User Custom Manager
    '''

    def create_user(self, email=None, password=None, commit=True):
        '''
        Create User
        '''
        if not email:
            raise ValueError('Email Address is Mandatory')
        user = self.model(email=self.normalize_email(email))
        user.set_password(password)
        if commit:
            user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        '''
        Create Superuser
        '''
        user = self.create_user(email, password, commit=False)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.first_name = 'Admin'
        user.user_role_id = UserRole.objects.filter(
            role=UserRole.SUPERADMIN).first().id
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)


class User(AbstractBaseUser, CheckEmailsBaseModel, PermissionsMixin):
    '''
    User Model 
    '''

    email = models.EmailField(unique=True)
    first_name = models.CharField("First Name", max_length=100)
    last_name = models.CharField("Last Name", max_length=100)
    phone = models.CharField("Contact Number", max_length=20,

                             help_text='Please enter a 10 digit mobile number.')
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(verbose_name='Active',
                                    default=False)
    user_role = models.ForeignKey(UserRole, on_delete=models.CASCADE,
                                  blank=True, null=True, verbose_name="User Role", )
    is_superuser = models.BooleanField(default=False)
    google_user = models.BooleanField(default=False)
    objects = UserManager()

    USERNAME_FIELD = 'email'

    @property
    def role(self):
        if self.user_role:
            return self.user_role.get_role_display()
        else:
            return '-'

    def __str__(self):
        return self.first_name + ' ' + self.last_name

    def get_short_name(self):
        '''
        It returns Short Name of user
        '''
        return self.first_name
    
    def get_full_name(self):
        '''
        It returns Short Name of user
        '''
        return self.first_name + ' ' + self.last_name

    @staticmethod
    def send_email_change_mail(user_id, old_email, request):
        user = User.objects.get(id=user_id)
        email_subject = 'Email Change'
        email = Email(user.email, email_subject)
        template_name = 'accounts/email/email_changed_template.html'
        context = {
            'user': user,
            'old_email': old_email
        }
        email.message_from_template(template_name, context, request).send()

    def send_set_password_email(self, request):
        token_link = UserToken.create_token(
            UserToken.RANDOM_LINK_WEB,
            user=self,
            extras=self.email
        )
        token_link.send_set_password_email(request)

    def save(self, *args, **kwargs):
        '''
        Save the model and does send the email
        '''
        self.email = self.email.lower()
        response = super(User, self).save(*args, **kwargs)
        return response
    

    def send_email_to_admins(self, request):
        '''  Notify admins '''
        super_admins = User.objects.filter(
            is_staff=True, is_superuser=True, is_active=True, 
            user_role__role=UserRole.SUPERADMIN
        ).exclude(email=self.email)
        subscription = self.client_credits.order_by('-create_date').first()
        email_template_name = 'accounts/admin/admin_user_notify.html'
        context = {
            'domain': request.get_host(),
            'protocol': request.scheme,
            'user': self,
            'subscription': subscription,
            'name': None,
        }
        for admin in super_admins:
            context['name'] = admin.first_name
            Email(admin.email, message.NEW_USER_CREATED).message_from_template(
                email_template_name, context, request).send()
        return self

    class Meta(object):
        ''' User Class Meta '''
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        app_label = 'accounts'


class UserProfile(CheckEmailsBaseModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='user_profile')
    balance_notify = models.BooleanField(default=True)
    email_notify = models.BooleanField(default=True)

    def __str__(self):
        return self.user.full_name


class UserToken(models.Model):
    '''
        User Token model is for sending tokens to user
        Tokens can be of two types: forgot password and OTP
    '''
    RANDOM_OTP_WEB = 1
    RANDOM_LINK_WEB = 2

    TOKEN_TYPE_CHOICE = (
        (RANDOM_OTP_WEB, 'Forgot password OTP'),
        (RANDOM_LINK_WEB, 'Forgot password Link')
    )

    
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name='token', on_delete=models.CASCADE)
    token = models.CharField(max_length=240)
    is_active = models.BooleanField(default=True)
    expire_date = models.DateTimeField()
    create_date = models.DateTimeField(auto_now_add=True)
    extras = models.CharField(max_length=255, null=True, blank=True)
    token_type = models.PositiveSmallIntegerField(choices=TOKEN_TYPE_CHOICE)

    def __str__(self):
        return "{0} : {1}".format(self.user, self.token)

    @staticmethod
    def create_token(token_type, user=None, extras=None):
        '''
            Create Token
        '''
        if token_type == UserToken.RANDOM_OTP_WEB:
            token = random.randint(1111, 9999)
            token = '{0:04d}'.format(token)
            # token = '1234'
        else:
            token = uuid4()
        expire_date = timezone.now() + timedelta(
            hours=settings.USER_TOKEN_EXPIRES_IN_HOURS)
        data = {
            'user': user,
            'token': token,
            'expire_date': expire_date,
            'extras': extras,
            'is_active': True,
            'token_type': token_type
        }
        UserToken.objects.filter(
            user=user, expire_date__gte=timezone.now(),
            is_active=True, token_type=token_type).update(
                expire_date=timezone.now())
        return UserToken.objects.create(**data)

    def send_forgot_password_email(self, request):
        '''  Forgot Password Email '''
        domain = request.get_host()
        protocol = request.scheme
        if self.token_type == UserToken.RANDOM_OTP_WEB:
            template_name = 'accounts/email/account_otp.html'
            subject = message.SUBJECT_OTP_PASSWORD
        else:
            template_name = 'accounts/email/forgot_password_customer.html'
            subject = message.SUBJECT_FORGOT_PASSWORD
        Email(
            self.user.email, subject,
        ).message_from_template(
            template_name, {
                'domain_name': domain,
                'protocol': protocol,
                'token': self.token,
                'name': self.user.first_name,
                'request': request,
            }, request).send()
        if self.token_type == UserToken.RANDOM_OTP_WEB:
            self.expire_date = timezone.now() + timezone.timedelta(minutes=15)
            self.save()
        return self

    def send_set_password_email(self, request):
        domain = request.get_host()
        protocol = request.scheme
        template_name = 'accounts/email/set_password.html'
        Email(
            self.user.email, message.SUBJECT_SET_PASSWORD,
        ).message_from_template(
            template_name, {
                'domain_name': domain,
                'protocol': protocol,
                'token': self.token,
                'name': self.user.first_name,
                'request': request
            }, request).send()
        return self
