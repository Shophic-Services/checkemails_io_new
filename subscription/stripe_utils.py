from django.db.models.expressions import F
import stripe, math, datetime, logging
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from app.middleware import get_current_request
# from geolocation.models import Currency
from accounts.models import User
from django import forms
from subscription.models import (ClientCreditSubscription,
                                 ClientPlanDetails, SubscriptionPackage,
                                 SubscriptionTransaction)
from subscription.serializers import PackageSerializer
# from assessments.constants import NUM_ASSESS_PER_PAGE
from decimal import Decimal
# from subscription.helper import PremiumSupportOption
# from accounts.helper import UserHelper
logger = logging.getLogger("stripe")


class StripeSubscriptionHelper(object):
    '''   Helper class for subscription module   '''
    stripe_connect_id = None
    is_reseller = False
    statement_descriptor = 'Check Emails Subscribe'

    def __init__(self, customer:User, data=None, end_type=ClientCreditSubscription.ONE_TIME_PAYMENT):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.customer = customer
        self.data = data
        self.end_type = end_type
 
    def create_customer(self):
        address={
                'country':self.customer.contact_country,
                'state':self.customer.contact_province,
                'city':self.customer.contact_city,
                'line1':self.customer.contact_address,
                'postal_code':self.customer.contact_postal_code
        }
        customer_dict = {
            'email': self.customer.email,
            'name': self.customer.contact_full_name if self.customer.contact_full_name else self.customer.email,
            'address':address,
            'phone':self.customer.contact_phone,
            'metadata':address,
        }

        customer = stripe.Customer.create(
            **customer_dict
        )
        self.customer.customer_id = customer.id
        return customer.id

    def create_card_source(self, customer_id, token):
        card_dict = {
            'source': token
        }
        # Add payment source
        card = stripe.Customer.create_source(
            customer_id, **card_dict
        )
        return card.id

    def create_subscription(self, token=None, card_source=None):
        '''
        create stripe subscription
        '''
        try:
            # Create customer
            if not self.customer.customer_id:
                customer_id = self.create_customer()
            else:
                customer_id = self.customer.customer_id

            # Create source from token
            if token:
                payment_source = self.create_card_source(customer_id, token)
            else:
                payment_source = card_source

            # Get plans
            items = self.get_items()

            subscription_dict = {
                'customer': customer_id,
                # 'pay_immediately': False,
            }
            if items:
                subscription_dict['items']=items

            if payment_source:
                subscription_dict['default_source'] = payment_source

            plan_price = self.plan.price
            if self.plan.subscription_period == 3:
                plan_price = self.plan.price * 12
            charge = stripe.Charge.create(
                currency="USD",
                amount=int((plan_price)*100),
                customer=customer_id,
                source=payment_source,
                description="{}".format(self.plan.name)
            )
        except Exception as e:
            print(e)
            raise forms.ValidationError(message=e.user_message, code=e.code)
        
        obj = self.create_sub_obj(None, charge)
        self.expire_old_subscriptions(obj)
        self.create_sub_transaction(obj, None, charge, ClientCreditSubscription.METHOD_STRIPE)
        return self.customer
    
    def create_product(self, nickname=""):
        '''  Create new stripe subscription product   '''
        self.metadata = {
            'plan_id': self.plan.id,
            'plan_type': self.plan.subscription_period,
        }
        plan_dict = {
            'name':"{}".format(self.plan.name),
            'type': 'service',
            'metadata': self.metadata,
            'statement_descriptor': self.statement_descriptor,
            'active': self.plan.is_active
        }
        try:
            plan_product = stripe.Product.retrieve(self.plan.plan_id)
        except Exception:
            try:
                plan_list = stripe.Product.search(query="metadata['plan_id']:'"+ self.plan.id +"'")
                plan_product = plan_list[0]
            except Exception:
                plan_product = stripe.Product.create(
                    **plan_dict
                )
                self.plan.plan_id = plan_product.id
                self.plan.save()
        return plan_product.id

    def create_onetime_price(self, nickname="", price=None):
        '''  Create one time price for stripe product   '''
        product = self.create_product(nickname)
        
        plan_price = self.plan.price
        
        if self.plan.subscription_period == 3:
            plan_price = self.plan.price * 12
        price_dict = {
            'product': product,
            'unit_amount_decimal' : (plan_price if not price else price) * 100,
            'nickname': nickname,
            'currency': 'USD',
            "billing_scheme": "per_unit",
            'active': self.plan.is_active,
        }
        stripe_plan = stripe.Price.create(
            **price_dict
        )
        return product, stripe_plan.id

    def get_items(self):
        from subscription.models import SubscriptionPackage
        self.plans = []
        lineitems = []
        if self.data.get('plan'):
            self.plan = SubscriptionPackage.objects.get(id=self.data.get('plan'))
            product, price = self.create_onetime_price(self.plan.name)
            
            plan_price = self.plan.price
            if self.plan.subscription_period == 3:
                plan_price = self.plan.price * 12
            custplan = ClientPlanDetails.objects.create(
                package=self.plan,
                product=product,
                type=ClientPlanDetails.STRIPE,
                price=price,
                amount=plan_price,
                name=self.plan.name
            )
            lineitems.append(self.construct_item(custplan))
            self.plans.append({
                'plan': custplan,
                'quantity': 1
            })
        
        return lineitems

    def construct_item(self, plan, quantity=1):
        lineitem = {
            "quantity": quantity,
            "price": plan.price,
            "metadata": {
                'name':plan.name,
                'id':plan.id,
                'package_name':plan.package.name,
                'price':plan.price
            }
        }

        return lineitem

    def create_sub_obj(self, stripe_data=None, stripe_charge_data=None):
        
        payment_method = ClientCreditSubscription.METHOD_STRIPE
        model = ClientCreditSubscription
        subscription_id = stripe_data.id if stripe_data else None
        stripe_charge_id = stripe_charge_data.id if stripe_charge_data else None

        invoice_id = stripe_data.latest_invoice if stripe_data else stripe_charge_data.invoice
        latest_receipt_url = None
        latest_charge_id = None
        if stripe_charge_id:
            latest_charge_id = stripe_charge_id
            latest_receipt_url = stripe_charge_data.receipt_url
        else:
            latest_charge_id, latest_receipt_url = self.get_receipt(
                stripe_data.latest_invoice, self.stripe_connect_id)
        obj = model(
            client=self.customer,
            payment_method=payment_method,
            acknowledgement=True,
            cust_subscription=subscription_id,
            cust_charge_id=stripe_charge_id,
            payment_type=self.end_type,
            latest_charge_id=latest_charge_id,
            latest_receipt_url=latest_receipt_url,
            amount=stripe_charge_data.get('amount')/100,
            latest_invoice_id = invoice_id,
            plan = self.plan,
            plan_data = stripe_charge_data,
            is_current=True,
            is_activated=True,
        )
        obj.plan_data = PackageSerializer(obj.plan).data
        today = timezone.now()
        if self.end_type == ClientCreditSubscription.ONE_TIME_PAYMENT:
            if self.plan.subscription_period == 1:
                obj.expire_date =  today + relativedelta(
                    days=7)
            if self.plan.subscription_period == 2:
                obj.expire_date =  today + relativedelta(
                    months=1)
            if self.plan.subscription_period == 3:
                obj.expire_date =  today + relativedelta(
                    months=12)
        self.customer.plan_id=str(obj.plan.id)
        self.customer.has_plan=True
        self.customer.save()
        obj.save()
        return obj 

    
    @staticmethod
    def get_sub_item(plan, stripe_sub):
        for item in stripe_sub.get('items').get('data'):
            if plan.price == item.get('price').get('id'):
                return item.get('id')
        return None


    def get_sub_items(self, stripe_data):
        if not stripe_data:
            return None, None
        sub_items = stripe_data.get('items').get('data')
        base_plan = self.item_dict.get('base_plan')
        overage_plan = self.item_dict.get('overage_plan')
        stripe_sub_item = None
        stripe_sub_item_overage = None
        for item in sub_items:
            plan_id = item.get('plan').get('id')
            if plan_id == base_plan:
                stripe_sub_item = item.get('id')
            elif plan_id == overage_plan:
                stripe_sub_item_overage = item.get('id')
        return stripe_sub_item, stripe_sub_item_overage


    def retreive_invoice(self, invoice_id, stripe_connect_id):
        if invoice_id:
            if stripe_connect_id:
                invoice_data = stripe.Invoice.retrieve(
                    invoice_id, stripe_account=stripe_connect_id
                )
            else:
                invoice_data = stripe.Invoice.retrieve(invoice_id)
            return invoice_data.charge
        return None

    def get_receipt(self, invoice_id, stripe_connect_id):
        if invoice_id:
            charge_id = self.retreive_invoice(invoice_id, stripe_connect_id)
        if charge_id:
            if stripe_connect_id:
                charge_data = stripe.Charge.retrieve(
                    charge_id, stripe_account=stripe_connect_id
                )
            else:
                charge_data = stripe.Charge.retrieve(charge_id)
            return charge_id, charge_data.receipt_url
        return None, None

        
    
    def expire_old_subscriptions(self, obj):
        '''
        Expire old subscriptions on creation of a new subscription
        '''
        subscriptions = ClientCreditSubscription.objects.filter(client=obj.client, is_current=True).exclude(id=obj.id).update(is_current=False, is_activated= False)


    
        
    def create_sub_transaction(self, obj, stripe_data, charge_data, payment_method):
        
        cust_transaction_data = stripe_data if stripe_data else charge_data
        if cust_transaction_data:
            charge_id = cust_transaction_data.id
            receipt_url = cust_transaction_data.receipt_url
        else:
            charge_id = None
            receipt_url = None

        data = {
            'cust_transaction_data': cust_transaction_data,
            'subscription': obj,
            'receipt_url': receipt_url,
            'charge_id': charge_id,
            'payment_method': payment_method
        }
        self.create_owner_transaction(data)
        self.create_revenue_transaction(data)

    def create_owner_transaction(self, data):
        # Create a purchase transaction for customer who purchased plan
        data['transaction_type'] = SubscriptionTransaction.SUBSCRIPTION_PURCHASE
        plan_price = self.plan.price
        if self.plan.subscription_period == 3:
            plan_price = self.plan.price * 12
        data['amount'] = plan_price
        sub_obj = SubscriptionTransaction.objects.create(**data)
        return sub_obj

    def create_revenue_transaction(self, data):
        if data.get('amount'):
            data.pop('amount')
        data['transaction_type'] = SubscriptionTransaction.CUSTOMER_REVENUE
        plan_price = self.plan.price
        if self.plan.subscription_period == 3:
            plan_price = self.plan.price * 12
        data['revenue'] = plan_price
        sub_obj = SubscriptionTransaction.objects.create(**data)
        return sub_obj
    
    def create_offline_data(self, plan):
        self.plan = plan
        payment_method = ClientCreditSubscription.METHOD_CASH
        model = ClientCreditSubscription
        plan_price = self.plan.price
        if self.plan.subscription_period == 3:
            plan_price = self.plan.price * 12
        obj = model(
            client=self.customer,
            payment_method=payment_method,
            acknowledgement=True,
            cust_subscription=None,
            cust_charge_id=None,
            payment_type=self.end_type,
            latest_charge_id=None,
            latest_receipt_url=None,
            amount=plan_price,
            latest_invoice_id = None,
            plan = self.plan,
            plan_data = None,
            is_current=True,
            is_activated=True,
        )
        obj.plan_data = PackageSerializer(obj.plan).data
        today = timezone.now()
        if self.end_type == ClientCreditSubscription.ONE_TIME_PAYMENT:
            if self.plan.subscription_period == 1:
                obj.expire_date =  today + relativedelta(
                    days=7)
            if self.plan.subscription_period == 2:
                obj.expire_date =  today + relativedelta(
                    months=1, days=-1)
            if self.plan.subscription_period == 3:
                obj.expire_date =  today + relativedelta(
                    months=12, days=-1)
        obj.save()
        self.customer.has_plan=True
        self.customer.save()
        self.expire_old_subscriptions(obj)
        self.create_sub_transaction(obj, None, None, ClientCreditSubscription.METHOD_CASH)
        return obj