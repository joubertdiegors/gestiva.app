from django.contrib import admin
from .models import Budget, BudgetItem, BudgetItemMaterial


class BudgetItemMaterialInline(admin.TabularInline):
    model           = BudgetItemMaterial
    extra           = 0
    readonly_fields = ['total_cost']


class BudgetItemInline(admin.StackedInline):
    model            = BudgetItem
    extra            = 0
    readonly_fields  = ['total_cost', 'total_price', 'effective_unit_price']
    show_change_link = True


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display    = ['number', 'title', 'client', 'status', 'total_ht', 'total_ttc', 'created_at']
    list_filter     = ['status']
    search_fields   = ['number', 'title']
    readonly_fields = ['subtotal_cost', 'subtotal_ht', 'total_ht', 'total_vat',
                       'total_ttc', 'gross_margin_amount', 'gross_margin_percent',
                       'created_at', 'updated_at']
    inlines         = [BudgetItemInline]
