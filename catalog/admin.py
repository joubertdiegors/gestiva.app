from django.contrib import admin
from .models import UnitOfMeasure, ProductCategory, Product


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display  = ['symbol', 'name']
    search_fields = ['symbol', 'name']


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'parent', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display    = ['name', 'brand', 'category', 'unit', 'is_active', 'is_approved']
    list_filter     = ['is_active', 'is_approved', 'category']
    search_fields   = ['name', 'brand', 'barcode']
    readonly_fields = ['best_purchase_price', 'sale_price_ht', 'sale_price_ttc', 'created_at', 'updated_at']
