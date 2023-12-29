
import math
from app import constant

import re
import copy
import hashlib

import magic_import

from django.urls import reverse
from django.conf import settings
from django.db.models import ( Q, Subquery, IntegerField)

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone
from accounts.models import User
from subscription.models import (ClientCreditSubscription,
                                 PaypalPlanDetails, SubscriptionPackage,
                                 SubscriptionTransaction)
from subscription.serializers import PackageSerializer


class PaypalPlanHelper(object):
    '''
    Helper class for creating/updating subscription plans on paypal
    '''
    paypal_connect_id = None
    is_reseller = False
    statement_descriptor = 'Check Emails Subscription'

    def __init__(self, plan):
        # TODO Create paypal log
        paypal.api_key = settings.paypal_SECRET_KEY
        self.plan = plan
        if hasattr(plan, 'paypal_details'):
            self.plan_details = plan.paypal_details
        else:
            self.plan_details = PaypalPlanDetails.objects.create(
                package=self.plan
            )
        self.metadata = {
            'plan_id': self.plan.id,
            'plan_type': self.plan.plan_type,
            'training_education': self.plan.training_education,
            'overage_charge': self.plan.overage_charge
        }
        if self.plan.plan_type == SubscriptionPackage.ASSESSMENT_BASED:
            self.metadata['assessments_allowed'] = self.plan.assessments_allowed
            self.unit_label = 'assessment'
        else:
            self.unit_label = 'image'
            self.metadata['images_allowed'] = self.plan.images_allowed
        if self.plan.belongs_to and self.plan.belongs_to.user_type == User.RESELLER:
            self.is_reseller = True
            self.paypal_connect_id = self.plan.belongs_to.paypal_connect_account.paypal_user_id
            self.statement_descriptor = 'Subscription Charge'

    def get_plan_name(self, interval, is_base_plan):
        plan_add =  ' - Yearly' if interval == 'year' else ' - Monthly'
        if is_base_plan:
            unit_label = interval
        else:
            unit_label = self.unit_label
            plan_add += ' Overage'
        plan_name = self.plan.name + plan_add
        return unit_label, plan_name

    def create_product(self, interval, is_base_plan=False):
        '''
        Create new paypal subscription product
        '''
        unit_label, plan_name = self.get_plan_name(interval, is_base_plan)
        plan_dict = {
            'name': plan_name,
            'type': 'service',
            'metadata': self.metadata,
            'statement_descriptor': self.statement_descriptor,
            'unit_label': unit_label,
            'active': self.plan.is_active
        }
        if self.is_reseller:
            plan_dict['paypal_account'] = self.paypal_connect_id
        plan_product = paypal.Product.create(
            **plan_dict
        )
        return plan_product.id

    def update_product(self, product_id, interval, is_base_plan=False):
        '''
        update paypal subscription product
        '''
        unit_label, plan_name = self.get_plan_name(interval, is_base_plan)
        plan_dict = {
            'name': plan_name,
            'metadata': self.metadata,
            'statement_descriptor': self.statement_descriptor,
            'unit_label': unit_label,
            'active': self.plan.is_active
        }
        if self.is_reseller:
            plan_dict['paypal_account'] = self.paypal_connect_id
        plan_product = paypal.Product.modify(
            product_id,
            **plan_dict
        )
        return plan_product.id

    def create_plan(self, interval, product_id, is_base_plan=False):
        '''
        Create base plan for a package
        '''
        unit_label, plan_name = self.get_plan_name(interval, True)
        factor = 12 if interval == 'year' else 1
        plan_dict = {
            'currency': 'CAD',
            'interval': interval,
            'product': product_id,
            'active': self.plan.is_active,
            'nickname': plan_name,
        }
        if self.is_reseller:
            plan_dict['paypal_account'] = self.paypal_connect_id
        if is_base_plan:
            amount = self.plan.price * 100 * factor
            plan_dict['amount_decimal'] = amount
            plan_dict['usage_type'] = 'licensed'
        else:
            plan_dict.update(self.get_overage_plan(factor))
        paypal_plan = paypal.Plan.create(
            **plan_dict
        )
        return paypal_plan.id

    def get_overage_plan(self, factor):
        '''
        create overage plan for a package
        '''
        if self.plan.plan_type == SubscriptionPackage.IMAGE_BASED:
            up_to = self.plan.images_allowed * factor
        else:
            up_to = self.plan.assessments_allowed * factor
        plan_dict = {
            'usage_type': 'metered',
            'aggregate_usage': 'sum',
            'billing_scheme': 'tiered',
            'tiers': [
                {
                    "unit_amount_decimal": "0",
                    "up_to": up_to
                },
                {
                    "unit_amount_decimal": self.plan.overage_charge * 100,
                    "up_to": "inf"
                }
            ],
            'tiers_mode': 'graduated',
        }
        return plan_dict

    def create_all_plans(self):
        '''
        Creates 4 plans for every package of admin
        Creates 2 plans for every package of reseller ( No overage )
        Monthly and it's overage, yearly and it's overage
        '''
        # Month base product        
        if self.plan_details.month_base_product:
            month_base_product = self.update_product(
                self.plan_details.month_base_product, 'month', True)
        else:
            month_base_product = self.create_product('month', True)
        month_base_plan = self.create_plan('month', month_base_product, True)

        self.plan_details.month_base_product = month_base_product
        self.plan_details.month_base_plan = month_base_plan

        if not self.is_reseller:
            # Month overage product
            if self.plan_details.month_overage_product:
                month_overage_product = self.update_product(
                    self.plan_details.month_overage_product, 'month', False)
            else:
                month_overage_product = self.create_product('month', False)
            month_overage_plan = self.create_plan(
                'month', month_overage_product, False)
            self.plan_details.month_overage_product = month_overage_product
            self.plan_details.month_overage_plan = month_overage_plan

        # Year base product
        if self.plan_details.year_base_product:
            year_base_product = self.update_product(
                self.plan_details.year_base_product, 'year', True)
        else:
            year_base_product = self.create_product('year', True)
        year_base_plan = self.create_plan('year', year_base_product, True)

        self.plan_details.year_base_product = year_base_product
        self.plan_details.year_base_plan = year_base_plan

        if not self.is_reseller:
            # Year overage product
            if self.plan_details.year_overage_product:
                year_overage_product = self.update_product(
                    self.plan_details.year_overage_product, 'year', False)
            else:
                year_overage_product = self.create_product('year', False)
            year_overage_plan = self.create_plan(
                'year', year_overage_product, False)
            self.plan_details.year_overage_product = year_overage_product
            self.plan_details.year_overage_plan = year_overage_plan

        self.plan_details.save()


