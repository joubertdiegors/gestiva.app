from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ProductSupplier


class ProductSupplierForm(forms.ModelForm):
    price_note = forms.CharField(
        label=_("Motivo (histórico)"),
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text=_("Opcional. Se o preço mudar, salva no histórico."),
    )

    class Meta:
        model = ProductSupplier
        fields = [
            'product',
            'supplier',
            'supplier_ref',
            'supplier_description',
            'unit_price',
            'package_qty',
            'package_unit',
            'minimum_order_qty',
            'lead_time_days',
            'is_preferred',
            'is_active',
            'valid_from',
            'valid_until',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'supplier_ref': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier_description': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}
            ),
            'package_qty': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}
            ),
            'package_unit': forms.Select(attrs={'class': 'form-control'}),
            'minimum_order_qty': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}
            ),
            'lead_time_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_preferred': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()

        vf = cleaned.get('valid_from')
        vu = cleaned.get('valid_until')
        if vf and vu and vu < vf:
            self.add_error('valid_until', _("A data final deve ser maior ou igual à data inicial."))

        package_qty = cleaned.get('package_qty')
        if package_qty is not None and package_qty <= 0:
            self.add_error('package_qty', _("Quantidade por embalagem deve ser maior que zero."))

        minimum_order_qty = cleaned.get('minimum_order_qty')
        if minimum_order_qty is not None and minimum_order_qty <= 0:
            self.add_error('minimum_order_qty', _("Quantidade mínima deve ser maior que zero."))

        return cleaned

