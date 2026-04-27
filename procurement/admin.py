from django.contrib import admin
from .models import (
    ProductSupplier,
    ProductSupplierPriceHistory,
    RFQ,
    RFQItem,
    RFQVendor,
    RFQVendorLine,
)


class PriceHistoryInline(admin.TabularInline):
    model           = ProductSupplierPriceHistory
    extra           = 0
    readonly_fields = ['price', 'effective_date', 'changed_by']
    can_delete      = False


@admin.register(ProductSupplier)
class ProductSupplierAdmin(admin.ModelAdmin):
    list_display  = ['product', 'supplier', 'unit_price', 'is_preferred', 'is_active']
    list_filter   = ['is_preferred', 'is_active']
    search_fields = ['product__name', 'supplier__name', 'supplier_ref']
    inlines       = [PriceHistoryInline]


class RFQItemInline(admin.TabularInline):
    model = RFQItem
    extra = 0


class RFQVendorInline(admin.TabularInline):
    model = RFQVendor
    extra = 0


@admin.register(RFQ)
class RFQAdmin(admin.ModelAdmin):
    list_display = ['number', 'status', 'due_date', 'requested_by', 'created_at']
    list_filter = ['status']
    search_fields = ['number', 'requested_by__username', 'requested_by__first_name', 'requested_by__last_name']
    inlines = [RFQItemInline, RFQVendorInline]


@admin.register(RFQVendorLine)
class RFQVendorLineAdmin(admin.ModelAdmin):
    list_display = ['rfq_vendor', 'rfq_item', 'unit_price', 'answered_at', 'updated_at']
    list_filter = ['answered_at']