class CreateSubscriptionData(object):
    '''
    Create subcription database object
    '''
    def __init__(self, obj, request):
        self.obj = obj
        self.request = request

    def create_data(self):
        self.obj.plan_data = PackageSerializer(self.obj.plan).data
        if self.obj.plan.subscription_period == SubscriptionPackage.SUBSCRIPTION_TWELVE_MONTH:
            self.obj.plan_data['price'] = 12 * self.obj.plan_data.get('price', 0)
        # self.obj.send_plan_email(self.request)
        # customer = self.obj.client
        # customer.plan_purchased_type = self.obj.plan.plan_type
        # customer.save()
        return self.obj

    def create_sub_transactions(self):
        receipt_url = None
        if self.obj.payment_receipt:
            receipt_url = settings.BUCKET_ACCESS_PATH + self.obj.payment_receipt.name
        data = {
            'subscription': self.obj,
            'receipt_url': receipt_url,
            'payment_method': self.obj.payment_method
        }
        self.create_owner_transaction(data)
        self.create_revenue_transaction(data)

    def create_owner_transaction(self, data):
        # Create a purchase transaction for client who purchased plan
        data['transaction_type'] = SubscriptionTransaction.SUBSCRIPTION_PURCHASE
        data['amount'] = self.obj.plan_data.get('price', 0)
        SubscriptionTransaction.objects.create(**data)

    def create_revenue_transaction(self, data):
        # Create a revenue transaction for admin
        if data.get('amount'):
            data.pop('amount')
        data['transaction_type'] = SubscriptionTransaction.CUSTOMER_REVENUE
        data['revenue'] = self.obj.plan_data.get('price', 0)
        SubscriptionTransaction.objects.create(**data)


