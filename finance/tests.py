import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from clients.models import Client
from finance.models import Payable, Receivable, Payment

User = get_user_model()


def _user():
    return User.objects.get_or_create(username='fin_tester', defaults={'password': 'x'})[0]


def _client():
    return Client.objects.get_or_create(name='Finance Test Client')[0]


def _payable(amount=Decimal('100.00'), user=None):
    return Payable.objects.create(
        description='Test payable',
        amount=amount,
        issue_date=datetime.date.today(),
        created_by=user or _user(),
    )


def _receivable(amount=Decimal('100.00'), user=None, client=None):
    return Receivable.objects.create(
        client=client or _client(),
        amount=amount,
        issue_date=datetime.date.today(),
    )


def _pay(payable=None, receivable=None, amount=Decimal('50.00'), user=None):
    return Payment.objects.create(
        payable=payable,
        receivable=receivable,
        date=datetime.date.today(),
        amount=amount,
        created_by=user or _user(),
    )


# ── Payable.sync_status ───────────────────────────────────────────────────────

class PayableSyncStatusTest(TestCase):

    def setUp(self):
        self.user = _user()

    def test_no_payments_stays_pending(self):
        p = _payable(user=self.user)
        p.sync_status()
        self.assertEqual(p.status, Payable.Status.PENDING)

    def test_partial_payment_sets_partial(self):
        p = _payable(amount=Decimal('100.00'), user=self.user)
        _pay(payable=p, amount=Decimal('40.00'), user=self.user)
        p.sync_status()
        p.refresh_from_db()
        self.assertEqual(p.status, Payable.Status.PARTIAL)

    def test_full_payment_sets_paid(self):
        p = _payable(amount=Decimal('100.00'), user=self.user)
        _pay(payable=p, amount=Decimal('100.00'), user=self.user)
        p.sync_status()
        p.refresh_from_db()
        self.assertEqual(p.status, Payable.Status.PAID)

    def test_overpayment_sets_paid(self):
        p = _payable(amount=Decimal('100.00'), user=self.user)
        _pay(payable=p, amount=Decimal('120.00'), user=self.user)
        p.sync_status()
        p.refresh_from_db()
        self.assertEqual(p.status, Payable.Status.PAID)

    def test_multiple_payments_accumulate(self):
        p = _payable(amount=Decimal('100.00'), user=self.user)
        _pay(payable=p, amount=Decimal('30.00'), user=self.user)
        _pay(payable=p, amount=Decimal('70.00'), user=self.user)
        p.sync_status()
        p.refresh_from_db()
        self.assertEqual(p.status, Payable.Status.PAID)


# ── Receivable.sync_status ────────────────────────────────────────────────────

class ReceivableSyncStatusTest(TestCase):

    def setUp(self):
        self.user  = _user()
        self.client = _client()

    def test_no_payments_stays_pending(self):
        r = _receivable(client=self.client)
        r.sync_status()
        self.assertEqual(r.status, Receivable.Status.PENDING)

    def test_partial_payment_sets_partial(self):
        r = _receivable(amount=Decimal('200.00'), client=self.client)
        _pay(receivable=r, amount=Decimal('80.00'), user=self.user)
        r.sync_status()
        r.refresh_from_db()
        self.assertEqual(r.status, Receivable.Status.PARTIAL)

    def test_full_payment_sets_paid(self):
        r = _receivable(amount=Decimal('200.00'), client=self.client)
        _pay(receivable=r, amount=Decimal('200.00'), user=self.user)
        r.sync_status()
        r.refresh_from_db()
        self.assertEqual(r.status, Receivable.Status.PAID)

    def test_sync_updates_linked_invoice(self):
        from invoicing.models import Invoice
        inv = Invoice.objects.create(
            number='FAT-TEST-0001',
            client=self.client,
            issue_date=datetime.date.today(),
            status=Invoice.Status.SENT,
            created_by=self.user,
        )
        r = Receivable.objects.create(
            invoice=inv,
            client=self.client,
            amount=Decimal('100.00'),
            issue_date=datetime.date.today(),
        )
        _pay(receivable=r, amount=Decimal('50.00'), user=self.user)
        r.sync_status()
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'partial')

    def test_sync_sets_invoice_paid(self):
        from invoicing.models import Invoice
        inv = Invoice.objects.create(
            number='FAT-TEST-0002',
            client=self.client,
            issue_date=datetime.date.today(),
            status=Invoice.Status.SENT,
            created_by=self.user,
        )
        r = Receivable.objects.create(
            invoice=inv,
            client=self.client,
            amount=Decimal('100.00'),
            issue_date=datetime.date.today(),
        )
        _pay(receivable=r, amount=Decimal('100.00'), user=self.user)
        r.sync_status()
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'paid')


# ── Invoice.next_number ───────────────────────────────────────────────────────

class InvoiceNextNumberTest(TestCase):

    def setUp(self):
        self.user   = _user()
        self.client = _client()

    def _inv(self, number):
        from invoicing.models import Invoice
        return Invoice.objects.create(
            number=number,
            client=self.client,
            issue_date=datetime.date.today(),
            created_by=self.user,
        )

    def test_first_number(self):
        from invoicing.models import Invoice
        import datetime as dt
        year = dt.date.today().year
        self.assertEqual(Invoice.next_number(), f'FAT-{year}-0001')

    def test_increments_sequence(self):
        from invoicing.models import Invoice
        import datetime as dt
        year = dt.date.today().year
        self._inv(f'FAT-{year}-0001')
        self.assertEqual(Invoice.next_number(), f'FAT-{year}-0002')

    def test_gap_safe(self):
        from invoicing.models import Invoice
        import datetime as dt
        year = dt.date.today().year
        self._inv(f'FAT-{year}-0050')
        self.assertEqual(Invoice.next_number(), f'FAT-{year}-0051')

    def test_uniqueness(self):
        from invoicing.models import Invoice
        import datetime as dt
        year = dt.date.today().year
        numbers = set()
        for _ in range(5):
            n = Invoice.next_number()
            self.assertNotIn(n, numbers)
            numbers.add(n)
            self._inv(n)
        self.assertEqual(len(numbers), 5)
