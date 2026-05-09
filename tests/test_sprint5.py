"""
Testes do Sprint 5 — 1º cliente em produção.

Cobre:
- Lock e versionamento de orçamentos (snapshot, edição bloqueada,
  unlock + re-lock cria v2).
- Decorador `otp_required` e middleware `OTPGateMiddleware`.
- Aprovação automática (status APPROVED + lock + BudgetVersion).

Não testa fluxos visuais de OTP (QR/templates) nem o registro real do
TOTPDevice — Django-otp tem testes próprios.
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings
from django.urls import reverse

from budget.models import Budget, BudgetItem, BudgetVersion
from budget.services import (
    BudgetLockedError,
    assert_editable,
    lock_budget,
    snapshot_budget,
    unlock_budget,
)

from .factories import BudgetFactory, BudgetItemFactory, UserFactory


User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Lock de orçamentos
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBudgetLock:
    def test_lock_marks_flags_and_creates_version(self):
        budget = BudgetFactory()
        BudgetItemFactory(budget=budget, quantity=Decimal('2'),
                          margin_percent=Decimal('20'),
                          labor_cost_per_unit=Decimal('10'))
        user = UserFactory()

        version = lock_budget(budget, user, reason='approved')

        budget.refresh_from_db()
        assert budget.is_locked is True
        assert budget.locked_at is not None
        assert budget.locked_by_id == user.id
        assert isinstance(version, BudgetVersion)
        assert version.version_number == 1
        assert version.reason == 'approved'

    def test_lock_is_idempotent(self):
        budget = BudgetFactory()
        user = UserFactory()
        v1 = lock_budget(budget, user)
        v2 = lock_budget(budget, user)
        # Não cria nova versão se já está locked.
        assert v2.pk == v1.pk
        assert BudgetVersion.objects.filter(budget=budget).count() == 1

    def test_unlock_then_lock_creates_v2(self):
        budget = BudgetFactory()
        user = UserFactory()
        lock_budget(budget, user)
        unlock_budget(budget, user)
        budget.refresh_from_db()
        assert budget.is_locked is False
        v2 = lock_budget(budget, user, reason='approved')
        assert v2.version_number == 2
        assert BudgetVersion.objects.filter(budget=budget).count() == 2

    def test_assert_editable_raises_when_locked(self):
        budget = BudgetFactory()
        lock_budget(budget, UserFactory())
        budget.refresh_from_db()
        with pytest.raises(BudgetLockedError):
            assert_editable(budget)

    def test_snapshot_includes_items_and_totals(self):
        budget = BudgetFactory(discount_percent=Decimal('10'))
        item = BudgetItemFactory(
            budget=budget,
            quantity=Decimal('2'),
            unit_price_override=Decimal('100.00'),
            margin_percent=Decimal('0'),
            labor_cost_per_unit=Decimal('0'),
            vat_rate=Decimal('21'),
        )
        snap = snapshot_budget(budget)
        assert snap['budget']['number'] == budget.number
        assert len(snap['items']) == 1
        assert snap['items'][0]['service_id'] == item.service_id
        assert Decimal(snap['items'][0]['quantity']) == Decimal('2')
        # 2 * 100 = 200 HT por linha; orçamento desconta 10% → total_ht=180
        assert Decimal(snap['totals']['subtotal_ht']) == Decimal('200')
        assert Decimal(snap['totals']['total_ht']) == Decimal('180')

    def test_snapshot_persisted_in_version_is_immutable(self):
        budget = BudgetFactory()
        BudgetItemFactory(budget=budget, quantity=Decimal('1'),
                          unit_price_override=Decimal('50.00'),
                          margin_percent=Decimal('0'),
                          labor_cost_per_unit=Decimal('0'))
        v1 = lock_budget(budget, UserFactory())
        snapshot_at_lock = v1.snapshot
        # Reabre, edita, re-aprova: snapshot v1 NÃO muda.
        unlock_budget(budget, UserFactory())
        BudgetItemFactory(budget=budget, quantity=Decimal('5'),
                          unit_price_override=Decimal('80.00'),
                          margin_percent=Decimal('0'),
                          labor_cost_per_unit=Decimal('0'))
        v2 = lock_budget(budget, UserFactory())
        v1.refresh_from_db()
        assert v1.snapshot == snapshot_at_lock
        assert len(v2.snapshot['items']) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Views de approve/unlock e bloqueio de edição
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBudgetViewsLock:
    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.client = client
        self.user = UserFactory(is_superuser=True, is_staff=True)
        self.user.set_password('pw12345678')
        self.user.save()
        self.client.force_login(self.user)

    @override_settings(OTP_REQUIRED_FOR_STAFF=False)
    def test_approve_locks_and_redirects(self):
        budget = BudgetFactory()
        BudgetItemFactory(budget=budget, quantity=Decimal('1'),
                          unit_price_override=Decimal('50'),
                          margin_percent=Decimal('0'),
                          labor_cost_per_unit=Decimal('0'))
        url = reverse('budget:budget_approve', args=[budget.pk])
        resp = self.client.post(url)
        assert resp.status_code == 302
        budget.refresh_from_db()
        assert budget.status == Budget.Status.APPROVED
        assert budget.is_locked is True
        assert BudgetVersion.objects.filter(budget=budget).count() == 1

    @override_settings(OTP_REQUIRED_FOR_STAFF=False)
    def test_item_save_blocked_when_locked(self):
        budget = BudgetFactory()
        lock_budget(budget, self.user)
        budget.refresh_from_db()
        url = reverse('budget:item_save', args=[budget.pk])
        resp = self.client.post(url, data={
            'service': '1',
            'quantity': '1',
            'margin_percent': '0',
            'discount_percent': '0',
            'vat_rate': '21',
        })
        assert resp.status_code == 409
        assert resp.json().get('locked') is True

    @override_settings(OTP_REQUIRED_FOR_STAFF=False)
    def test_unlock_clears_flags(self):
        budget = BudgetFactory()
        lock_budget(budget, self.user)
        url = reverse('budget:budget_unlock', args=[budget.pk])
        resp = self.client.post(url)
        assert resp.status_code == 302
        budget.refresh_from_db()
        assert budget.is_locked is False
        assert budget.locked_at is None


# ─────────────────────────────────────────────────────────────────────────────
# OTP — middleware gate
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestOTPGate:
    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.client = client
        self.user = UserFactory(is_superuser=True, is_staff=True)
        self.user.set_password('pw12345678')
        self.user.save()

    @override_settings(OTP_REQUIRED_FOR_STAFF=True)
    def test_staff_without_totp_redirects_to_setup(self):
        self.client.force_login(self.user)
        # Tenta aceder a uma rota qualquer protegida (dashboard).
        resp = self.client.get('/pt-br/dashboard/', follow=False)
        assert resp.status_code == 302
        assert '/accounts/2fa/setup/' in resp['Location']

    @override_settings(OTP_REQUIRED_FOR_STAFF=True)
    def test_setup_url_itself_is_exempt(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('accounts:otp_setup'))
        # 200 (renderiza setup) — não pode redirecionar para si próprio.
        assert resp.status_code == 200

    @override_settings(OTP_REQUIRED_FOR_STAFF=True)
    def test_healthz_is_exempt(self):
        self.client.force_login(self.user)
        resp = self.client.get('/healthz/')
        assert resp.status_code == 200

    @override_settings(OTP_REQUIRED_FOR_STAFF=False)
    def test_dev_mode_no_op_for_staff(self):
        self.client.force_login(self.user)
        resp = self.client.get('/pt-br/dashboard/', follow=False)
        # Sem 2FA exigido → passa direto (dashboard renderiza).
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# OTP — decorador
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestOTPDecorator:
    def test_otp_required_redirects_unverified_staff(self, settings):
        settings.OTP_REQUIRED_FOR_STAFF = True
        from accounts.decorators import otp_required

        rf = RequestFactory()
        view = otp_required(lambda r: None)
        req = rf.get('/some/path/')
        req.user = UserFactory(is_staff=True)
        # Simula middleware: user.is_verified() existe e é False.
        req.user.is_verified = lambda: False

        resp = view(req)
        assert resp.status_code == 302
        # Sem device → setup; com device → verify.
        assert '/accounts/2fa/setup/' in resp['Location']

    def test_otp_required_passes_when_verified(self, settings):
        settings.OTP_REQUIRED_FOR_STAFF = True
        from accounts.decorators import otp_required

        rf = RequestFactory()
        view = otp_required(lambda r: 'ok')
        req = rf.get('/some/path/')
        req.user = UserFactory(is_staff=True)
        req.user.is_verified = lambda: True

        assert view(req) == 'ok'

    def test_otp_required_no_op_in_dev(self, settings):
        settings.OTP_REQUIRED_FOR_STAFF = False
        from accounts.decorators import otp_required

        rf = RequestFactory()
        view = otp_required(lambda r: 'ok')
        req = rf.get('/some/path/')
        req.user = UserFactory(is_staff=True)
        req.user.is_verified = lambda: False

        assert view(req) == 'ok'
