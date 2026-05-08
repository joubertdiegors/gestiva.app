import datetime
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


class Invoice(models.Model):

    class Status(models.TextChoices):
        DRAFT     = 'draft',     _('Draft')
        SENT      = 'sent',      _('Sent')
        PARTIAL   = 'partial',   _('Partially paid')
        PAID      = 'paid',      _('Paid')
        CANCELLED = 'cancelled', _('Cancelled')

    class InvoiceType(models.TextChoices):
        DIRECT      = 'direct',      _('Direct invoice')
        ADVANCE     = 'advance',     _('Advance invoice')
        FROM_BUDGET = 'from_budget', _('From budget')
        CREDIT_NOTE = 'credit_note', _('Credit note')

    # ── Identification ────────────────────────────────────────────────────────
    external_id = models.UUIDField(
        _('External ID'), default=uuid.uuid4, editable=False, unique=True,
    )
    number = models.CharField(_('Number'), max_length=40, unique=True)
    title  = models.CharField(_('Title'), max_length=255, blank=True, default='')

    # ── Relations ─────────────────────────────────────────────────────────────
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name=_('Client'),
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoices',
        verbose_name=_('Project'),
    )
    budget = models.ForeignKey(
        'budget.Budget',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoices',
        verbose_name=_('Budget origin'),
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    issue_date = models.DateField(_('Issue date'))
    due_date   = models.DateField(_('Due date'), null=True, blank=True)

    # ── Financial ─────────────────────────────────────────────────────────────
    discount_percent = models.DecimalField(
        _('Global discount (%)'), max_digits=6, decimal_places=2, default=Decimal('0'),
    )
    vat_rate = models.DecimalField(
        _('Default VAT (%)'), max_digits=6, decimal_places=2, default=Decimal('21.00'),
    )

    # ── Billing address snapshot ──────────────────────────────────────────────
    billing_name    = models.CharField(_('Billing name'), max_length=255, blank=True, default='')
    billing_address = models.TextField(_('Billing address'), blank=True, default='')
    billing_vat     = models.CharField(_('Billing VAT number'), max_length=50, blank=True, default='')

    # ── Type ─────────────────────────────────────────────────────────────────
    invoice_type = models.CharField(
        _('Invoice type'), max_length=20, choices=InvoiceType.choices, default=InvoiceType.DIRECT,
    )

    # ── Authorization / work fields ───────────────────────────────────────────
    bon_de_facturation   = models.CharField(_('Authorization number'), max_length=100, blank=True, default='')
    authorization_date   = models.DateField(_('Authorization date'), null=True, blank=True)
    authorization_contact = models.CharField(_('Authorization contact'), max_length=255, blank=True, default='')
    work_start_date      = models.DateField(_('Work start date'), null=True, blank=True)
    work_end_date        = models.DateField(_('Work end date'), null=True, blank=True)
    execution_notes      = models.TextField(_('Execution notes'), blank=True, default='')

    # ── Status & notes ────────────────────────────────────────────────────────
    status = models.CharField(
        _('Status'), max_length=20, choices=Status.choices, default=Status.DRAFT,
    )
    notes_internal = models.TextField(_('Internal notes'), blank=True, default='')
    notes_client   = models.TextField(_('Notes for client'), blank=True, default='')
    payment_terms  = models.TextField(_('Payment terms'), blank=True, default='')

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='invoices_created',
        verbose_name=_('Created by'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at    = models.DateTimeField(_('Sent at'), null=True, blank=True)

    class Meta:
        verbose_name        = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering            = ['-issue_date', '-number']
        indexes = [
            models.Index(fields=['status', '-issue_date']),
            models.Index(fields=['client']),
        ]

    def __str__(self):
        return f'{self.number} — {self.client.name}'

    @property
    def subtotal_ht(self):
        return sum((ln.total_ht for ln in self.lines.all()), Decimal('0'))

    @property
    def discount_amount(self):
        return (self.subtotal_ht * self.discount_percent / Decimal('100')).quantize(Decimal('0.0001'))

    @property
    def total_ht(self):
        return self.subtotal_ht - self.discount_amount

    @property
    def total_vat(self):
        return sum((ln.vat_amount for ln in self.lines.all()), Decimal('0'))

    @property
    def total_ttc(self):
        return self.total_ht + self.total_vat

    @property
    def amount_paid(self):
        from finance.models import Payment
        paid = Payment.objects.filter(
            receivable__invoice=self,
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        return paid

    @property
    def amount_due(self):
        return self.total_ttc - self.amount_paid

    @property
    def is_overdue(self):
        if self.due_date and self.status not in (self.Status.PAID, self.Status.CANCELLED):
            return self.due_date < datetime.date.today()
        return False

    @classmethod
    def next_number(cls):
        """
        Reserva o próximo número de fatura.

        DEVE ser chamado dentro de uma transação aberta pelo caller, e o
        objeto retornado deve ser persistido nessa mesma transação. O
        bloqueio de tabela (select_for_update) evita que dois processos
        leiam o mesmo "último número" e gerem o mesmo `number` (seria UNIQUE
        constraint violation em produção).
        """
        year = datetime.date.today().year
        prefix = f'FAT-{year}-'
        with transaction.atomic():
            last = (
                cls.objects.select_for_update()
                .filter(number__startswith=prefix)
                .order_by('-number')
                .values_list('number', flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            return f'{prefix}{seq:04d}'


class InvoiceLine(models.Model):

    class LineType(models.TextChoices):
        LINE      = 'line',      _('Line')
        TITLE     = 'title',     _('Title (H1)')
        H2        = 'h2',        _('Subtitle H2')
        H3        = 'h3',        _('Subtitle H3')
        H4        = 'h4',        _('Subtitle H4+')
        COMMENT   = 'comment',   _('Comment')
        PAGE_BREAK = 'page_break', _('Page break')

    invoice     = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='lines', verbose_name=_('Invoice'),
    )
    order       = models.PositiveIntegerField(_('Order'), default=0)
    line_type   = models.CharField(
        _('Line type'), max_length=20, choices=LineType.choices, default=LineType.LINE,
    )
    description = models.CharField(_('Description'), max_length=255, blank=True, default='')
    detail      = models.TextField(_('Detail'), blank=True, default='')
    quantity    = models.DecimalField(_('Quantity'), max_digits=12, decimal_places=4, default=Decimal('1'))
    unit        = models.CharField(_('Unit'), max_length=30, blank=True, default='')
    unit_price  = models.DecimalField(_('Unit price (€)'), max_digits=14, decimal_places=4, default=Decimal('0'))
    discount_percent = models.DecimalField(
        _('Discount (%)'), max_digits=6, decimal_places=2, default=Decimal('0'),
    )
    vat_rate = models.DecimalField(
        _('VAT (%)'), max_digits=6, decimal_places=2, default=Decimal('21.00'),
    )
    budget_item = models.ForeignKey(
        'budget.BudgetItem',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoice_lines',
        verbose_name=_('Budget item origin'),
    )

    class Meta:
        verbose_name        = _('Invoice line')
        verbose_name_plural = _('Invoice lines')
        ordering            = ['invoice', 'order']

    def __str__(self):
        return f'{self.invoice.number} › {self.description}'

    @property
    def is_section(self):
        return self.line_type in (self.LineType.TITLE, self.LineType.H2, self.LineType.H3, self.LineType.H4)

    @property
    def is_numeric(self):
        return self.line_type == self.LineType.LINE

    @property
    def total_ht_before_discount(self):
        return self.quantity * self.unit_price

    @property
    def line_discount(self):
        return (self.total_ht_before_discount * self.discount_percent / Decimal('100')).quantize(Decimal('0.0001'))

    @property
    def total_ht(self):
        return self.total_ht_before_discount - self.line_discount

    @property
    def vat_amount(self):
        return (self.total_ht * self.vat_rate / Decimal('100')).quantize(Decimal('0.0001'))

    @property
    def total_ttc(self):
        return self.total_ht + self.vat_amount
