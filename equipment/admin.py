from django.contrib import admin
from .models import Equipment, EquipmentCategory, EquipmentLoan, EquipmentSale


@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ["internal_code", "name", "brand", "model", "category", "status", "condition"]
    list_filter = ["status", "condition", "category"]
    search_fields = ["name", "brand", "model", "serial_number", "internal_code"]


@admin.register(EquipmentLoan)
class EquipmentLoanAdmin(admin.ModelAdmin):
    list_display = ["equipment", "collaborator", "loaned_at", "expected_return", "returned_at"]
    list_filter = ["returned_at"]
    search_fields = ["equipment__name", "collaborator__name"]


@admin.register(EquipmentSale)
class EquipmentSaleAdmin(admin.ModelAdmin):
    list_display = ["equipment", "collaborator", "sale_date", "sale_price", "amount_paid", "status"]
    list_filter = ["status"]
    search_fields = ["equipment__name", "collaborator__name"]
