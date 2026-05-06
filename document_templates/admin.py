from django.contrib import admin
from .models import DocumentTemplate


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display  = ('name', 'document_type', 'status', 'is_system', 'is_default', 'created_at')
    list_filter   = ('document_type', 'status', 'is_system')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'created_by')
