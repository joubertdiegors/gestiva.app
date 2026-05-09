"""
Testes finance — Payment sync, Payable/Receivable status (Sprint 3).
"""
from decimal import Decimal

import pytest

from finance.models import Payable, Payment, Receivable
from finance.services import sync_payable_status, sync_receivable_status
from invoicing.models import Invoice
from tests.factories import (
    InvoiceFactory,
    InvoiceLineFactory,
    PayableFactory,
    PaymentFactory,
    ReceivableFactory,
)


@pytest.mark.django_db
class TestPayableSync:
    def test_status_pending_with_no_payments(self):
        p = PayableFactory(amount=Decimal('100'))
        sync_payable_status(p)
        p.refresh_from_db()
        assert p.status == Payable.Status.PENDING

    def test_status_partial_when_under_paid(self, user):
        p = PayableFactory(amount=Decimal('100'))
        PaymentFactory(payable=p, amount=Decimal('40'), created_by=user)
        p.refresh_from_db()
        assert p.status == Payable.Status.PARTIAL
        assert p.amount_remaining == Decimal('60')

    def test_status_paid_when_fully_covered(self, user):
        p = PayableFactory(amount=Decimal('100'))
        PaymentFactory(payable=p, amount=Decimal('100'), created_by=user)
        p.refresh_from_db()
        assert p.status == Payable.Status.PAID

    def test_status_paid_when_overpaid(self, user):
        """Pagar mais do que o devido também conta como pago."""
        p = PayableFactory(amount=Decimal('100'))
        PaymentFactory(payable=p, amount=Decimal('150'), created_by=user)
        p.refresh_from_db()
        assert p.status == Payable.Status.PAID

    def test_deleting_payment_reverts_status(self, user):
        p = PayableFactory(amount=Decimal('100'))
        pay = PaymentFactory(payable=p, amount=Decimal('100'), created_by=user)
        p.refresh_from_db()
        assert p.status == Payable.Status.PAID
        pay.delete()
        p.refresh_from_db()
        assert p.status == Payable.Status.PENDING


@pytest.mark.django_db
class TestReceivableSync:
    def _build(self, **overrides):
        invoice = InvoiceFactory()
        InvoiceLineFactory(invoice=invoice, quantity=Decimal('1'), unit_price=Decimal('100'), vat_rate=Decimal('0'))
        invoice.refresh_from_db()
        defaults = {
            'invoice': invoice,
            'client': invoice.client,
            'amount': invoice.total_ttc,
        }
        defaults.update(overrides)
        return ReceivableFactory(**defaults)

    def test_pending_with_no_payments(self):
        rec = self._build()
        sync_receivable_status(rec)
        rec.refresh_from_db()
        assert rec.status == Receivable.Status.PENDING

    def test_partial_when_under_paid(self, user):
        rec = self._build()
        PaymentFactory(receivable=rec, amount=Decimal('30'), created_by=user)
        rec.refresh_from_db()
        assert rec.status == Receivable.Status.PARTIAL

    def test_paid_when_fully_covered(self, user):
        rec = self._build()
        PaymentFactory(receivable=rec, amount=rec.amount, created_by=user)
        rec.refresh_from_db()
        assert rec.status == Receivable.Status.PAID

    def test_paying_receivable_propagates_to_invoice(self, user):
        rec = self._build()
        invoice = rec.invoice
        invoice.status = Invoice.Status.SENT
        invoice.save()
        PaymentFactory(receivable=rec, amount=rec.amount, created_by=user)
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.PAID

    def test_partial_payment_propagates_partial_status_to_invoice(self, user):
        rec = self._build()
        invoice = rec.invoice
        invoice.status = Invoice.Status.SENT
        invoice.save()
        PaymentFactory(receivable=rec, amount=rec.amount / 2, created_by=user)
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.PARTIAL

    def test_does_not_overwrite_draft_invoice(self, user):
        """Faturas DRAFT não devem mudar de status só por causa de pagamentos."""
        rec = self._build()
        invoice = rec.invoice
        invoice.status = Invoice.Status.DRAFT
        invoice.save()
        PaymentFactory(receivable=rec, amount=rec.amount, created_by=user)
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.DRAFT


@pytest.mark.django_db
class TestPaymentXorConstraint:
    """
    O CheckConstraint `payment_has_exactly_one_parent` deve impedir um
    Payment com ambos (ou nenhum) parent.
    """

    def test_payment_without_any_parent_violates_constraint(self, user):
        with pytest.raises(Exception):
            Payment.objects.create(
                date='2026-05-01',
                amount=Decimal('10'),
                created_by=user,
            )
