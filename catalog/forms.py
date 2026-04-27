from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Product, ProductCategory, UnitOfMeasure


class UnitOfMeasureForm(forms.ModelForm):
    class Meta:
        model  = UnitOfMeasure
        fields = ['symbol', 'name', 'description']
        widgets = {
            'symbol':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'kg, m², un…'}),
            'name':        forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model  = ProductCategory
        fields = ['name', 'parent', 'is_active']
        widgets = {
            'name':      forms.TextInput(attrs={'class': 'form-control'}),
            'parent':    forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        qs = ProductCategory.objects.filter(is_active=True)
        if instance and instance.pk:
            # Impede seleccionar a si própria ou descendentes como pai
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


class ProductForm(forms.ModelForm):
    class Meta:
        model  = Product
        fields = [
            'name', 'brand', 'barcode',
            'category', 'unit',
            'vat_rate', 'sale_margin',
            'notes', 'is_active', 'is_approved',
        ]
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control'}),
            'brand':       forms.TextInput(attrs={'class': 'form-control'}),
            'barcode':     forms.TextInput(attrs={'class': 'form-control'}),
            'category':    forms.Select(attrs={'class': 'form-control'}),
            'unit':        forms.Select(attrs={'class': 'form-control'}),
            'vat_rate':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'sale_margin': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active':   forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = _('— Sem categoria —')
        self.fields['category'].queryset = (
            ProductCategory.objects.filter(is_active=True).order_by('name')
        )
        self.fields['unit'].queryset = UnitOfMeasure.objects.order_by('symbol')
