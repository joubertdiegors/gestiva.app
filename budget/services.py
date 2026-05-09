"""
Camada de serviço de budget.

- Sprint 3: `compute_item_unit_price`, `compute_budget_totals`.
- Sprint 5: `lock_budget`, `unlock_budget`, `snapshot_budget` —
  versioning de orçamentos APPROVED.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone


def compute_item_unit_price(item) -> Decimal:
    """
    Devolve o preço unitário efectivo de uma linha de orçamento.

    Replica `BudgetItem.effective_unit_price` mas isolado em função para
    facilitar testes e futuras variações (ex.: aplicar margens globais).
    """
    if item.unit_price_override and item.unit_price_override > 0:
        return item.unit_price_override
    if not item.quantity:
        return Decimal('0')
    margin_factor = Decimal('1') + (item.margin_percent / Decimal('100'))
    return (item.total_cost / item.quantity) * margin_factor


def compute_budget_totals(budget) -> dict:
    """
    Recalcula totais agregados do orçamento a partir das suas linhas.

    Não persiste nada — todos os valores são Decimal. O caller decide
    formatação.
    """
    items = list(budget.items.all())
    subtotal_cost = sum((item.total_cost for item in items), Decimal('0'))
    subtotal_ht = sum((item.total_price for item in items), Decimal('0'))
    discount_amount = (
        subtotal_ht * budget.discount_percent / Decimal('100')
    ).quantize(Decimal('0.01'))
    total_ht = subtotal_ht - discount_amount
    total_vat = sum((item.vat_amount for item in items), Decimal('0'))
    total_ttc = total_ht + total_vat
    return {
        'subtotal_cost': subtotal_cost,
        'subtotal_ht': subtotal_ht,
        'discount_amount': discount_amount,
        'total_ht': total_ht,
        'total_vat': total_vat,
        'total_ttc': total_ttc,
        'gross_margin_amount': total_ht - subtotal_cost,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 5 — versioning / lock
# ─────────────────────────────────────────────────────────────────────────────

class BudgetLockedError(Exception):
    """Tentativa de editar um orçamento bloqueado."""


def _serialize_decimal(value) -> str:
    """Decimal → string com 4 casas (preserva precisão completa do modelo)."""
    if value is None:
        return ''
    if isinstance(value, Decimal):
        return str(value)
    return str(Decimal(str(value)))


def snapshot_budget(budget) -> dict:
    """
    Devolve a estrutura completa do orçamento como dict serializável.

    Inclui dados de cabeçalho, capítulos, linhas, materiais e totais
    calculados. JSON-friendly (todos os Decimal → string).
    """
    from .models import BudgetChapter, BudgetItem

    chapters = list(BudgetChapter.objects.filter(budget=budget).order_by('order', 'id'))
    items = list(
        BudgetItem.objects
        .filter(budget=budget)
        .select_related('chapter', 'service')
        .prefetch_related('materials')
        .order_by('chapter__order', 'order', 'id')
    )
    totals = compute_budget_totals(budget)

    return {
        'budget': {
            'id': budget.pk,
            'external_id': str(budget.external_id),
            'number': budget.number,
            'title': budget.title,
            'status': budget.status,
            'client_id': budget.client_id,
            'client_name': budget.client.name if budget.client else '',
            'project_id': budget.project_id,
            'project_name': budget.project.name if budget.project else '',
            'issue_date': budget.issue_date.isoformat() if budget.issue_date else '',
            'valid_until': budget.valid_until.isoformat() if budget.valid_until else '',
            'global_margin_percent': _serialize_decimal(budget.global_margin_percent),
            'discount_percent': _serialize_decimal(budget.discount_percent),
            'vat_rate': _serialize_decimal(budget.vat_rate),
            'notes': budget.notes,
            'notes_client': budget.notes_client,
            'payment_terms': budget.payment_terms,
        },
        'chapters': [
            {
                'id': ch.pk,
                'parent_id': ch.parent_id,
                'title': ch.title,
                'order': ch.order,
            }
            for ch in chapters
        ],
        'items': [
            {
                'id': it.pk,
                'chapter_id': it.chapter_id,
                'service_id': it.service_id,
                'service_name': it.service_name_snapshot,
                'service_code': it.service_code_snapshot,
                'service_unit': it.service_unit_snapshot,
                'description': it.description,
                'quantity': _serialize_decimal(it.quantity),
                'unit_price_override': _serialize_decimal(it.unit_price_override),
                'effective_unit_price': _serialize_decimal(it.effective_unit_price),
                'labor_cost_per_unit': _serialize_decimal(it.labor_cost_per_unit),
                'margin_percent': _serialize_decimal(it.margin_percent),
                'discount_percent': _serialize_decimal(it.discount_percent),
                'vat_rate': _serialize_decimal(it.vat_rate),
                'order': it.order,
                'total_cost': _serialize_decimal(it.total_cost),
                'total_price': _serialize_decimal(it.total_price),
                'vat_amount': _serialize_decimal(it.vat_amount),
                'materials': [
                    {
                        'product_id': m.product_id,
                        'supplier_id': m.supplier_id,
                        'product_name': m.product_name_snapshot,
                        'unit': m.unit_snapshot,
                        'quantity': _serialize_decimal(m.quantity),
                        'unit_price': _serialize_decimal(m.unit_price_snapshot),
                    }
                    for m in it.materials.all()
                ],
            }
            for it in items
        ],
        'totals': {k: _serialize_decimal(v) for k, v in totals.items()},
    }


def lock_budget(budget, user, *, reason: str = 'manual'):
    """
    Marca o orçamento como locked + grava `BudgetVersion` com snapshot.

    Idempotente: chamar em orçamento já locked não cria novo snapshot
    nem altera nada. Usar `unlock_budget` antes para reabrir.
    """
    from .models import BudgetVersion

    if budget.is_locked:
        return budget.versions.order_by('-version_number').first()

    with transaction.atomic():
        # Re-lê com select_for_update para evitar race com outro lock paralelo.
        budget.__class__.objects.select_for_update().filter(pk=budget.pk).first()

        next_version = (
            budget.versions.order_by('-version_number')
            .values_list('version_number', flat=True)
            .first()
            or 0
        ) + 1

        now = timezone.now()
        version = BudgetVersion.objects.create(
            budget=budget,
            version_number=next_version,
            locked_at=now,
            locked_by=user if user and user.is_authenticated else None,
            reason=reason or 'manual',
            snapshot=snapshot_budget(budget),
        )

        budget.is_locked = True
        budget.locked_at = now
        budget.locked_by = user if user and user.is_authenticated else None
        budget.save(update_fields=['is_locked', 'locked_at', 'locked_by'])

    return version


def unlock_budget(budget, user):
    """
    Remove o lock para permitir edição. Não apaga BudgetVersion existentes
    — a história fica preservada. Próxima `lock_budget` cria v(N+1).
    """
    if not budget.is_locked:
        return budget

    budget.is_locked = False
    budget.locked_at = None
    budget.locked_by = None
    budget.save(update_fields=['is_locked', 'locked_at', 'locked_by'])
    return budget


def assert_editable(budget):
    """Lança `BudgetLockedError` se o orçamento estiver bloqueado."""
    if budget.is_locked:
        raise BudgetLockedError(
            f"Budget {budget.number} is locked at version "
            f"{budget.versions.count()}. Unlock before editing."
        )
