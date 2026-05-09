"""
Testes do Sprint 4 — pronto para vender.

Cobre:
- SoftDeleteMixin: managers `objects` (vivos) e `all_objects`, restore, hard.
- Validação VAT BE em Client/Supplier/Subcontractor.clean().
- `create_invoice_from_budget` (copia linhas, respeita override de preço).
- `create_credit_note_from_invoice` (quantidades negadas, link de origem).

Testes de WeasyPrint e SMTP ficam fora do CI local (Windows não tem GTK
instalado por defeito) — são exercitados em produção/PythonAnywhere.
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from invoicing.models import Invoice, InvoiceLine
from invoicing.services import (
    create_credit_note_from_invoice,
    create_invoice_from_budget,
)

from .factories import (
    BudgetFactory,
    BudgetItemFactory,
    ClientFactory,
    InvoiceFactory,
    InvoiceLineFactory,
    SubcontractorFactory,
    SupplierFactory,
    UserFactory,
)


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSoftDelete:
    def test_default_manager_hides_deleted(self, client_obj):
        client_obj.delete()
        assert client_obj.is_deleted is True
        assert client_obj.deleted_at is not None
        from clients.models import Client
        assert not Client.objects.filter(pk=client_obj.pk).exists()
        assert Client.all_objects.filter(pk=client_obj.pk).exists()

    def test_restore(self, client_obj):
        client_obj.delete()
        client_obj.refresh_from_db()
        assert client_obj.is_deleted is True
        client_obj.restore()
        client_obj.refresh_from_db()
        assert client_obj.is_deleted is False
        assert client_obj.deleted_at is None

    def test_hard_delete(self, client_obj):
        pk = client_obj.pk
        client_obj.delete(hard=True)
        from clients.models import Client
        assert not Client.all_objects.filter(pk=pk).exists()

    def test_queryset_bulk_soft_delete(self):
        from clients.models import Client
        ClientFactory.create_batch(3)
        Client.objects.all().delete()
        assert Client.objects.count() == 0
        assert Client.all_objects.count() == 3

    def test_invoice_soft_delete(self, invoice):
        invoice.delete()
        assert Invoice.objects.filter(pk=invoice.pk).exists() is False
        assert Invoice.all_objects.filter(pk=invoice.pk).exists() is True


# ── VAT BE validation ─────────────────────────────────────────────────────────

VALID_BE_VAT = 'BE0403170701'  # número público real (Belgacom) — checksum válido


@pytest.mark.django_db
class TestVatValidation:
    def test_valid_vat_passes(self):
        c = ClientFactory.build(vat_number=VALID_BE_VAT)
        c.full_clean()  # não deve levantar

    def test_invalid_vat_raises(self):
        c = ClientFactory.build(vat_number='BE0000000000')
        with pytest.raises(ValidationError) as exc:
            c.full_clean()
        assert 'vat' in str(exc.value).lower() or 'invalid' in str(exc.value).lower()

    def test_empty_vat_passes(self):
        c = ClientFactory.build(vat_number='')
        c.full_clean()

    def test_supplier_vat_validation(self):
        s = SupplierFactory.build(vat_number='BE_lixo_123')
        with pytest.raises(ValidationError):
            s.full_clean()

    def test_subcontractor_vat_validation(self):
        s = SubcontractorFactory.build(vat_number='nao-e-vat')
        with pytest.raises(ValidationError):
            s.full_clean()

    def test_vat_normalized_on_clean(self):
        c = ClientFactory.build(vat_number='BE 0403.170.701')
        c.full_clean()
        assert c.vat_number == VALID_BE_VAT


# ── create_invoice_from_budget ────────────────────────────────────────────────

@pytest.mark.django_db
class TestCreateInvoiceFromBudget:
    def test_copies_lines_with_effective_price(self, client_obj):
        user = UserFactory()
        budget = BudgetFactory(client=client_obj)
        BudgetItemFactory(
            budget=budget,
            quantity=Decimal('2'),
            unit_price_override=Decimal('100.0000'),
            margin_percent=Decimal('30'),
            discount_percent=Decimal('0'),
            vat_rate=Decimal('21'),
        )
        BudgetItemFactory(
            budget=budget,
            quantity=Decimal('1'),
            unit_price_override=Decimal('50.0000'),
            margin_percent=Decimal('0'),
            discount_percent=Decimal('0'),
            vat_rate=Decimal('21'),
        )

        invoice = create_invoice_from_budget(budget, user)

        assert invoice.invoice_type == Invoice.InvoiceType.FROM_BUDGET
        assert invoice.budget_id == budget.pk
        assert invoice.client_id == budget.client_id
        assert invoice.status == Invoice.Status.DRAFT

        line_lines = list(invoice.lines.filter(line_type=InvoiceLine.LineType.LINE))
        assert len(line_lines) == 2
        assert line_lines[0].unit_price == Decimal('100.0000')
        assert line_lines[1].unit_price == Decimal('50.0000')

    def test_independent_invoice_number(self, client_obj):
        user = UserFactory()
        budget = BudgetFactory(client=client_obj)
        BudgetItemFactory(budget=budget, quantity=Decimal('1'), unit_price_override=Decimal('10'))

        inv1 = create_invoice_from_budget(budget, user)
        inv2 = create_invoice_from_budget(budget, user)
        assert inv1.number != inv2.number


# ── create_credit_note_from_invoice ───────────────────────────────────────────

@pytest.mark.django_db
class TestCreateCreditNote:
    def test_credit_note_negates_quantities(self, invoice):
        InvoiceLineFactory(
            invoice=invoice, quantity=Decimal('3'), unit_price=Decimal('100'),
        )
        InvoiceLineFactory(
            invoice=invoice, quantity=Decimal('1'), unit_price=Decimal('50'),
        )
        user = UserFactory()

        cn = create_credit_note_from_invoice(invoice, user)

        assert cn.invoice_type == Invoice.InvoiceType.CREDIT_NOTE
        assert cn.credit_note_origin_id == invoice.pk
        assert cn.client_id == invoice.client_id
        assert cn.total_ht < Decimal('0')

        for src, dst in zip(invoice.lines.order_by('order'), cn.lines.order_by('order')):
            if dst.line_type == InvoiceLine.LineType.LINE:
                assert dst.quantity == -src.quantity

    def test_credit_note_total_mirrors_origin(self, invoice):
        InvoiceLineFactory(
            invoice=invoice, quantity=Decimal('2'), unit_price=Decimal('100'),
            vat_rate=Decimal('21'),
        )
        user = UserFactory()
        cn = create_credit_note_from_invoice(invoice, user)
        assert cn.total_ttc == -invoice.total_ttc

    def test_origin_invoice_status_unchanged(self, invoice):
        InvoiceLineFactory(invoice=invoice)
        original_status = invoice.status
        user = UserFactory()
        create_credit_note_from_invoice(invoice, user)
        invoice.refresh_from_db()
        assert invoice.status == original_status
