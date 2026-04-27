from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    Vehicle,
    VehicleCategory,
    VehicleDocument,
    VehicleMaintenance,
    VehicleFueling,
    VehicleFine,
    VehicleExpense,
)


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "license_plate", "brand", "model", "year", "color", "vin",
            "category", "fuel_type", "status", "current_km", "default_driver", "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class VehicleCategoryForm(forms.ModelForm):
    class Meta:
        model = VehicleCategory
        fields = ["name"]


class VehicleDocumentForm(forms.ModelForm):
    class Meta:
        model = VehicleDocument
        fields = [
            "doc_type", "description", "issue_date", "expiry_date",
            "insurer_or_entity", "reference", "cost", "file", "notes",
        ]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class VehicleMaintenanceForm(forms.ModelForm):
    class Meta:
        model = VehicleMaintenance
        fields = [
            "maintenance_type", "status", "description",
            "scheduled_date", "completed_date", "km_at_service", "next_service_km",
            "workshop", "cost", "invoice_reference", "notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "scheduled_date": forms.DateInput(attrs={"type": "date"}),
            "completed_date": forms.DateInput(attrs={"type": "date"}),
        }


class VehicleFuelingForm(forms.ModelForm):
    class Meta:
        model = VehicleFueling
        fields = [
            "driver", "date", "km", "liters", "fuel_type",
            "price_per_liter", "total_cost", "station", "full_tank", "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class VehicleFineForm(forms.ModelForm):
    class Meta:
        model = VehicleFine
        fields = [
            "driver", "date", "location", "offence_description",
            "amount", "points", "reference", "status", "paid_date",
            "deduct_from_payroll", "payroll_deducted", "payroll_deducted_date",
            "file", "notes",
        ]
        widgets = {
            "offence_description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "date": forms.DateInput(attrs={"type": "date"}),
            "paid_date": forms.DateInput(attrs={"type": "date"}),
            "payroll_deducted_date": forms.DateInput(attrs={"type": "date"}),
        }


class VehicleExpenseForm(forms.ModelForm):
    class Meta:
        model = VehicleExpense
        fields = ["expense_type", "date", "description", "amount", "driver", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
