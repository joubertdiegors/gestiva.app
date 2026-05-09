"""
Testes budget — BudgetItem.computed_unit_price, totais e overrides (Sprint 3).
"""
from decimal import Decimal

import pytest

from budget.services import compute_budget_totals, compute_item_unit_price
from tests.factories import (
    BudgetFactory,
    BudgetItemFactory,
    BudgetItemMaterialFactory,
)


@pytest.mark.django_db
class TestBudgetItemTotals:
    def test_total_labor_cost(self):
        item = BudgetItemFactory(
            quantity=Decimal('5'),
            labor_cost_per_unit=Decimal('20'),
        )
        assert item.total_labor_cost == Decimal('100')

    def test_total_material_cost_aggregates_materials(self):
        item = BudgetItemFactory(quantity=Decimal('1'), labor_cost_per_unit=Decimal('0'))
        BudgetItemMaterialFactory(
            budget_item=item, quantity=Decimal('2'), unit_price_snapshot=Decimal('5'),
        )
        BudgetItemMaterialFactory(
            budget_item=item, quantity=Decimal('1'), unit_price_snapshot=Decimal('10'),
        )
        assert item.total_material_cost == Decimal('20')

    def test_total_cost_combines_labor_and_materials(self):
        item = BudgetItemFactory(
            quantity=Decimal('1'),
            labor_cost_per_unit=Decimal('30'),
        )
        BudgetItemMaterialFactory(
            budget_item=item, quantity=Decimal('1'), unit_price_snapshot=Decimal('10'),
        )
        assert item.total_cost == Decimal('40')


@pytest.mark.django_db
class TestBudgetItemPricing:
    def test_computed_unit_price_with_margin(self):
        item = BudgetItemFactory(
            quantity=Decimal('1'),
            labor_cost_per_unit=Decimal('100'),
            margin_percent=Decimal('30'),
        )
        # cost=100, +30% = 130
        assert item.computed_unit_price == Decimal('130')

    def test_effective_unit_price_uses_override_when_set(self):
        item = BudgetItemFactory(
            quantity=Decimal('1'),
            labor_cost_per_unit=Decimal('100'),
            margin_percent=Decimal('30'),
            unit_price_override=Decimal('200'),
        )
        assert item.effective_unit_price == Decimal('200')

    def test_effective_unit_price_ignores_zero_override(self):
        item = BudgetItemFactory(
            quantity=Decimal('1'),
            labor_cost_per_unit=Decimal('100'),
            margin_percent=Decimal('30'),
            unit_price_override=Decimal('0'),
        )
        # 0 não conta como override válido — devolve computed
        assert item.effective_unit_price == item.computed_unit_price

    def test_computed_unit_price_zero_quantity(self):
        item = BudgetItemFactory.build(
            quantity=Decimal('0'),
            labor_cost_per_unit=Decimal('100'),
            margin_percent=Decimal('30'),
        )
        # build() não persiste — total_cost depende de materials.all() que falharia
        # em build mode; testamos via service que tem o mesmo guard.
        assert compute_item_unit_price(item) == Decimal('0')

    def test_total_price_applies_line_discount(self):
        item = BudgetItemFactory(
            quantity=Decimal('2'),
            labor_cost_per_unit=Decimal('50'),  # cost 50 × 2 = 100
            margin_percent=Decimal('0'),  # preço unit = 50
            discount_percent=Decimal('10'),
        )
        # total_price_before_discount = 100; -10% = 90
        assert item.total_price == Decimal('90.0000')

    def test_vat_amount_uses_line_rate(self):
        item = BudgetItemFactory(
            quantity=Decimal('1'),
            labor_cost_per_unit=Decimal('100'),
            margin_percent=Decimal('0'),
            vat_rate=Decimal('21'),
        )
        # total_price=100, vat=21
        assert item.vat_amount == Decimal('21.0000')


@pytest.mark.django_db
class TestBudgetTotals:
    def test_subtotal_ht_with_multiple_items(self, client_obj):
        budget = BudgetFactory(client=client_obj)
        BudgetItemFactory(
            budget=budget, quantity=Decimal('1'),
            labor_cost_per_unit=Decimal('100'), margin_percent=Decimal('0'),
        )
        BudgetItemFactory(
            budget=budget, quantity=Decimal('2'),
            labor_cost_per_unit=Decimal('25'), margin_percent=Decimal('0'),
        )
        # 100 + 50 = 150
        assert budget.subtotal_ht == Decimal('150')

    def test_global_discount_applies(self, client_obj):
        budget = BudgetFactory(client=client_obj, discount_percent=Decimal('10'))
        BudgetItemFactory(
            budget=budget, quantity=Decimal('1'),
            labor_cost_per_unit=Decimal('200'), margin_percent=Decimal('0'),
        )
        # 200 - 10% = 180
        assert budget.total_ht == Decimal('180')

    def test_gross_margin_amount(self, client_obj):
        budget = BudgetFactory(client=client_obj)
        BudgetItemFactory(
            budget=budget, quantity=Decimal('1'),
            labor_cost_per_unit=Decimal('100'), margin_percent=Decimal('25'),
        )
        # cost=100, total_ht=125, margem=25
        assert budget.gross_margin_amount == Decimal('25')

    def test_compute_budget_totals_matches_properties(self, client_obj):
        budget = BudgetFactory(client=client_obj, discount_percent=Decimal('5'))
        BudgetItemFactory(
            budget=budget, quantity=Decimal('1'),
            labor_cost_per_unit=Decimal('100'), margin_percent=Decimal('20'),
            vat_rate=Decimal('21'),
        )
        result = compute_budget_totals(budget)
        assert result['subtotal_ht'] == budget.subtotal_ht
        assert result['total_ht'] == budget.total_ht
        assert result['total_vat'] == budget.total_vat
        assert result['total_ttc'] == budget.total_ttc
