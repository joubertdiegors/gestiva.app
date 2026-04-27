from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Collaborator, CollaboratorAddress, CollaboratorInsuranceNote, Nationality, Language, InsuranceFund, InsuranceFundContact, LegalForm, DriverLicense, ParkingPermit


class CollaboratorForm(forms.ModelForm):
    class Meta:
        model = Collaborator
        fields = [
            'company', 'role', 'entry_date', 'exit_date',
            'insurance_fund',
            'photo', 'name', 'status',
            'id_number', 'id_expiry', 'birth_date',
            'nationalities', 'languages',
            'phone', 'phone2', 'email', 'email2',
            'notes',
        ]
        widgets = {
            'company':        forms.Select(attrs={'class': 'field-input'}),
            'insurance_fund': forms.Select(attrs={'class': 'field-input'}),
            'photo':          forms.FileInput(attrs={'class': 'form-control'}),
            'name':           forms.TextInput(attrs={'class': 'field-input', 'placeholder': '—'}),
            'role':           forms.TextInput(attrs={'class': 'field-input', 'placeholder': '—'}),
            'status':         forms.Select(attrs={'class': 'field-input'}),
            'id_number':      forms.TextInput(attrs={'class': 'field-input', 'placeholder': '—'}),
            'id_expiry':      forms.DateInput(attrs={'class': 'field-input', 'type': 'date'}),
            'birth_date':     forms.DateInput(attrs={'class': 'field-input', 'type': 'date'}),
            'nationalities':  forms.SelectMultiple(attrs={'class': 'field-input field-select-multi', 'size': '3'}),
            'languages':      forms.SelectMultiple(attrs={'class': 'field-input field-select-multi', 'size': '3'}),
            'phone':          forms.TextInput(attrs={'class': 'field-input', 'placeholder': '—'}),
            'phone2':         forms.TextInput(attrs={'class': 'field-input', 'placeholder': '—'}),
            'email':          forms.EmailInput(attrs={'class': 'field-input', 'placeholder': '—'}),
            'email2':         forms.EmailInput(attrs={'class': 'field-input', 'placeholder': '—'}),
            'entry_date':     forms.DateInput(attrs={'class': 'field-input', 'type': 'date'}),
            'exit_date':      forms.DateInput(attrs={'class': 'field-input', 'type': 'date'}),
            'notes':          forms.Textarea(attrs={'class': 'field-input', 'rows': 4, 'placeholder': 'Observações…'}),
        }


class CollaboratorInsuranceNoteForm(forms.ModelForm):
    class Meta:
        model = CollaboratorInsuranceNote
        fields = ['insurance_fund', 'update_date', 'note', 'is_blocked', 'resolved_at']
        widgets = {
            'insurance_fund': forms.Select(attrs={'class': 'form-control'}),
            'update_date':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note':           forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                    'placeholder': 'Descreva a pendência, bloqueio ou situação…'}),
            'is_blocked':     forms.CheckboxInput(),
            'resolved_at':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class CollaboratorAddressForm(forms.ModelForm):
    class Meta:
        model = CollaboratorAddress
        fields = ['street', 'number', 'complement', 'city', 'postal_code', 'state', 'country', 'valid_from']
        widgets = {
            'street':      forms.TextInput(attrs={'class': 'form-control'}),
            'number':      forms.TextInput(attrs={'class': 'form-control'}),
            'complement':  forms.TextInput(attrs={'class': 'form-control'}),
            'city':        forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'state':       forms.TextInput(attrs={'class': 'form-control'}),
            'country':     forms.TextInput(attrs={'class': 'form-control'}),
            'valid_from':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class LegalFormForm(forms.ModelForm):
    class Meta:
        model = LegalForm
        fields = ['abbreviation', 'name', 'notes']
        widgets = {
            'abbreviation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: SRL, SA…'}),
            'name':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo da forma jurídica'}),
            'notes':        forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição ou observações…'}),
        }


class NationalityForm(forms.ModelForm):
    class Meta:
        model = Nationality
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Portuguesa, Belga…'})}


class LanguageForm(forms.ModelForm):
    class Meta:
        model = Language
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Português, Francês…'})}


class InsuranceFundForm(forms.ModelForm):
    class Meta:
        model = InsuranceFund
        fields = ['name', 'phone', 'email', 'address', 'notes']
        widgets = {
            'name':    forms.TextInput(attrs={'class': 'form-control'}),
            'phone':   forms.TextInput(attrs={'class': 'form-control'}),
            'email':   forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes':   forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InsuranceFundContactForm(forms.ModelForm):
    class Meta:
        model = InsuranceFundContact
        fields = ['name', 'role', 'phone', 'email', 'notes']
        widgets = {
            'name':  forms.TextInput(attrs={'class': 'form-control'}),
            'role':  forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class DriverLicenseForm(forms.ModelForm):
    class Meta:
        model = DriverLicense
        fields = [
            "license_number", "categories",
            "issue_date", "expiry_date", "issuing_municipality", "scan",
            "takes_vehicle_home", "private_use_authorized",
            "has_garage", "has_fixed_parking",
            "needs_parking_card", "parking_paid_by_company",
        ]
        widgets = {
            "issue_date":  forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }
        help_texts = {
            "categories": _("Comma-separated BE categories, e.g. B,BE,C"),
        }


class ParkingPermitForm(forms.ModelForm):
    class Meta:
        model = ParkingPermit
        fields = ["registration_date", "expiry_date", "amount", "notes"]
        widgets = {
            "registration_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expiry_date":       forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "amount":            forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes":             forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class CollaboratorHourlyRateCreateForm(forms.Form):
    hourly_rate = forms.DecimalField(
        label=_("Valor/hora"), max_digits=10, decimal_places=2, min_value=0,
    )
    start_date = forms.DateField(
        label=_("Data de início"), input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
