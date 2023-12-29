from app import message
from django import forms

from subscription.models import ClientCreditSubscription


class ClientCreditSubscriptionForm(forms.ModelForm):  

    class Meta:
        model = ClientCreditSubscription
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        '''
        Makes user_role a mandatory field for staff creation
        '''
        super(ClientCreditSubscriptionForm, self).__init__(*args, **kwargs)
        
        if self.fields.get('is_activated'):
            self.fields['is_activated'].widget = forms.HiddenInput()
            if not self.instance.id:
                self.fields['is_activated'].initial = True