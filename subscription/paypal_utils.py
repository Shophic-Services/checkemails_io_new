import os, json
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest
from paypalcheckoutsdk.orders import OrdersCaptureRequest
from paypalcheckoutsdk.orders import OrdersGetRequest

from django.utils import timezone
from dateutil.relativedelta import relativedelta

import sys
from django.conf import settings
from subscription.models import ClientPlanDetails, ClientCreditSubscription, SubscriptionTransaction
from subscription.serializers import PackageSerializer

class PayPalClient:
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET

        """Setting up and Returns PayPal SDK environment with PayPal Access credentials.
           For demo purpose, we are using SandboxEnvironment. In production this will be
           LiveEnvironment."""
        self.environment = SandboxEnvironment(client_id=self.client_id, client_secret=self.client_secret)

        """ Returns PayPal HTTP client instance with environment which has access
            credentials context. This can be used invoke PayPal API's provided the
            credentials have the access to do so. """
        self.client = PayPalHttpClient(self.environment)

    def object_to_json(self, json_data):
        """
        Function to print all json data in an organized readable manner
        """
        result = {}
        if sys.version_info[0] < 3:
            itr = json_data.__dict__.iteritems()
        else:
            itr = json_data.__dict__.items()
        for key,value in itr:
            # Skip internal attributes.
            if key.startswith("__") or key.startswith("_"):
                continue
            result[key] = self.array_to_json_array(value) if isinstance(value, list) else\
                        self.object_to_json(value) if not self.is_primittive(value) else\
                         value
        return result;
    def array_to_json_array(self, json_array):
        result =[]
        if isinstance(json_array, list):
            for item in json_array:
                result.append(self.object_to_json(item) if  not self.is_primittive(item) \
                              else self.array_to_json_array(item) if isinstance(item, list) else item)
        return result;

    def is_primittive(self, data):
        return isinstance(data, str) or isinstance(data, str) or isinstance(data, int)
    

class CreateOrder(PayPalClient):

  #2. Set up your server to receive a call from the client
  """ This is the sample function to create an order. It uses the
    JSON body returned by buildRequestBody() to create an order."""

  def create_order(self,package=None,amt_value=0,present_donor=None):
      
    request = OrdersCreateRequest()
    request.headers['prefer'] = 'return=representation'
    
    #3. Call PayPal to set up a transaction
    request.request_body(
      {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": amt_value
                }
            }
        ]
    }
    )
    response = self.client.execute(request)
    orderid=response.result.id
        
    plan_price = package.price
    if package.subscription_period == 3:
        plan_price = package.price * 12
    custplan = ClientPlanDetails.objects.create(
        package=package,
        product=orderid,
        type=ClientPlanDetails.PAYPAL,
        price=amt_value,
        amount=plan_price,
        name=package.name
    )
    json_data = self.object_to_json(response.result)
    return json_data
  

class GetOrder(PayPalClient):

  #2. Set up your server to receive a call from the client
  """You can use this function to retrieve an order by passing order ID as an argument"""   
  def get_order(self, order_id):
    """Method to get order"""
    request = OrdersGetRequest(order_id)
    #3. Call PayPal to get the transaction
    response = self.client.execute(request)
    #4. Save the transaction in your database. Implement logic to save transaction to your database for future reference.
    print ('Status Code: ', response.status_code)
    print ('Status: ', response.result.status)
    print ('Order ID: ', response.result.id)
    print ('Intent: ', response.result.intent)
    print('Links :')
    for link in response.result.links:
      print('\t{}: {}\tCall Type: {}'.format(link.rel, link.href, link.method))
    print('Gross Amount: {} {}'.format(response.result.purchase_units[0].amount.currency_code,
                       response.result.purchase_units[0].amount.value))
 
    json_data = self.object_to_json(response.result)
    print("get_order_json_data: ", json.dumps(json_data,indent=4))
    return json_data




  
class CaptureOrder(PayPalClient):
        
    """this is the sample function performing payment capture on the order. Approved Order id should be passed as an argument to this function"""

    def capture_order(self, order_id, package,amt_value,present_donor=None):
        """Method to capture order using order_id"""
        # print('order_id==='+order_id)
        request = OrdersCaptureRequest(order_id)
        end_type = ClientCreditSubscription.ONE_TIME_PAYMENT
        response = self.client.execute(request)
        json_data = self.object_to_json(response.result)
        payment_method = ClientCreditSubscription.METHOD_PAYPAL
        model = ClientCreditSubscription
        subscription_id = None
        paypal_charge_id = response.result.id

        invoice_id = None
        latest_receipt_url = None
        latest_charge_id = None
        latest_charge_id = paypal_charge_id
        obj = model(
            client=present_donor,
            payment_method=payment_method,
            acknowledgement=True,
            cust_subscription=subscription_id,
            cust_charge_id=paypal_charge_id,
            payment_type=end_type,
            latest_charge_id=latest_charge_id,
            latest_receipt_url=latest_receipt_url,
            amount=amt_value,
            latest_invoice_id = invoice_id,
            plan = package,
            plan_data = json_data,
            is_current=True,
            is_activated=True,
        )
        obj.plan_data = PackageSerializer(package).data
        today = timezone.now()
        if end_type == ClientCreditSubscription.ONE_TIME_PAYMENT:
            if package.subscription_period == 1:
                obj.expire_date =  today + relativedelta(
                    days=7)
            if package.subscription_period == 2:
                obj.expire_date =  today + relativedelta(
                    months=1)
            if package.subscription_period == 3:
                obj.expire_date =  today + relativedelta(
                    months=12)
        obj.save()
        ClientCreditSubscription.objects.filter(client=obj.client, is_current=True).exclude(id=obj.id).update(is_current=False, is_activated= False)
        
        charge_id = paypal_charge_id

        data = {
            'cust_transaction_data': json_data,
            'subscription': obj,
            'charge_id': charge_id,
            'payment_method': payment_method
        }
        self.create_owner_transaction(data, package)
        self.create_revenue_transaction(data, package)
            
        return json_data
    
    

    def create_owner_transaction(self, data, package):
        # Create a purchase transaction for customer who purchased plan
        data['transaction_type'] = SubscriptionTransaction.SUBSCRIPTION_PURCHASE
        plan_price = package.price
        if package.subscription_period == 3:
            plan_price = package.price * 12
        data['amount'] = plan_price
        sub_obj = SubscriptionTransaction.objects.create(**data)
        return sub_obj

    def create_revenue_transaction(self, data, package):
        if data.get('amount'):
            data.pop('amount')
        data['transaction_type'] = SubscriptionTransaction.CUSTOMER_REVENUE
        plan_price = package.price
        if package.subscription_period == 3:
            plan_price = package.price * 12
        data['revenue'] = plan_price
        sub_obj = SubscriptionTransaction.objects.create(**data)
        return sub_obj