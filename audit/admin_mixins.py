from django.utils.html import format_html
from audit.models import AuditLog


class AuditHistoryMixin:
    """
    Mixin para exibir histórico de auditoria no admin
    """

    def audit_history(self, obj):
        if not obj:
            return "-"

        logs = AuditLog.objects.filter(
            model_name=obj.__class__.__name__,
            object_id=str(obj.pk)
        ).order_by('-created_at')[:20]

        if not logs:
            return "Sem histórico"

        html = "<div style='max-height:300px; overflow:auto; font-family: monospace;'>"

        for log in logs:
            html += "<div style='margin-bottom:12px;'>"

            html += f"""
                <div style="font-weight:bold;">
                    {log.created_at.strftime('%d/%m/%Y %H:%M:%S')} — {log.user or 'Sistema'}
                </div>
            """

            html += f"<div><em>{log.action.upper()}</em></div>"

            if isinstance(log.changes, dict):
                for field, change in log.changes.items():

                    if isinstance(change, dict) and 'old' in change:
                        html += f"""
                            <div>
                                <strong>{field}</strong>: 
                                <span style='color:red'>{change['old']}</span>
                                →
                                <span style='color:green'>{change['new']}</span>
                            </div>
                        """
                    else:
                        html += f"""
                            <div>
                                <strong>{field}</strong>: {change}
                            </div>
                        """

            html += "</div><hr>"

        html += "</div>"

        return format_html(html)

    audit_history.short_description = "Histórico de alterações"