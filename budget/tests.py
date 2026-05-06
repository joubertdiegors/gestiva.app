from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import UnitOfMeasure
from clients.models import Client
from services.models import Service, ServiceCategory

from .models import Budget, BudgetItem, BudgetItemMaterial

User = get_user_model()


def _user():
    return User.objects.create_user(username='tester', password='x')


def _client():
    return Client.objects.create(name='Test Client')


def _service():
    unit, _ = UnitOfMeasure.objects.get_or_create(name='un', symbol='un')
    cat, _  = ServiceCategory.objects.get_or_create(name='Test Cat')
    return Service.objects.create(
        name='Test Service',
        code='SRV-001',
        unit=unit,
        category=cat,
        labor_cost_per_unit=Decimal('10.00'),
    )


def _budget(service, client=None, discount=Decimal('0'), global_margin=None):
    b = Budget.objects.create(
        number='ORC-TEST-0001',
        title='Test Budget',
        client=client,
        discount_percent=discount,
        vat_rate=Decimal('23.00'),
        global_margin_percent=global_margin,
    )
    item = BudgetItem.objects.create(
        budget=b,
        service=service,
        service_name_snapshot=service.name,
        service_code_snapshot=service.code,
        service_unit_snapshot='un',
        quantity=Decimal('2.00'),
        labor_cost_per_unit=Decimal('10.00'),
        margin_percent=Decimal('20.00'),
        vat_rate=Decimal('23.00'),
    )
    return b, item


class BudgetTotalsTest(TestCase):

    def setUp(self):
        self.service = _service()

    def test_subtotal_ht_no_materials(self):
        # cost=10*2=20, margin 20% → unit_price=20/2*1.2=12, total_price=24
        b, item = _budget(self.service)
        self.assertEqual(item.total_cost, Decimal('20.00'))
        self.assertEqual(item.computed_unit_price, Decimal('12.0000'))
        self.assertEqual(item.total_price, Decimal('24.0000'))
        self.assertEqual(b.subtotal_ht, Decimal('24.0000'))

    def test_vat_and_total_ttc(self):
        b, _ = _budget(self.service)
        expected_vat = (Decimal('24.0000') * Decimal('23') / Decimal('100')).quantize(Decimal('0.0001'))
        self.assertEqual(b.total_vat, expected_vat)
        self.assertEqual(b.total_ttc, b.subtotal_ht + expected_vat)

    def test_global_discount(self):
        b, _ = _budget(self.service, discount=Decimal('10.00'))
        self.assertEqual(b.discount_amount, Decimal('2.40'))  # 24 * 10% = 2.40
        self.assertEqual(b.total_ht, Decimal('21.60'))  # 24 - 2.40

    def test_with_material(self):
        from catalog.models import Product
        unit, _ = UnitOfMeasure.objects.get_or_create(name='un', symbol='un')
        product = Product.objects.create(name='Cement', unit=unit)
        b, item = _budget(self.service)
        BudgetItemMaterial.objects.create(
            budget_item=item,
            product=product,
            product_name_snapshot='Cement',
            unit_snapshot='un',
            quantity=Decimal('3.00'),
            unit_price_snapshot=Decimal('5.00'),
        )
        # material_cost = 3 * 5 = 15; labor = 10*2 = 20 → total_cost = 35
        self.assertEqual(item.total_material_cost, Decimal('15.00'))
        self.assertEqual(item.total_cost, Decimal('35.00'))

    def test_unit_price_override(self):
        b, item = _budget(self.service)
        item.unit_price_override = Decimal('15.00')
        item.save()
        self.assertEqual(item.effective_unit_price, Decimal('15.00'))
        self.assertEqual(item.total_price, Decimal('30.0000'))  # 15 * 2

    def test_gross_margin_percent(self):
        b, _ = _budget(self.service)
        # total_ht=24, total_cost=20 → margin = 4/24 * 100 = 16.67%
        self.assertAlmostEqual(float(b.gross_margin_percent), 16.67, places=1)

    def test_next_number_sequence(self):
        import datetime
        year = datetime.date.today().year
        n1 = Budget.next_number()
        self.assertEqual(n1, f'ORC-{year}-0001')
        Budget.objects.create(number=n1, title='B1')
        n2 = Budget.next_number()
        self.assertEqual(n2, f'ORC-{year}-0002')

    def test_next_number_gap_safe(self):
        import datetime
        year = datetime.date.today().year
        Budget.objects.create(number=f'ORC-{year}-0099', title='B99')
        n = Budget.next_number()
        self.assertEqual(n, f'ORC-{year}-0100')