class PaypalSubscriptionHelper(object):
    '''
    Helper class for subscription module
    '''
    paypal_connect_id = None
    is_reseller = False
    item_dict = {
        'base_plan': None,
        'overage_plan': None
    }

    def __init__(self, customer, plan, duration, end_type, request=None, is_direct=False):
        paypal.api_key = settings.paypal_SECRET_KEY
        self.customer = customer
        self.plan = plan
        self.duration = duration
        self.end_type = end_type
        if request:
            self.user_type = request.user.user_type
        else:
            self.user_type = customer.business_model
        if self.user_type == User.DIRECT and \
            self.plan.belongs_to and \
                self.plan.belongs_to.user_type == User.RESELLER:
            self.is_reseller = True
            self.paypal_connect_id = self.plan.belongs_to.paypal_connect_account.paypal_user_id
        self.request = request
        self.is_direct = is_direct
 
    def create_customer(self):
        # Create platform customer
        customer_dict = {
            'email': self.customer.customer_user.email,
            'name': self.customer.customer_user.full_name
        }
        if self.is_reseller:
            customer_dict['paypal_account'] = self.paypal_connect_id
        customer = paypal.Customer.create(
            **customer_dict
        )
        self.customer.paypal_customer_id = customer.id
        self.customer.save()
        return customer.id

    def create_card_source(self, customer_id, token):
        card_dict = {
            'source': token
        }
        if self.is_reseller:
            card_dict['paypal_account'] = self.paypal_connect_id
        # Add payment source
        card = paypal.Customer.create_source(
            customer_id, **card_dict
        )
        return card.id

    def create_subscription(self, token=None):
        '''
        create paypal subscription
        '''
        # Create customer
        if not self.customer.paypal_customer_id:
            customer_id = self.create_customer()
        else:
            customer_id = self.customer.paypal_customer_id

        # Create source from token
        if token:
            payment_source = self.create_card_source(customer_id, token)
        else:
            payment_source = None

        # Get plans
        items = []
        if self.duration == ClientCreditSubscription.SUBSCRIPTION_TWELVE_MONTH:
            items.append({'plan': self.plan.paypal_details.year_base_plan})
            self.item_dict['base_plan'] = self.plan.paypal_details.year_base_plan
            if not self.is_reseller:
                items.append({'plan': self.plan.paypal_details.year_overage_plan})
                self.item_dict['overage_plan'] = self.plan.paypal_details.year_overage_plan
        else:
            items.append({'plan': self.plan.paypal_details.month_base_plan})
            self.item_dict['base_plan'] = self.plan.paypal_details.month_base_plan
            if not self.is_reseller:
                items.append({'plan': self.plan.paypal_details.month_overage_plan})
                self.item_dict['overage_plan'] = self.plan.paypal_details.month_overage_plan

        subscription_dict = {
            'customer': customer_id,
            'items': items,
            'prorate': False,
        }

        if payment_source:
            subscription_dict['default_source'] = payment_source

        if self.end_type == ClientCreditSubscription.ONE_TIME_PAYMENT:
            subscription_dict['cancel_at_period_end'] = True
        if self.is_reseller:
            subscription_dict['paypal_account'] = self.paypal_connect_id
        subscription_obj = paypal.Subscription.create(
            **subscription_dict
        )
        obj = self.create_sub_obj(subscription_obj)
        return obj

    def create_sub_obj(self, paypal_data=None, paypal_charge_data=None):
        payment_method = ClientCreditSubscription.METHOD_paypal
        payment_method = ClientCreditSubscription.METHOD_PAYPAL_CHARGE
        model = ClientCreditSubscription
        subscription_id = paypal_data.id if paypal_data else None
        paypal_charge_id = paypal_charge_data.id if paypal_charge_data else None
        latest_receipt_url = None
        latest_charge_id = None
        if paypal_charge_id:
            latest_charge_id = paypal_charge_id
            latest_receipt_url = paypal_charge_data.receipt_url
        else:
            latest_charge_id, latest_receipt_url = self.get_receipt(
                paypal_data.latest_invoice, self.paypal_connect_id)
        paypal_sub_item, paypal_sub_item_overage = self.get_sub_items(paypal_data)
        belongs_to = self.plan.belongs_to
        obj = model(
            plan=self.plan,
            customer=self.customer,
            subscription_period=self.duration,
            payment_method=payment_method,
            acknowledgement=True,
            paypal_subscription=subscription_id,
            paypal_charge_id=paypal_charge_id,
            payment_type=self.end_type,
            belongs_to=belongs_to,
            latest_charge_id=latest_charge_id,
            latest_receipt_url=latest_receipt_url,
            paypal_sub_item_overage=paypal_sub_item_overage,
            paypal_sub_item=paypal_sub_item
        )
        obj = CreateSubscriptionData(obj, self.request).create_data()
        if not self.is_direct:
            today = timezone.now().date()
            if self.end_type == ClientCreditSubscription.ONE_TIME_PAYMENT:
                obj.expire_date =  today + relativedelta(
                    months=obj.subscription_period, days=-1)
            else:
                obj.renews_on = today + relativedelta(months=obj.subscription_period)
        obj.save()
        self.create_sub_transaction(
            obj, paypal_data, paypal_charge_data, 
            latest_receipt_url, latest_charge_id, payment_method)
        return obj

    def get_sub_items(self, paypal_data):
        if not paypal_data:
            return None, None
        sub_items = paypal_data.get('items').get('data')
        base_plan = self.item_dict.get('base_plan')
        overage_plan = self.item_dict.get('overage_plan')
        paypal_sub_item = None
        paypal_sub_item_overage = None
        for item in sub_items:
            plan_id = item.get('plan').get('id')
            if plan_id == base_plan:
                paypal_sub_item = item.get('id')
            elif plan_id == overage_plan:
                paypal_sub_item_overage = item.get('id')
        return paypal_sub_item, paypal_sub_item_overage

    def create_paypal_charge(self, customer_id, payment_source):
        description = self.plan.name
        if self.is_reseller:
            charge = paypal.Charge.create(
                currency='CAD',
                amount=self.plan.price * 100,
                customer=customer_id,
                source=payment_source,
                description=description,
                paypal_account=self.paypal_connect_id
            )
        else:
            charge = paypal.Charge.create(
                currency='CAD',
                amount=self.plan.price * 100,
                customer=customer_id,
                source=payment_source,
                description=description,
            )
        return charge

    def retreive_invoice(self, invoice_id, paypal_connect_id):
        _ = self
        if invoice_id:
            if paypal_connect_id:
                invoice_data = paypal.Invoice.retrieve(
                    invoice_id, paypal_account=paypal_connect_id
                )
            else:
                invoice_data = paypal.Invoice.retrieve(invoice_id)
            return invoice_data.charge
        return None

    def get_receipt(self, invoice_id, paypal_connect_id):
        if invoice_id:
            charge_id = self.retreive_invoice(invoice_id, paypal_connect_id)
        if charge_id:
            if paypal_connect_id:
                charge_data = paypal.Charge.retrieve(
                    charge_id, paypal_account=paypal_connect_id
                )
            else:
                charge_data = paypal.Charge.retrieve(charge_id)
            return charge_id, charge_data.receipt_url
        return None, None

    def create_direct_subscription(self, token):
        self.end_type = ClientCreditSubscription.ONE_TIME_PAYMENT
        self.duration = ClientCreditSubscription.SUBSCRIPTION_ONE_MONTH
        if not self.customer.paypal_customer_id:
            customer_id = self.create_customer()
        else:
            customer_id = self.customer.paypal_customer_id
        payment_source = self.create_card_source(customer_id, token)
        paypal_charge_id = self.create_paypal_charge(customer_id, payment_source)
        obj = self.create_sub_obj(None, paypal_charge_id)
        return obj
        
    def create_sub_transaction(self, sub_obj, paypal_data, charge_data, receipt_url, charge_id, payment_method):
        paypal_transaction_data = paypal_data if paypal_data else charge_data
        data = {
            'paypal_transaction_data': paypal_transaction_data,
            'subscription': sub_obj,
            'receipt_url': receipt_url,
            'charge_id': charge_id,
            'payment_method': payment_method
        }
        self.create_owner_transaction(data)
        self.create_revenue_transaction(data)

    def create_owner_transaction(self, data):
        # Create a purchase transaction for customer who purchased plan
        data['transaction_type'] = SubscriptionTransaction.SUBSCRIPTION_PURCHASE
        data['amount'] = self.plan.price * self.duration
        sub_obj = SubscriptionTransaction.objects.create(**data)
        return sub_obj

    def create_revenue_transaction(self, data):
        if data.get('amount'):
            data.pop('amount')
        data['transaction_type'] = SubscriptionTransaction.CUSTOMER_REVENUE
        data['revenue'] = self.plan.price * self.duration
        sub_obj = SubscriptionTransaction.objects.create(**data)
        return sub_obj