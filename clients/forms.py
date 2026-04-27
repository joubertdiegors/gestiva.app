from django import forms
from .models import Client, ClientAddress, ClientContact


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'trade_name', 'category', 'legal_form',
                  'vat_number', 'vat_rate', 'responsible', 'notes', 'is_active']
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control'}),
            'trade_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'category':    forms.HiddenInput(),
            'legal_form':  forms.Select(attrs={'class': 'form-control'}),
            'vat_number':  forms.TextInput(attrs={'class': 'form-control'}),
            'vat_rate':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'responsible': forms.TextInput(attrs={'class': 'form-control'}),
            'notes':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ClientAddressForm(forms.ModelForm):
    class Meta:
        model = ClientAddress
        fields = ['label', 'street', 'number', 'complement',
                  'city', 'postal_code', 'state', 'country', 'is_default']
        widgets = {
            'label':       forms.TextInput(attrs={'class': 'form-control'}),
            'street':      forms.TextInput(attrs={'class': 'form-control'}),
            'number':      forms.TextInput(attrs={'class': 'form-control'}),
            'complement':  forms.TextInput(attrs={'class': 'form-control'}),
            'city':        forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'state':       forms.TextInput(attrs={'class': 'form-control'}),
            'country':     forms.TextInput(attrs={'class': 'form-control'}),
        }


class ClientContactForm(forms.ModelForm):
    class Meta:
        model = ClientContact
        fields = ['contact_type', 'name', 'phone', 'email', 'website', 'is_default']
        widgets = {
            'contact_type': forms.Select(attrs={'class': 'form-control'}),
            'name':         forms.TextInput(attrs={'class': 'form-control'}),
            'phone':        forms.TextInput(attrs={'class': 'form-control'}),
            'email':        forms.EmailInput(attrs={'class': 'form-control'}),
            'website':      forms.URLInput(attrs={'class': 'form-control'}),
        }
