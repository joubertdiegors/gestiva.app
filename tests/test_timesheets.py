"""
Testes do Timesheet — agora fonte única de mão-de-obra (Sprint 3).

Verifica `effective_rate`, `total_cost`, `computed_hours` e o snapshot
automático do hourly_rate via CollaboratorHourlyRate.
"""
import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from tests.factories import (
    CollaboratorHourlyRateFactory,
    TimesheetFactory,
)


@pytest.mark.django_db
class TestTimesheetTotals:
    def test_effective_rate_normal(self):
        ts = TimesheetFactory(
            hours=Decimal('8'),
            hourly_rate_snapshot=Decimal('25'),
            is_overtime=False,
        )
        assert ts.effective_rate == Decimal('25')

    def test_effective_rate_overtime_applies_multiplier(self):
        ts = TimesheetFactory(
            hours=Decimal('2'),
            hourly_rate_snapshot=Decimal('25'),
            is_overtime=True,
            overtime_rate=Decimal('1.50'),
        )
        assert ts.effective_rate == Decimal('25') * Decimal('1.50')

    def test_total_cost_normal(self):
        ts = TimesheetFactory(
            hours=Decimal('8'),
            hourly_rate_snapshot=Decimal('25'),
        )
        assert ts.total_cost == Decimal('200.00')

    def test_total_cost_overtime(self):
        ts = TimesheetFactory(
            hours=Decimal('2'),
            hourly_rate_snapshot=Decimal('30'),
            is_overtime=True,
            overtime_rate=Decimal('2'),
        )
        # 2h × (30 × 2) = 120
        assert ts.total_cost == Decimal('120.00')

    def test_total_cost_zero_when_no_rate(self):
        ts = TimesheetFactory(
            hours=Decimal('8'),
            hourly_rate_snapshot=None,
        )
        assert ts.total_cost == Decimal('0')


@pytest.mark.django_db
class TestTimesheetComputedHours:
    def test_computed_hours_from_start_end(self):
        ts = TimesheetFactory(
            hours=None,
            start_time=datetime.time(8, 0),
            end_time=datetime.time(17, 30),
        )
        assert ts.computed_hours == Decimal('9.50')

    def test_computed_hours_falls_back_to_hours_field(self):
        ts = TimesheetFactory(
            hours=Decimal('6.5'),
            start_time=None,
            end_time=None,
        )
        assert ts.computed_hours == Decimal('6.5')


@pytest.mark.django_db
class TestTimesheetClean:
    def test_end_must_be_after_start(self):
        ts = TimesheetFactory.build(
            start_time=datetime.time(17, 0),
            end_time=datetime.time(8, 0),
        )
        with pytest.raises(ValidationError):
            ts.clean()

    def test_requires_either_hours_or_start(self):
        ts = TimesheetFactory.build(
            hours=None,
            start_time=None,
            end_time=None,
        )
        with pytest.raises(ValidationError):
            ts.clean()


@pytest.mark.django_db
class TestTimesheetHourlyRateSnapshot:
    """
    Quando o Timesheet é gravado sem hourly_rate_snapshot explícito, deve
    buscar a tarifa válida em CollaboratorHourlyRate para a data — e
    congelar esse valor para auditoria.
    """

    def test_picks_active_rate_on_save(self, collaborator):
        CollaboratorHourlyRateFactory(
            collaborator=collaborator,
            hourly_rate=Decimal('22.50'),
            start_date=datetime.date(2026, 1, 1),
            end_date=None,
        )
        ts = TimesheetFactory(
            worker=collaborator,
            date=datetime.date(2026, 5, 1),
            hourly_rate_snapshot=None,
        )
        ts.refresh_from_db()
        assert ts.hourly_rate_snapshot == Decimal('22.50')

    def test_does_not_overwrite_explicit_snapshot(self, collaborator):
        CollaboratorHourlyRateFactory(
            collaborator=collaborator,
            hourly_rate=Decimal('22.50'),
            start_date=datetime.date(2026, 1, 1),
        )
        ts = TimesheetFactory(
            worker=collaborator,
            hourly_rate_snapshot=Decimal('40'),
        )
        ts.refresh_from_db()
        assert ts.hourly_rate_snapshot == Decimal('40')


@pytest.mark.django_db
class TestProjectTimesheetsRelation:
    """
    Confirma que `project.timesheets` é o canal único para listagem de
    mão-de-obra na vista do projecto (após eliminação de ProjectLabourEntry).
    """

    def test_project_exposes_timesheets_via_related_name(self, project, collaborator):
        TimesheetFactory(
            project=project,
            worker=collaborator,
            hours=Decimal('5'),
            hourly_rate_snapshot=Decimal('30'),
        )
        labour = list(project.timesheets.all())
        assert len(labour) == 1
        assert labour[0].total_cost == Decimal('150.00')
