from django.contrib import admin
from .models import Supplier, SupplierAddress, SupplierContact


class SupplierAddressInline(admin.TabularInline):
    model = SupplierAddress
    extra = 1


class SupplierContactInline(admin.TabularInline):
    model = SupplierContact
    extra = 1


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'vat_number', 'is_active')
    search_fields = ('name', 'vat_number')
    inlines = [SupplierAddressInline, SupplierContactInline]
