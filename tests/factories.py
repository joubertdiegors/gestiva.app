"""
Factories partilhadas para testes financeiros (Sprint 3).

Mantém-se mínimo: cada factory cria só o que o seu modelo exige, e nada mais.
Os testes financeiros usam Decimal explícito sempre que possível para evitar
arredondamento de float a viajar até cálculos sensíveis.
"""
import datetime
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from budget.models import Budget, BudgetItem, BudgetItemMaterial
from catalog.models import Product, UnitOfMeasure
from clients.models import Client
from finance.models import Payable, Payment, Receivable
from invoicing.models import Invoice, InvoiceLine
from projects.models import Project
from services.models import Service
from subcontractors.models import Subcontractor
from suppliers.models import Supplier
from timesheets.models import Timesheet
from workforce.models import Collaborator, CollaboratorHourlyRate


User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'tester{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')
    is_staff = True
    is_active = True


class ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Client

    name = factory.Sequence(lambda n: f'Cliente {n}')
    category = 'professional'
    # None por defeito: a validação BE só corre via full_clean() e a maior
    # parte dos testes não passa por aí. Testes específicos de VAT atribuem
    # um número válido (BE0403170701, p.ex.).
    vat_number = None
    vat_rate = Decimal('21.00')


class SubcontractorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subcontractor

    name = factory.Sequence(lambda n: f'Sub {n}')
    category = 'professional'
    vat_number = ''


class SupplierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Supplier

    name = factory.Sequence(lambda n: f'Fornecedor {n}')


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: f'Obra {n}')
    client = factory.SubFactory(ClientFactory)
    created_by = factory.SubFactory(UserFactory)
    status = Project.Status.ACTIVE


class CollaboratorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Collaborator

    company = factory.SubFactory(SubcontractorFactory)
    name = factory.Sequence(lambda n: f'Colaborador {n}')
    status = 'active'


class CollaboratorHourlyRateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CollaboratorHourlyRate

    collaborator = factory.SubFactory(CollaboratorFactory)
    hourly_rate = Decimal('25.00')
    start_date = datetime.date(2026, 1, 1)


class TimesheetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Timesheet

    worker = factory.SubFactory(CollaboratorFactory)
    project = factory.SubFactory(ProjectFactory)
    date = datetime.date(2026, 5, 1)
    hours = Decimal('8.00')
    hourly_rate_snapshot = Decimal('25.00')


class UnitOfMeasureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UnitOfMeasure
        django_get_or_create = ('symbol',)

    symbol = 'ea'
    name = 'Unidade'


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f'Produto {n}')
    unit = factory.SubFactory(UnitOfMeasureFactory)
    is_active = True
    is_approved = True


class ServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Service

    code = factory.Sequence(lambda n: f'SVC-{n:04d}')
    name = factory.Sequence(lambda n: f'Serviço {n}')
    unit = factory.SubFactory(UnitOfMeasureFactory)
    labor_cost_per_unit = Decimal('20.0000')
    default_margin_percent = Decimal('30.00')


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    number = factory.Sequence(lambda n: f'FAT-2026-{n:04d}')
    client = factory.SubFactory(ClientFactory)
    issue_date = datetime.date(2026, 5, 1)
    due_date = datetime.date(2026, 6, 1)
    discount_percent = Decimal('0')
    vat_rate = Decimal('21.00')
    created_by = factory.SubFactory(UserFactory)


class InvoiceLineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InvoiceLine

    invoice = factory.SubFactory(InvoiceFactory)
    description = factory.Sequence(lambda n: f'Linha {n}')
    quantity = Decimal('1.0000')
    unit_price = Decimal('100.0000')
    discount_percent = Decimal('0')
    vat_rate = Decimal('21.00')


class BudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Budget

    number = factory.Sequence(lambda n: f'ORC-2026-{n:04d}')
    title = factory.Sequence(lambda n: f'Orçamento {n}')
    client = factory.SubFactory(ClientFactory)
    status = Budget.Status.DRAFT
    issue_date = datetime.date(2026, 5, 1)
    discount_percent = Decimal('0')
    vat_rate = Decimal('21.00')


class BudgetItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BudgetItem

    budget = factory.SubFactory(BudgetFactory)
    service = factory.SubFactory(ServiceFactory)
    service_name_snapshot = factory.LazyAttribute(lambda o: o.service.name)
    service_code_snapshot = factory.LazyAttribute(lambda o: o.service.code)
    service_unit_snapshot = factory.LazyAttribute(lambda o: o.service.unit.symbol)
    quantity = Decimal('1.0000')
    labor_cost_per_unit = Decimal('20.0000')
    margin_percent = Decimal('30.00')
    discount_percent = Decimal('0')
    vat_rate = Decimal('21.00')


class BudgetItemMaterialFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BudgetItemMaterial

    budget_item = factory.SubFactory(BudgetItemFactory)
    product = factory.SubFactory(ProductFactory)
    product_name_snapshot = factory.LazyAttribute(lambda o: o.product.name)
    unit_snapshot = factory.LazyAttribute(lambda o: o.product.unit.symbol)
    quantity = Decimal('1.0000')
    unit_price_snapshot = Decimal('10.0000')


class ReceivableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Receivable

    invoice = factory.SubFactory(InvoiceFactory)
    client = factory.LazyAttribute(lambda o: o.invoice.client)
    amount = Decimal('121.0000')
    issue_date = datetime.date(2026, 5, 1)
    due_date = datetime.date(2026, 6, 1)


class PayableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payable

    supplier = factory.SubFactory(SupplierFactory)
    description = 'Conta a pagar de teste'
    amount = Decimal('100.0000')
    issue_date = datetime.date(2026, 5, 1)
    due_date = datetime.date(2026, 6, 1)
    created_by = factory.SubFactory(UserFactory)


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    date = datetime.date(2026, 5, 15)
    amount = Decimal('50.0000')
    method = Payment.Method.TRANSFER
    created_by = factory.SubFactory(UserFactory)
