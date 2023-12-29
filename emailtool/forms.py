from django import forms
from django.forms import formset_factory

class EmailDataForm(forms.Form):
    firstname = forms.CharField(
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter First Name'
        })
    )
    lastname = forms.CharField(
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter Last Name'
        })
    )
    domain = forms.CharField(
        label='Domain',
        widget=forms.TextInput(attrs={
            'class': 'text-left form-control px-2',
            'placeholder': 'Enter Domain'
        })
    )
EmailDataFormset = formset_factory(EmailDataForm, extra=1)