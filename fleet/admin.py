from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    VehicleCategory,
    Vehicle,
    VehicleDocument,
    VehicleMaintenance,
    VehicleFueling,
    VehicleFine,
    VehicleExpense,
)


@admin.register(VehicleCategory)
class VehicleCategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


class VehicleDocumentInline(admin.TabularInline):
    model = VehicleDocument
    extra = 0
    fields = ["doc_type", "description", "expiry_date", "insurer_or_entity", "reference", "cost"]


class VehicleMaintenanceInline(admin.TabularInline):
    model = VehicleMaintenance
    extra = 0
    fields = ["maintenance_type", "status", "scheduled_date", "description", "cost"]


class VehicleFuelingInline(admin.TabularInline):
    model = VehicleFueling
    extra = 0
    fields = ["date", "driver", "km", "liters", "total_cost", "station"]


class VehicleFineInline(admin.TabularInline):
    model = VehicleFine
    extra = 0
    fields = ["date", "driver", "amount", "status", "deduct_from_payroll"]


class VehicleExpenseInline(admin.TabularInline):
    model = VehicleExpense
    extra = 0
    fields = ["date", "expense_type", "description", "amount", "driver"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        "license_plate", "brand", "model", "year", "category",
        "fuel_type", "status", "current_km", "default_driver",
    ]
    list_filter = ["status", "category", "fuel_type"]
    search_fields = ["license_plate", "brand", "model", "vin"]
    inlines = [
        VehicleDocumentInline,
        VehicleMaintenanceInline,
        VehicleFuelingInline,
        VehicleFineInline,
        VehicleExpenseInline,
    ]


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "vehicle", "doc_type", "description", "expiry_date",
        "insurer_or_entity", "reference", "is_expired",
    ]
    list_filter = ["doc_type", "expiry_date"]
    search_fields = ["vehicle__license_plate", "reference", "insurer_or_entity"]

    @admin.display(boolean=True, description=_("Expired"))
    def is_expired(self, obj):
        return obj.is_expired


@admin.register(VehicleMaintenance)
class VehicleMaintenanceAdmin(admin.ModelAdmin):
    list_display = [
        "vehicle", "maintenance_type", "status",
        "scheduled_date", "completed_date", "workshop", "cost",
    ]
    list_filter = ["maintenance_type", "status"]
    search_fields = ["vehicle__license_plate", "description", "workshop"]


@admin.register(VehicleFueling)
class VehicleFuelingAdmin(admin.ModelAdmin):
    list_display = ["vehicle", "date", "driver", "km", "liters", "fuel_type", "total_cost", "station"]
    list_filter = ["fuel_type", "date"]
    search_fields = ["vehicle__license_plate", "driver__name", "station"]


@admin.register(VehicleFine)
class VehicleFineAdmin(admin.ModelAdmin):
    list_display = [
        "vehicle", "date", "driver", "amount", "points",
        "status", "deduct_from_payroll", "payroll_deducted",
    ]
    list_filter = ["status", "deduct_from_payroll", "payroll_deducted"]
    search_fields = ["vehicle__license_plate", "driver__name", "reference", "location"]


@admin.register(VehicleExpense)
class VehicleExpenseAdmin(admin.ModelAdmin):
    list_display = ["vehicle", "date", "expense_type", "description", "amount", "driver"]
    list_filter = ["expense_type"]
    search_fields = ["vehicle__license_plate", "description", "driver__name"]
