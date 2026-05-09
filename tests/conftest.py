"""
Fixtures comuns aos testes financeiros do Sprint 3.

A maior parte dos testes recorre a `pytest.mark.django_db` directamente; este
conftest expõe apenas factories que tendem a ser pedidas ao mesmo tempo.
"""
import pytest

from .factories import (
    BudgetFactory,
    BudgetItemFactory,
    BudgetItemMaterialFactory,
    ClientFactory,
    CollaboratorFactory,
    InvoiceFactory,
    InvoiceLineFactory,
    PayableFactory,
    PaymentFactory,
    ProjectFactory,
    ReceivableFactory,
    SubcontractorFactory,
    SupplierFactory,
    TimesheetFactory,
    UserFactory,
)


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def client_obj(db):
    return ClientFactory()


@pytest.fixture
def project(db, client_obj, user):
    return ProjectFactory(client=client_obj, created_by=user)


@pytest.fixture
def collaborator(db):
    return CollaboratorFactory()


@pytest.fixture
def supplier(db):
    return SupplierFactory()


@pytest.fixture
def invoice(db, client_obj, user):
    return InvoiceFactory(client=client_obj, created_by=user)


@pytest.fixture
def budget(db, client_obj):
    return BudgetFactory(client=client_obj)
