from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Service, ServiceCategory, ServiceMaterial
from catalog.models import UnitOfMeasure, Product


class ServiceCategoryForm(forms.ModelForm):
    class Meta:
        model  = ServiceCategory
        fields = ['name', 'parent', 'is_active']
        widgets = {
            'name':      forms.TextInput(attrs={'class': 'form-control'}),
            'parent':    forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        qs = ServiceCategory.objects.filter(is_active=True)
        if instance and instance.pk:
            excluded = self._get_descendants(instance)
            excluded.add(instance.pk)
            qs = qs.exclude(pk__in=excluded)
        self.fields['parent'].queryset = qs
        self.fields['parent'].empty_label = _('— Sem categoria pai —')

    def _get_descendants(self, category):
        ids = set()
        for child in category.children.all():
            ids.add(child.pk)
            ids |= self._get_descendants(child)
        return ids


class ServiceForm(forms.ModelForm):
    class Meta:
        model  = Service
        fields = [
            'code', 'name', 'description',
            'category', 'unit',
            'time_per_unit',
            'labor_cost_per_unit',
            'sale_price_per_unit',
            'default_margin_percent',
            'is_active',
        ]
        widgets = {
            'code':                  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: CIM-001'}),
            'name':                  forms.TextInput(attrs={'class': 'form-control'}),
            'description':           forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category':              forms.Select(attrs={'class': 'form-control'}),
            'unit':                  forms.Select(attrs={'class': 'form-control'}),
            'time_per_unit':         forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'labor_cost_per_unit':   forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}),
            'sale_price_per_unit':   forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}),
            'default_margin_percent':forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'is_active':             forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = _('— Sem categoria —')
        self.fields['category'].queryset = (
            ServiceCategory.objects.filter(is_active=True).order_by('name')
        )
        self.fields['unit'].queryset = UnitOfMeasure.objects.order_by('symbol')


class ServiceMaterialForm(forms.ModelForm):
    class Meta:
        model  = ServiceMaterial
        fields = ['product', 'quantity_per_unit', 'waste_percent', 'note']
        widgets = {
            'product':          forms.Select(attrs={'class': 'form-control'}),
            'quantity_per_unit':forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}),
            'waste_percent':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'note':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Observação opcional')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = (
            Product.objects.filter(is_active=True)
            .select_related('unit')
            .order_by('name')
        )
        self.fields['product'].empty_label = _('— Selecione o produto —')
