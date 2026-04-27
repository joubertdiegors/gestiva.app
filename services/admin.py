from django.contrib import admin
from .models import ServiceCategory, Service, ServiceMaterial


class ServiceMaterialInline(admin.TabularInline):
    model           = ServiceMaterial
    extra           = 1
    readonly_fields = ['effective_quantity']


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'parent', 'is_active']
    search_fields = ['name']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display    = ['code', 'name', 'unit', 'labor_cost_per_unit', 'default_margin_percent', 'is_active']
    list_filter     = ['is_active', 'category']
    search_fields   = ['code', 'name']
    readonly_fields = ['material_cost_per_unit', 'total_cost_per_unit', 'suggested_price_per_unit']
    inlines         = [ServiceMaterialInline]
