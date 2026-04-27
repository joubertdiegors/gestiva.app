from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Budget, BudgetChapter, BudgetItem


class BudgetForm(forms.ModelForm):
    issue_date = forms.DateField(
        label=_("Data de emissão"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
        required=False,
    )
    valid_until = forms.DateField(
        label=_("Válido até"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
        required=False,
    )

    class Meta:
        model  = Budget
        fields = [
            'number', 'title', 'client', 'project',
            'issue_date', 'valid_until',
            'global_margin_percent', 'discount_percent', 'vat_rate',
            'payment_terms', 'notes', 'notes_client',
        ]
        widgets = {
            'number':               forms.TextInput(attrs={'class': 'form-control'}),
            'title':                forms.TextInput(attrs={'class': 'form-control'}),
            'client':               forms.Select(attrs={'class': 'form-control', 'id': 'id_client'}),
            'project':              forms.Select(attrs={'class': 'form-control', 'id': 'id_project'}),
            'global_margin_percent':forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'discount_percent':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'vat_rate':             forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'payment_terms':        forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes':                forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes_client':         forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BudgetChapterForm(forms.ModelForm):
    class Meta:
        model  = BudgetChapter
        fields = ['title', 'parent', 'order']
        widgets = {
            'title':  forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'order':  forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def __init__(self, *args, budget=None, **kwargs):
        super().__init__(*args, **kwargs)
        if budget:
            qs = BudgetChapter.objects.filter(budget=budget)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            self.fields['parent'].queryset = qs
        else:
            self.fields['parent'].queryset = BudgetChapter.objects.none()
        self.fields['parent'].required = False
        self.fields['order'].required  = False


class BudgetItemForm(forms.ModelForm):
    class Meta:
        model  = BudgetItem
        fields = [
            'service', 'chapter', 'description',
            'quantity', 'unit_price_override',
            'labor_cost_per_unit', 'margin_percent',
            'discount_percent', 'vat_rate', 'order',
        ]
        widgets = {
            'service':            forms.Select(attrs={'class': 'form-control'}),
            'chapter':            forms.Select(attrs={'class': 'form-control'}),
            'description':        forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'quantity':           forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}),
            'unit_price_override':forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}),
            'labor_cost_per_unit':forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}),
            'margin_percent':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percent':   forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'vat_rate':           forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'order':              forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def __init__(self, *args, budget=None, **kwargs):
        super().__init__(*args, **kwargs)
        if budget:
            self.fields['chapter'].queryset = BudgetChapter.objects.filter(budget=budget)
        else:
            self.fields['chapter'].queryset = BudgetChapter.objects.none()
        self.fields['chapter'].required          = False
        self.fields['description'].required      = False
        self.fields['unit_price_override'].required = False
        self.fields['order'].required            = False
