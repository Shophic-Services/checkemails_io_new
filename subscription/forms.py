from typing import Any
from django import forms
from django.forms import formset_factory

from accounts.models import User, UserToken
from subscription.models import ClientCreditSubscription
from django.utils import timezone

class SubscriptionBuyForm(forms.Form):
    contact_full_name = forms.CharField(
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter Name'
        })
    )
    contact_phone = forms.CharField(
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter Phone'
        })
    )
    contact_address = forms.CharField(
        label='Address',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter Address'
        })
    )
    contact_country = forms.CharField(
        label='Country',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter Country'
        })
    )
    contact_province = forms.CharField(
        label='State',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter State'
        })
    )
    contact_city = forms.CharField(
        label='City',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter City'
        })
    )
    contact_postal_code = forms.CharField(
        label='Postal Code',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter Postal Code'
        })
    )
    
    stripeToken = forms.CharField(required=False)
    plan = forms.CharField(required=False)


    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        super(SubscriptionBuyForm, self).__init__(*args, **kwargs)

    def get_user_data(self):
        data =self.cleaned_data
        user_billing_dict = {
        'contact_full_name' : data.get('contact_full_name'),
        'contact_address' : data.get('contact_address'),
        'contact_phone' : data.get('contact_phone'),
        'contact_city' : data.get('contact_city'),
        'contact_country' : data.get('contact_country'),
        'contact_province' : data.get('contact_province'),
        'contact_postal_code' : data.get('contact_postal_code'),
        }

        return user_billing_dict
    
    def clean(self):
        from subscription.stripe_utils import StripeSubscriptionHelper
        billing_data = self.get_user_data()
        uuid = self.request.session.get('token')
        try:
            token = UserToken.objects.get(
                uuid=uuid)
            User.objects.filter(id=token.user.id).update(**billing_data)
            customer = token.user
        except Exception:
            token = None
            customer = self.request.user
        ClientCreditSubscription.objects.filter(client=customer).update(is_activated=False,is_current=False, expire_date=timezone.now())
        customer.has_plan=False
        customer.save()
        helper = StripeSubscriptionHelper(customer, self.cleaned_data, ClientCreditSubscription.ONE_TIME_PAYMENT)
        customer = helper.create_subscription(token=self.cleaned_data.get('stripeToken'))
        return self.cleaned_data