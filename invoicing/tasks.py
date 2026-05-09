"""
Tarefas de invoicing.

Hoje são funções síncronas chamadas dentro do request — quando vier Celery,
basta decorar com `@shared_task` e trocar a chamada por `.delay(invoice_id)`.
Por isso recebem **IDs**, não objectos: tasks Celery serializam args.

Função idempotente: correr 2× não duplica o email; apenas envia outra vez. O
caller decide se quer evitar isso (ex: bloquear botão "Enviar" depois do
primeiro envio).
"""
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_invoice_email_task(
    invoice_id: int,
    *,
    to: list[str],
    cc: list[str] | None = None,
    subject: str | None = None,
    body: str | None = None,
) -> None:
    """
    Envia uma fatura por email com PDF anexo.

    Levanta exceção se SMTP falhar — caller deve apanhar e mostrar mensagem
    ao utilizador (a transação NÃO deve depender disto).
    """
    from weasyprint import HTML

    from .models import Invoice
    from .views import _prepare_print_context

    invoice = (
        Invoice.objects
        .select_related('client', 'project')
        .prefetch_related('lines', 'client__addresses', 'client__contacts')
        .get(pk=invoice_id)
    )

    # Render PDF
    ctx = _prepare_print_context_no_request(invoice)
    ctx['is_pdf'] = True
    html_string = render_to_string('invoicing/invoice_print.html', ctx)
    pdf_bytes = HTML(string=html_string).write_pdf()

    # Compose email
    if not subject:
        subject = f'Fatura {invoice.number} — {settings.COMPANY_NAME}'
    if not body:
        body = render_to_string('invoicing/email/invoice_body.txt', {
            'invoice': invoice,
            'company_name': settings.COMPANY_NAME,
        })

    msg = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
        cc=cc or [],
    )
    msg.attach(f'{invoice.number}.pdf', pdf_bytes, 'application/pdf')
    msg.send(fail_silently=False)
    logger.info('Invoice %s sent by email to %s', invoice.number, to)


def _prepare_print_context_no_request(invoice):
    """
    Versão simplificada do `_prepare_print_context` que não precisa de
    `request`. Útil para tasks (ex: cron que envia faturas em lote — Celery
    futuro). Não suporta `?template=<id>`; usa apenas o template default.
    """
    from document_templates.models import DocumentTemplate

    tmpl = (
        DocumentTemplate.objects.filter(
            document_type=DocumentTemplate.TYPE_INVOICE,
            status=DocumentTemplate.STATUS_ACTIVE,
            is_default=True,
        ).first()
        or DocumentTemplate.objects.filter(
            document_type=DocumentTemplate.TYPE_INVOICE,
            status=DocumentTemplate.STATUS_ACTIVE,
        ).first()
    )

    # Hierarchical numbering — duplicado do views.py mas trivial.
    counters = [0, 0, 0, 0]
    numbered_lines = []
    for line in invoice.lines.all().order_by('order'):
        lt = line.line_type
        num = ''
        if lt == 'title':
            counters[0] += 1; counters[1] = counters[2] = counters[3] = 0
            num = str(counters[0])
        elif lt == 'h2':
            counters[1] += 1; counters[2] = counters[3] = 0
            num = f'{counters[0]}.{counters[1]}'
        elif lt == 'h3':
            counters[2] += 1; counters[3] = 0
            num = f'{counters[0]}.{counters[1]}.{counters[2]}'
        elif lt == 'h4':
            counters[3] += 1
            num = f'{counters[0]}.{counters[1]}.{counters[2]}.{counters[3]}'
        numbered_lines.append((line, num))

    return {
        'invoice': invoice,
        'lines': numbered_lines,
        'sections': {},
        'tmpl': tmpl,
        'tmpl_choices': [],
        'has_template': bool(tmpl),
    }
