"""
Camada de serviço de invoicing — Sprint 3 (incremental) + Sprint 4.

Aqui vivem regras de negócio que estavam coladas a views/AJAX e que precisam
de ser testadas em isolamento. Mantém-se ao mínimo: cada função recebe os
ids/instâncias de que precisa, abre a sua transação onde for relevante e
devolve o objecto manipulado.
"""
import datetime
from decimal import Decimal

from django.db import transaction


def compute_invoice_totals(invoice) -> dict:
    """
    Recalcula totais de uma fatura a partir das suas linhas.

    Não persiste nada — devolve apenas um dicionário com Decimals para uso
    em respostas AJAX e em testes unitários. Cabe ao caller decidir se
    serializa para string.
    """
    lines = list(invoice.lines.all())
    subtotal_ht = sum((line.total_ht for line in lines), Decimal('0'))
    discount_amount = (
        subtotal_ht * invoice.discount_percent / Decimal('100')
    ).quantize(Decimal('0.01'))
    total_ht = subtotal_ht - discount_amount
    total_vat = sum((line.vat_amount for line in lines), Decimal('0'))
    total_ttc = total_ht + total_vat
    return {
        'subtotal_ht': subtotal_ht,
        'discount_amount': discount_amount,
        'total_ht': total_ht,
        'total_vat': total_vat,
        'total_ttc': total_ttc,
    }


def ensure_receivable_for_invoice(invoice):
    """
    Garante existência (e amount actualizado) de Receivable para a fatura.

    Não devia correr em invoices DRAFT — o caller controla isso. Devolve a
    Receivable resultante.
    """
    from finance.models import Receivable

    with transaction.atomic():
        receivable, _ = Receivable.objects.get_or_create(
            invoice=invoice,
            defaults={
                'client': invoice.client,
                'project': invoice.project,
                'amount': invoice.total_ttc,
                'issue_date': invoice.issue_date,
                'due_date': invoice.due_date,
                'status': Receivable.Status.PENDING,
            },
        )
        new_amount = invoice.total_ttc
        if receivable.amount != new_amount:
            receivable.amount = new_amount
            receivable.save(update_fields=['amount', 'updated_at'])
    return receivable


def create_invoice_from_budget(budget, user, *, issue_date=None):
    """
    Cria uma nova fatura DRAFT (`invoice_type=from_budget`) copiando linhas
    de um orçamento. Usa `effective_unit_price` (que respeita override) e
    inclui chapters como linhas de título (`title`).

    Idempotência: cada chamada cria uma fatura nova. O caller é responsável
    por evitar duplicação se for indesejável.
    """
    from .models import Invoice, InvoiceLine

    with transaction.atomic():
        invoice = Invoice.objects.create(
            number=Invoice.next_number(),
            title=budget.title or '',
            client=budget.client,
            project=budget.project,
            budget=budget,
            issue_date=issue_date or datetime.date.today(),
            status=Invoice.Status.DRAFT,
            invoice_type=Invoice.InvoiceType.FROM_BUDGET,
            discount_percent=budget.discount_percent,
            vat_rate=budget.vat_rate,
            payment_terms=budget.payment_terms,
            notes_client=budget.notes_client,
            created_by=user,
        )

        # Group items by chapter to preserve hierarchy as title lines.
        order = 0
        items = list(
            budget.items.select_related('chapter', 'service').order_by('chapter_id', 'order')
        )
        last_chapter_id = object()  # sentinel — first iteration always differs
        for item in items:
            chapter = item.chapter
            if chapter and getattr(chapter, 'id', None) != last_chapter_id:
                order += 10
                InvoiceLine.objects.create(
                    invoice=invoice,
                    order=order,
                    line_type=InvoiceLine.LineType.TITLE,
                    description=chapter.name if chapter else '',
                )
                last_chapter_id = chapter.id

            order += 10
            InvoiceLine.objects.create(
                invoice=invoice,
                order=order,
                line_type=InvoiceLine.LineType.LINE,
                description=item.service_name_snapshot,
                detail=item.description or '',
                quantity=item.quantity,
                unit=item.service_unit_snapshot or '',
                unit_price=item.effective_unit_price,
                discount_percent=item.discount_percent,
                vat_rate=item.vat_rate,
                budget_item=item,
            )

    return invoice


def create_credit_note_from_invoice(origin_invoice, user, *, issue_date=None):
    """
    Cria uma nota de crédito (`invoice_type=credit_note`) que estorna uma
    fatura existente. Linhas copiadas com **quantidade negativa** para que
    `total_ht`/`total_ttc` saiam negativos automaticamente. Liga
    `credit_note_origin` à fatura origem.

    Não altera o status da fatura origem — esse fluxo (CANCELLED ou manter
    PAID) é decisão de negócio do utilizador.
    """
    from .models import Invoice, InvoiceLine

    with transaction.atomic():
        credit_note = Invoice.objects.create(
            number=Invoice.next_number(),
            title=f'Avoir — {origin_invoice.number}',
            client=origin_invoice.client,
            project=origin_invoice.project,
            credit_note_origin=origin_invoice,
            issue_date=issue_date or datetime.date.today(),
            status=Invoice.Status.DRAFT,
            invoice_type=Invoice.InvoiceType.CREDIT_NOTE,
            discount_percent=origin_invoice.discount_percent,
            vat_rate=origin_invoice.vat_rate,
            billing_name=origin_invoice.billing_name,
            billing_address=origin_invoice.billing_address,
            billing_vat=origin_invoice.billing_vat,
            payment_terms=origin_invoice.payment_terms,
            created_by=user,
        )
        for src in origin_invoice.lines.all().order_by('order'):
            qty = src.quantity
            if src.line_type == InvoiceLine.LineType.LINE:
                qty = -src.quantity
            InvoiceLine.objects.create(
                invoice=credit_note,
                order=src.order,
                line_type=src.line_type,
                description=src.description,
                detail=src.detail,
                quantity=qty,
                unit=src.unit,
                unit_price=src.unit_price,
                discount_percent=src.discount_percent,
                vat_rate=src.vat_rate,
            )

    return credit_note
