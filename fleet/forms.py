from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import (
    Vehicle,
    VehicleCategory,
    VehicleDocument,
    VehicleMaintenance,
    VehicleFueling,
    VehicleFine,
    VehicleExpense,
)

FC = {"class": "form-control"}
FC_SM = {"class": "form-control form-control-sm"}


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "fleet_number", "license_plate", "brand", "model", "year", "color", "vin",
            "category", "fuel_type", "status", "current_km", "default_driver", "notes",
        ]
        widgets = {
            "fleet_number": forms.NumberInput(attrs=FC),
            "license_plate": forms.TextInput(attrs=FC),
            "brand": forms.TextInput(attrs=FC),
            "model": forms.TextInput(attrs=FC),
            "year": forms.NumberInput(attrs=FC),
            "color": forms.TextInput(attrs=FC),
            "vin": forms.TextInput(attrs=FC),
            "category": forms.Select(attrs=FC),
            "fuel_type": forms.Select(attrs=FC),
            "status": forms.Select(attrs=FC),
            "current_km": forms.NumberInput(attrs=FC),
            "default_driver": forms.Select(attrs=FC),
            "notes": forms.Textarea(attrs={"rows": 3, **FC}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fleet_number = cleaned_data.get("fleet_number")
        status = cleaned_data.get("status")

        if fleet_number is not None:
            active_statuses = [Vehicle.STATUS_ACTIVE, Vehicle.STATUS_MAINTENANCE]
            if status in active_statuses:
                qs = Vehicle.objects.filter(
                    fleet_number=fleet_number,
                    status__in=active_statuses,
                )
                if self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    self.add_error(
                        "fleet_number",
                        ValidationError(
                            _("Fleet number %(n)s is already assigned to an active vehicle."),
                            params={"n": fleet_number},
                        ),
                    )
        return cleaned_data


class VehicleCategoryForm(forms.ModelForm):
    class Meta:
        model = VehicleCategory
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs=FC),
        }


class VehicleDocumentForm(forms.ModelForm):
    class Meta:
        model = VehicleDocument
        fields = [
            "doc_type", "description", "issue_date", "expiry_date",
            "insurer_or_entity", "reference", "cost", "file", "notes",
        ]
        widgets = {
            "doc_type": forms.Select(attrs=FC),
            "description": forms.TextInput(attrs=FC),
            "issue_date": forms.DateInput(attrs={"type": "date", **FC}),
            "expiry_date": forms.DateInput(attrs={"type": "date", **FC}),
            "insurer_or_entity": forms.TextInput(attrs=FC),
            "reference": forms.TextInput(attrs=FC),
            "cost": forms.NumberInput(attrs=FC),
            "notes": forms.Textarea(attrs={"rows": 3, **FC}),
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
            "maintenance_type": forms.Select(attrs=FC),
            "status": forms.Select(attrs=FC),
            "description": forms.Textarea(attrs={"rows": 3, **FC}),
            "scheduled_date": forms.DateInput(attrs={"type": "date", **FC}),
            "completed_date": forms.DateInput(attrs={"type": "date", **FC}),
            "km_at_service": forms.NumberInput(attrs=FC),
            "next_service_km": forms.NumberInput(attrs=FC),
            "workshop": forms.TextInput(attrs=FC),
            "cost": forms.NumberInput(attrs=FC),
            "invoice_reference": forms.TextInput(attrs=FC),
            "notes": forms.Textarea(attrs={"rows": 3, **FC}),
        }


class VehicleFuelingForm(forms.ModelForm):
    class Meta:
        model = VehicleFueling
        fields = [
            "driver", "date", "km", "liters", "fuel_type",
            "price_per_liter", "total_cost", "station", "full_tank", "notes",
        ]
        widgets = {
            "driver": forms.Select(attrs=FC),
            "date": forms.DateInput(attrs={"type": "date", **FC}),
            "km": forms.NumberInput(attrs=FC),
            "liters": forms.NumberInput(attrs=FC),
            "fuel_type": forms.Select(attrs=FC),
            "price_per_liter": forms.NumberInput(attrs=FC),
            "total_cost": forms.NumberInput(attrs=FC),
            "station": forms.TextInput(attrs=FC),
            "notes": forms.Textarea(attrs={"rows": 2, **FC}),
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
            "driver": forms.Select(attrs=FC),
            "date": forms.DateInput(attrs={"type": "date", **FC}),
            "location": forms.TextInput(attrs=FC),
            "offence_description": forms.Textarea(attrs={"rows": 3, **FC}),
            "amount": forms.NumberInput(attrs=FC),
            "points": forms.NumberInput(attrs=FC),
            "reference": forms.TextInput(attrs=FC),
            "status": forms.Select(attrs=FC),
            "paid_date": forms.DateInput(attrs={"type": "date", **FC}),
            "payroll_deducted_date": forms.DateInput(attrs={"type": "date", **FC}),
            "notes": forms.Textarea(attrs={"rows": 3, **FC}),
        }


class VehicleExpenseForm(forms.ModelForm):
    class Meta:
        model = VehicleExpense
        fields = ["expense_type", "date", "description", "amount", "driver", "notes"]
        widgets = {
            "expense_type": forms.Select(attrs=FC),
            "date": forms.DateInput(attrs={"type": "date", **FC}),
            "description": forms.TextInput(attrs=FC),
            "amount": forms.NumberInput(attrs=FC),
            "driver": forms.Select(attrs=FC),
            "notes": forms.Textarea(attrs={"rows": 2, **FC}),
        }
