from django.contrib import admin
from .models import Subcontractor, SubcontractorAddress


class SubcontractorAddressInline(admin.TabularInline):
    model = SubcontractorAddress
    extra = 1


@admin.register(Subcontractor)
class SubcontractorAdmin(admin.ModelAdmin):
    list_display = ('name', 'legal_form', 'vat_number', 'status')
    list_filter = ('status',)
    search_fields = ('name', 'vat_number')
    ordering = ('name',)
    inlines = [SubcontractorAddressInline]
