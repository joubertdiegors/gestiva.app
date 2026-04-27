from django.contrib import admin
from django.utils.html import format_html
import json

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'action', 'object_id', 'user', 'created_at')
    list_filter = ('action', 'model_name', 'user', 'created_at')
    search_fields = ('object_id', 'model_name')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'formatted_changes', 'created_at')

    def formatted_changes(self, obj):
        if not obj.changes:
            return "-"

        html = "<div style='font-family: monospace;'>"

        if isinstance(obj.changes, dict) and all(
            isinstance(v, dict) and 'old' in v and 'new' in v
            for v in obj.changes.values()
        ):
            for field, values in obj.changes.items():
                html += f"""
                <div style="margin-bottom:10px;">
                    <strong>{field}</strong><br>
                    <span style="color:red;">{values['old']}</span>
                    →
                    <span style="color:green;">{values['new']}</span>
                </div>
                """
        else:
            pretty_json = json.dumps(obj.changes, indent=2, ensure_ascii=False)
            html += f"<pre>{pretty_json}</pre>"

        html += "</div>"

        return format_html(html)

    formatted_changes.short_description = "Alterações"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False