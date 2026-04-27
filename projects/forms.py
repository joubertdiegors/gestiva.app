from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Project

from clients.models import ClientContact


class ProjectForm(forms.ModelForm):

    start_date = forms.DateField(
        label=_("Start date"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
        required=False
    )

    end_date = forms.DateField(
        label=_("End date"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
        required=False
    )

    class Meta:
        model = Project
        fields = [
            'name',
            'client',
            'contacts',
            'address',
            'managers',
            'start_date',
            'end_date',
            'notes',
            'has_work_registration',
            'work_registration_type',
            'work_registration_number',
            'status',  # ✅ ADICIONADO
        ]

        widgets = {
            'name':    forms.TextInput(attrs={'class': 'form-control'}),
            'client':  forms.Select(attrs={'class': 'form-control'}),
            'status':  forms.Select(attrs={'class': 'form-control'}),
            'contacts': forms.SelectMultiple(attrs={'class': 'form-control', 'size': 5}),
            'managers': forms.SelectMultiple(attrs={'class': 'form-control', 'size': 4}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes':   forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'work_registration_type':   forms.Select(attrs={'class': 'form-control'}),
            'work_registration_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        has_registration = cleaned_data.get('has_work_registration')

        # 🔥 LIMPEZA DE DADOS
        if not has_registration:
            cleaned_data['work_registration_type'] = None
            cleaned_data['work_registration_number'] = None

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 POST
        if 'client' in self.data:
            try:
                client_id = int(self.data.get('client'))
                self.fields['contacts'].queryset = ClientContact.objects.filter(client_id=client_id)
            except (ValueError, TypeError):
                self.fields['contacts'].queryset = ClientContact.objects.none()

        # 🔥 EDIÇÃO
        elif self.instance.pk and self.instance.client:
            self.fields['contacts'].queryset = ClientContact.objects.filter(client=self.instance.client)

        # 🔥 CREATE
        else:
            self.fields['contacts'].queryset = ClientContact.objects.none()