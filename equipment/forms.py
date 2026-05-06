from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Equipment, EquipmentCategory, EquipmentLoan, EquipmentSale

FC = {"class": "form-control"}


class EquipmentCategoryForm(forms.ModelForm):
    class Meta:
        model = EquipmentCategory
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs=FC)}


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = [
            "category", "name", "brand", "model", "serial_number", "internal_code",
            "status", "condition", "purchase_date", "purchase_price", "notes",
        ]
        widgets = {
            "category": forms.Select(attrs=FC),
            "name": forms.TextInput(attrs=FC),
            "brand": forms.TextInput(attrs=FC),
            "model": forms.TextInput(attrs=FC),
            "serial_number": forms.TextInput(attrs=FC),
            "internal_code": forms.TextInput(attrs=FC),
            "status": forms.Select(attrs=FC),
            "condition": forms.Select(attrs=FC),
            "purchase_date": forms.DateInput(attrs={"type": "date", **FC}),
            "purchase_price": forms.NumberInput(attrs=FC),
            "notes": forms.Textarea(attrs={"rows": 3, **FC}),
        }


class EquipmentLoanForm(forms.ModelForm):
    class Meta:
        model = EquipmentLoan
        fields = ["collaborator", "loaned_at", "expected_return", "notes"]
        widgets = {
            "collaborator": forms.Select(attrs=FC),
            "loaned_at": forms.DateTimeInput(attrs={"type": "datetime-local", **FC}),
            "expected_return": forms.DateInput(attrs={"type": "date", **FC}),
            "notes": forms.Textarea(attrs={"rows": 2, **FC}),
        }


class EquipmentReturnForm(forms.ModelForm):
    class Meta:
        model = EquipmentLoan
        fields = ["returned_at", "notes"]
        widgets = {
            "returned_at": forms.DateTimeInput(attrs={"type": "datetime-local", **FC}),
            "notes": forms.Textarea(attrs={"rows": 2, **FC}),
        }


class EquipmentSaleForm(forms.ModelForm):
    class Meta:
        model = EquipmentSale
        fields = [
            "collaborator", "sale_date", "sale_price", "installments",
            "amount_paid", "status", "notes",
        ]
        widgets = {
            "collaborator": forms.Select(attrs=FC),
            "sale_date": forms.DateInput(attrs={"type": "date", **FC}),
            "sale_price": forms.NumberInput(attrs=FC),
            "installments": forms.NumberInput(attrs=FC),
            "amount_paid": forms.NumberInput(attrs=FC),
            "status": forms.Select(attrs=FC),
            "notes": forms.Textarea(attrs={"rows": 2, **FC}),
        }
