"""
Testes Invoice — totais e numeração (Sprint 3).
"""
import datetime
from decimal import Decimal

import pytest

from invoicing.models import Invoice
from invoicing.services import compute_invoice_totals, ensure_receivable_for_invoice
from tests.factories import (
    InvoiceFactory,
    InvoiceLineFactory,
)


@pytest.mark.django_db
class TestInvoiceLineTotals:
    def test_line_total_ht_no_discount(self):
        line = InvoiceLineFactory(
            quantity=Decimal('3'),
            unit_price=Decimal('10'),
            discount_percent=Decimal('0'),
        )
        assert line.total_ht == Decimal('30')

    def test_line_total_ht_with_discount(self):
        line = InvoiceLineFactory(
            quantity=Decimal('2'),
            unit_price=Decimal('100'),
            discount_percent=Decimal('10'),
        )
        # 200 - 10% = 180
        assert line.total_ht == Decimal('180.0000')

    def test_line_vat_amount_uses_line_rate(self):
        line = InvoiceLineFactory(
            quantity=Decimal('1'),
            unit_price=Decimal('100'),
            vat_rate=Decimal('6'),
        )
        assert line.vat_amount == Decimal('6.0000')

    def test_line_total_ttc(self):
        line = InvoiceLineFactory(
            quantity=Decimal('1'),
            unit_price=Decimal('100'),
            vat_rate=Decimal('21'),
        )
        assert line.total_ttc == Decimal('121.0000')


@pytest.mark.django_db
class TestInvoiceTotals:
    def test_subtotal_with_multiple_lines(self, invoice):
        InvoiceLineFactory(invoice=invoice, quantity=Decimal('1'), unit_price=Decimal('100'))
        InvoiceLineFactory(invoice=invoice, quantity=Decimal('2'), unit_price=Decimal('50'))
        assert invoice.subtotal_ht == Decimal('200.0000')

    def test_global_discount_applies_to_subtotal(self, invoice):
        invoice.discount_percent = Decimal('10')
        invoice.save()
        InvoiceLineFactory(invoice=invoice, quantity=Decimal('1'), unit_price=Decimal('100'))
        InvoiceLineFactory(invoice=invoice, quantity=Decimal('1'), unit_price=Decimal('100'))
        # 200 - 10% = 180
        assert invoice.total_ht == Decimal('180.0000')

    def test_total_ttc_combines_ht_and_vat(self, invoice):
        InvoiceLineFactory(
            invoice=invoice, quantity=Decimal('1'),
            unit_price=Decimal('100'), vat_rate=Decimal('21'),
        )
        assert invoice.total_ttc == Decimal('121.0000')

    def test_amount_due_with_no_payments(self, invoice):
        InvoiceLineFactory(invoice=invoice, quantity=Decimal('1'), unit_price=Decimal('100'))
        assert invoice.amount_paid == Decimal('0')
        assert invoice.amount_due == invoice.total_ttc


@pytest.mark.django_db
class TestInvoiceServiceTotals:
    def test_compute_invoice_totals_matches_properties(self, invoice):
        invoice.discount_percent = Decimal('5')
        invoice.save()
        InvoiceLineFactory(invoice=invoice, quantity=Decimal('1'), unit_price=Decimal('100'), vat_rate=Decimal('21'))
        InvoiceLineFactory(invoice=invoice, quantity=Decimal('2'), unit_price=Decimal('50'), vat_rate=Decimal('21'))
        result = compute_invoice_totals(invoice)
        assert result['subtotal_ht'] == invoice.subtotal_ht
        assert result['total_ht'] == invoice.total_ht
        assert result['total_vat'] == invoice.total_vat
        assert result['total_ttc'] == invoice.total_ttc


@pytest.mark.django_db
class TestInvoiceNumbering:
    def test_next_number_first_of_year(self):
        nb = Invoice.next_number()
        year = datetime.date.today().year
        assert nb == f'FAT-{year}-0001'

    def test_next_number_increments(self, client_obj, user):
        InvoiceFactory(
            number=f'FAT-{datetime.date.today().year}-0007',
            client=client_obj,
            created_by=user,
        )
        nb = Invoice.next_number()
        assert nb == f'FAT-{datetime.date.today().year}-0008'


@pytest.mark.django_db
class TestEnsureReceivable:
    def test_creates_receivable_with_invoice_total(self, invoice):
        InvoiceLineFactory(invoice=invoice, quantity=Decimal('1'), unit_price=Decimal('100'))
        rec = ensure_receivable_for_invoice(invoice)
        assert rec.amount == invoice.total_ttc
        assert rec.client_id == invoice.client_id

    def test_updates_receivable_amount_when_lines_change(self, invoice):
        line = InvoiceLineFactory(invoice=invoice, quantity=Decimal('1'), unit_price=Decimal('100'))
        rec = ensure_receivable_for_invoice(invoice)
        original_total = rec.amount

        line.unit_price = Decimal('200')
        line.save()
        rec = ensure_receivable_for_invoice(invoice)
        assert rec.amount != original_total
        assert rec.amount == invoice.total_ttc
