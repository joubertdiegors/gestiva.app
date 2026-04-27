from django import forms
from .models import Subcontractor, SubcontractorAddress


class SubcontractorForm(forms.ModelForm):
    class Meta:
        model = Subcontractor
        fields = ['name', 'trade_name', 'category', 'legal_form', 'vat_number',
                  'vat_rate', 'responsible', 'status', 'notes']
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control'}),
            'trade_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'category':    forms.HiddenInput(),
            'legal_form':  forms.Select(attrs={'class': 'form-control'}),
            'vat_number':  forms.TextInput(attrs={'class': 'form-control'}),
            'vat_rate':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'responsible': forms.TextInput(attrs={'class': 'form-control'}),
            'status':      forms.Select(attrs={'class': 'form-control'}),
            'notes':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SubcontractorAddressForm(forms.ModelForm):
    class Meta:
        model = SubcontractorAddress
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
