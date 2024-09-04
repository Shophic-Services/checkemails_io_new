from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from checkemails.core.base_models import (CheckEmailsBaseModel, CheckEmailsBaseWithDeleteModel)

import uuid, os
from datetime import datetime
from accounts import constant as account_constant
from django.db.models import JSONField
from accounts.models import User, UserRole
import random
import string

class ClientRecord(CheckEmailsBaseModel):
    client = models.ForeignKey(
        "accounts.User", verbose_name='Client', on_delete=models.CASCADE,
         db_index=True)


class SubscriptionPackage(CheckEmailsBaseModel):
    '''
    Model for plans/packages that are subscribed by customers
    '''
    SUBSCRIPTION_ONE_WEEK = 1
    SUBSCRIPTION_ONE_MONTH = 2
    SUBSCRIPTION_TWELVE_MONTH = 3
    SUBSCRIPTION_CUSTOM = 4

    SUBSCRIPTION_CHOICES = (
        (SUBSCRIPTION_ONE_WEEK, 'One Week'),
        (SUBSCRIPTION_ONE_MONTH, 'One Month'),
        (SUBSCRIPTION_TWELVE_MONTH, 'One Year'),
        (SUBSCRIPTION_CUSTOM, 'Custom'),
    )
    CUSTOM_HELP_TEXT = "Our Plan offers the flexibility of unlimited checks tailored to your specific needs, perfect for both individuals and small businesses seeking reliable, continuous access to our services. Additionally, you can save more with a commitment-based pricing model, designed for those who want to maximize value with long-term usage."
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)    
    name = models.CharField(verbose_name='Plan Name', max_length=50)
    price = models.PositiveSmallIntegerField(verbose_name='Plan Price in USD')
    is_active = models.BooleanField(verbose_name='Is Active', default=True)
    is_custom = models.BooleanField(verbose_name='Is Custom', default=True)
    can_change = models.BooleanField(verbose_name='Can Change', default=True)
    information = models.TextField(null=True, blank=True, default=CUSTOM_HELP_TEXT)
    plan_id = models.CharField(max_length=100, null=True, blank=True)
    start_date = models.DateField(verbose_name='Start Date', null=True, blank=True)
    end_date = models.DateField(verbose_name='End Date', null=True, blank=True)
    
    
    subscription_period = models.PositiveSmallIntegerField(
        verbose_name='Subscription Period', choices=SUBSCRIPTION_CHOICES, 
        default=SUBSCRIPTION_CUSTOM
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'


class ClientPlanDetails(CheckEmailsBaseWithDeleteModel):
    '''
    client plan details
    '''
    STRIPE = 1
    PAYPAL = 2
    TYPES = (
        (STRIPE, "Stripe"),
        (PAYPAL, "Paypal"),
    )

    package = models.ForeignKey(
        SubscriptionPackage, on_delete=models.CASCADE, related_name='custsubsdetails')
    type = models.PositiveSmallIntegerField(_("Plan Type"), choices=TYPES, default=STRIPE)
    plan_duration = models.CharField(max_length=50, null=True, blank=True)
    product = models.CharField(max_length=50, null=True, blank=True)
    price = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(_("Amount"), max_digits=7, decimal_places=2)
    tax = models.CharField(max_length=50, null=True, blank=True)
    

class PackageDescription(CheckEmailsBaseWithDeleteModel):
    '''
    Package description
    '''
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription_package = models.ForeignKey(
        SubscriptionPackage, on_delete=models.CASCADE, related_name='plan_descriptions')
    description = models.CharField(verbose_name='Description', max_length=100)

    def __str__(self):
        return self.subscription_package.name

    class Meta:
        verbose_name = 'Package Description'
        verbose_name_plural = 'Package Description'



class ClientCreditSubscription(CheckEmailsBaseModel):
    '''
    Model for storing plans subscribed by customers
    '''
    METHOD_CASH = 1
    METHOD_CHEQUE = 2
    METHOD_DEBIT_CARD = 3
    METHOD_CREDIT_CARD = 4
    METHOD_ONLINE = 5
    METHOD_STRIPE = 6
    METHOD_STRIPE_CHARGE = 7
    METHOD_PAYPAL = 8

    PAYMENT_OPTIONS = (
        (METHOD_CASH, 'Cash'),
        (METHOD_CHEQUE, 'Cheque'),
        (METHOD_DEBIT_CARD, 'Debit Card'),
        (METHOD_CREDIT_CARD, 'Credit Card'),
        (METHOD_ONLINE, 'Internet Banking'),
        (METHOD_STRIPE, 'Stripe Subscription'),
        (METHOD_STRIPE_CHARGE, 'Stripe Charge'),
        (METHOD_PAYPAL, 'Paypal Subscription'),
    )

    ADMIN_PAYMENT_OPTIONS = (
        (METHOD_CASH, 'Cash'),
        (METHOD_CHEQUE, 'Cheque'),
        (METHOD_DEBIT_CARD, 'Debit Card'),
        (METHOD_CREDIT_CARD, 'Credit Card'),
        (METHOD_ONLINE, 'Internet Banking'),
    )

    ONE_TIME_PAYMENT = 1
    RECURRING_PAYMENT = 2

    PAYMENT_TYPE_CHOICES = (
        (ONE_TIME_PAYMENT, 'One Time'),
        (RECURRING_PAYMENT, 'Recurring Payment')
    )


    invoice = models.CharField(default=int(uuid.uuid4().node) + int(datetime.now().timestamp()), max_length=256)
    plan = models.ForeignKey(
        SubscriptionPackage, verbose_name='Subscription Plan', 
        related_name='subscribed_plans', on_delete=models.CASCADE)
    client = models.ForeignKey(
        "accounts.ClientUser", verbose_name='Client', on_delete=models.CASCADE,
        related_name='client_credits', db_index=True, limit_choices_to={'user_role__role': account_constant.CLIENT})
    activated_on = models.DateTimeField(verbose_name='Activated On', auto_now_add=True)
    plan_data = JSONField(null=True, blank=True)
    payment_method = models.PositiveSmallIntegerField(
        verbose_name='Payment Method', choices=PAYMENT_OPTIONS, default=METHOD_CASH
    )
    payment_type = models.PositiveSmallIntegerField(
        verbose_name='Payment Type', choices=PAYMENT_TYPE_CHOICES, default=ONE_TIME_PAYMENT,
        db_index=True
    )
    payment_receipt =models.FileField(
        upload_to=settings.PAYMENT_RECEIPT_PATH, max_length=500, 
        verbose_name='Payment Receipt', null=True, blank=True)
    acknowledgement = models.BooleanField(
        # verbose_name=message.ACKNOWLEDMENT, 
        default=False)
    expire_date = models.DateTimeField(verbose_name='Expire Date', null=True, blank=True)
    is_current = models.BooleanField(verbose_name='Is Current', default=True)
    cust_subscription = models.CharField(null=True, blank=True, max_length=50)
    cust_charge_id = models.CharField(null=True, blank=True, max_length=50)
    renews_on = models.DateTimeField(verbose_name='Renews on', null=True, blank=True)
    recurring_data = JSONField(null=True, blank=True)
    is_cancelled = models.BooleanField(default=False)
    plan_updated = models.BooleanField(default=False)
    cancellation_comment = models.TextField(null=True, blank=True)
    latest_receipt_url = models.TextField(null=True, blank=True)
    latest_invoice_id = models.TextField(null=True, blank=True)
    latest_charge_id = models.CharField(null=True, blank=True, max_length=200)    
    is_activated = models.BooleanField(default=False)
    amount = models.CharField(max_length=50, null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super(ClientCreditSubscription, self).__init__(*args, **kwargs)
        self._payment_receipt = self.payment_receipt

    def __str__(self):
        return '{0}: {1}'.format(self.plan.name, self.client.first_name)

    @property
    def get_duration(self):
        if self.plan.plan_type == SubscriptionPackage.IMAGE_BASED:
            if self.subscription_period == self.SUBSCRIPTION_TWELVE_MONTH:
                if self.payment_type == self.ONE_TIME_PAYMENT:
                    return '12 Months'
                else:
                    return 'Yearly Recurring'
            else:
                if self.payment_type == self.ONE_TIME_PAYMENT:
                    return '1 Month'
                else:
                    return 'Monthly Recurring'
        else:
            return 'NA'

    class Meta:
        verbose_name = 'Credit'
        verbose_name_plural = 'Credits'

    # def send_plan_email(self, request):
    #     subject = message.EMAIL_SUBJECT_NEW_PLAN
    #     context = {
    #         'customer_name': self.customer.customer_user.full_name,
    #         'plan_name': self.plan.name
    #     }
    #     to_email = self.customer.customer_user.email
    #     template_name = 'subscription/email/new_subscription.html'
    #     Email(to_email, subject).message_from_template(
    #         template_name, context, request
    #     ).send()


class SubscriptionTransaction(CheckEmailsBaseModel):
    '''
    Transactions for subscriptions
    '''
    SUBSCRIPTION_PURCHASE = 1
    SUBCRIPTION_RENEWAL = 2
    CUSTOMER_REVENUE = 3
    
    TRANSCATION_TYPES=(
        (SUBSCRIPTION_PURCHASE, 'Subscription Purchase'),
        (SUBCRIPTION_RENEWAL, 'Subscription Renewal'),
        (CUSTOMER_REVENUE, 'Client Revenue'),
    )

    subscription = models.ForeignKey(
        ClientCreditSubscription, verbose_name='Customer Subscription',
        on_delete=models.CASCADE, related_name='sub_transactions')
    transaction_date = models.DateTimeField(auto_now_add=True)    
    cust_transaction_data = JSONField(null=True, blank=True)
    transaction_type = models.PositiveSmallIntegerField(
        verbose_name='Transaction Type', choices=TRANSCATION_TYPES,
        default=SUBSCRIPTION_PURCHASE)
    amount = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    revenue = models.DecimalField(verbose_name="Total overage charges in CAD",
                max_digits=7, decimal_places=2, default=0)
    receipt_url = models.CharField(null=True, blank=True, max_length=300)
    charge_id = models.CharField(null=True, blank=True, max_length=200)
    payment_method = models.PositiveSmallIntegerField(
        verbose_name='Payment Method', 
        choices=ClientCreditSubscription.PAYMENT_OPTIONS, 
        default=ClientCreditSubscription.METHOD_STRIPE
    )
    payment_receipt = models.FileField(
        upload_to=settings.PAYMENT_RECEIPT_PATH, max_length=500, 
        verbose_name='Payment Receipt', null=True, blank=True)


    def __str__(self):
        return '{0}: {1}'.format(self.subscription.plan.name, self.subscription.client.first_name)

    class Meta:
        verbose_name = 'Overrage Transaction Fee (Offline)'
        verbose_name_plural = 'Overrage Transaction Fees (Offline)'


def generate_unique_code(length=6):
    characters = string.ascii_letters + string.digits
    code = (''.join(random.choice(characters) for _ in range(length))).upper()
    return code

class ReferralCode(CheckEmailsBaseModel):

    name = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Referred By',
        on_delete=models.CASCADE, related_name='referred_user')
    referral_user = models.ForeignKey(User, verbose_name='Referral User',
        on_delete=models.CASCADE, related_name='referral_user')
    package = models.ForeignKey(
        SubscriptionPackage, on_delete=models.CASCADE, related_name='referral_plan')
    is_active = models.BooleanField(verbose_name='Active',
                                    default=False)    
    

    referral_code = models.CharField(null=True, blank=True, max_length=6, default=generate_unique_code())
    expire_date = models.DateField(verbose_name='Referral Expire Date', null=True, blank=True)

    def __str__(self):
        return '{0}: {1}'.format(self.user.first_name, self.referral_user.first_name)

    class Meta:
        verbose_name = 'Referral Plan Code'
        verbose_name_plural = 'Referral Plan Code'