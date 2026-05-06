import datetime
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Payable(models.Model):
    """Conta a pagar — origina de ProjectSupplierInvoice ou entrada manual."""

    class Status(models.TextChoices):
        PENDING   = 'pending',   _('Pending')
        PARTIAL   = 'partial',   _('Partially paid')
        PAID      = 'paid',      _('Paid')
        CANCELLED = 'cancelled', _('Cancelled')

    # ── Origin (optional links to source records) ────────────────────────────
    supplier_invoice = models.OneToOneField(
        'projects.ProjectSupplierInvoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payable',
        verbose_name=_('Supplier invoice'),
    )
    subcontractor_invoice_ref = models.OneToOneField(
        'contracts.SubcontractorInvoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payable_entry',
        verbose_name=_('Subcontractor invoice'),
    )

    # ── Manual entry fields ───────────────────────────────────────────────────
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='payables',
        verbose_name=_('Supplier'),
    )
    subcontractor = models.ForeignKey(
        'subcontractors.Subcontractor',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='payables',
        verbose_name=_('Subcontractor'),
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payables',
        verbose_name=_('Project'),
    )
    description  = models.CharField(_('Description'), max_length=255, blank=True, default='')
    reference    = models.CharField(_('Reference'), max_length=100, blank=True, default='')
    amount       = models.DecimalField(_('Amount (€)'), max_digits=14, decimal_places=4)
    issue_date   = models.DateField(_('Issue date'))
    due_date     = models.DateField(_('Due date'), null=True, blank=True)
    status       = models.CharField(
        _('Status'), max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    notes = models.TextField(_('Notes'), blank=True, default='')

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payables_created',
        verbose_name=_('Created by'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Payable')
        verbose_name_plural = _('Payables')
        ordering            = ['due_date', '-amount']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['supplier']),
        ]

    def __str__(self):
        return f'{self.reference or self.description} — €{self.amount}'

    @property
    def amount_paid(self):
        return self.payments.aggregate(
            total=models.Sum('amount'),
        )['total'] or Decimal('0')

    @property
    def amount_remaining(self):
        return self.amount - self.amount_paid

    @property
    def is_overdue(self):
        if self.due_date and self.status not in (self.Status.PAID, self.Status.CANCELLED):
            return self.due_date < datetime.date.today()
        return False

    def sync_status(self):
        """Recalculate and save status based on payments."""
        paid = self.amount_paid
        if paid <= 0:
            new = self.Status.PENDING
        elif paid >= self.amount:
            new = self.Status.PAID
        else:
            new = self.Status.PARTIAL
        if new != self.status:
            self.status = new
            self.save(update_fields=['status', 'updated_at'])


class Receivable(models.Model):
    """Conta a receber — originada de Invoice emitida ao cliente."""

    class Status(models.TextChoices):
        PENDING   = 'pending',   _('Pending')
        PARTIAL   = 'partial',   _('Partially paid')
        PAID      = 'paid',      _('Paid')
        CANCELLED = 'cancelled', _('Cancelled')

    # ── Origin — one of invoice OR statement must be set ─────────────────────
    invoice = models.OneToOneField(
        'invoicing.Invoice',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='receivable',
        verbose_name=_('Invoice'),
    )
    statement = models.OneToOneField(
        'contracts.Statement',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='receivable',
        verbose_name=_('Statement (EA)'),
        limit_choices_to={'statement_type': 'client'},
    )

    # ── Denormalized for fast queries ─────────────────────────────────────────
    client   = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,
        related_name='receivables',
        verbose_name=_('Client'),
    )
    project  = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='receivables',
        verbose_name=_('Project'),
    )
    amount     = models.DecimalField(_('Amount (€)'), max_digits=14, decimal_places=4)
    issue_date = models.DateField(_('Issue date'))
    due_date   = models.DateField(_('Due date'), null=True, blank=True)
    status     = models.CharField(
        _('Status'), max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    notes = models.TextField(_('Notes'), blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Receivable')
        verbose_name_plural = _('Receivables')
        ordering            = ['due_date', '-amount']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['client']),
        ]

    def __str__(self):
        ref = self.invoice.number if self.invoice_id else f'EA {self.statement.number}'
        return f'{ref} — {self.client.name} — €{self.amount}'

    @property
    def amount_paid(self):
        return self.payments.aggregate(
            total=models.Sum('amount'),
        )['total'] or Decimal('0')

    @property
    def amount_remaining(self):
        return self.amount - self.amount_paid

    @property
    def is_overdue(self):
        if self.due_date and self.status not in (self.Status.PAID, self.Status.CANCELLED):
            return self.due_date < datetime.date.today()
        return False

    def sync_status(self):
        """Recalculate and save status based on payments; also updates Invoice if linked."""
        paid = self.amount_paid
        if paid <= 0:
            new_r = self.Status.PENDING
            new_i = 'sent'
        elif paid >= self.amount:
            new_r = self.Status.PAID
            new_i = 'paid'
        else:
            new_r = self.Status.PARTIAL
            new_i = 'partial'

        if new_r != self.status:
            self.status = new_r
            self.save(update_fields=['status', 'updated_at'])

        if self.invoice_id:
            inv = self.invoice
            if inv.status not in ('draft', 'cancelled') and inv.status != new_i:
                inv.status = new_i
                inv.save(update_fields=['status', 'updated_at'])


class Payment(models.Model):
    """Registo de pagamento — associado a Payable OU Receivable (nunca ambos)."""

    class Method(models.TextChoices):
        TRANSFER = 'transfer', _('Bank transfer')
        CHEQUE   = 'cheque',   _('Cheque')
        CASH     = 'cash',     _('Cash')
        CARD     = 'card',     _('Card')
        OTHER    = 'other',    _('Other')

    payable = models.ForeignKey(
        Payable,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='payments',
        verbose_name=_('Payable'),
    )
    receivable = models.ForeignKey(
        Receivable,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='payments',
        verbose_name=_('Receivable'),
    )

    date      = models.DateField(_('Payment date'))
    amount    = models.DecimalField(_('Amount (€)'), max_digits=14, decimal_places=4)
    method    = models.CharField(
        _('Method'), max_length=20, choices=Method.choices, default=Method.TRANSFER,
    )
    reference = models.CharField(_('Reference / transaction ID'), max_length=100, blank=True, default='')
    notes     = models.TextField(_('Notes'), blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments_created',
        verbose_name=_('Created by'),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _('Payment')
        verbose_name_plural = _('Payments')
        ordering            = ['-date']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(payable__isnull=False, receivable__isnull=True) |
                    models.Q(payable__isnull=True,  receivable__isnull=False)
                ),
                name='payment_has_exactly_one_parent',
            )
        ]

    def __str__(self):
        parent = self.payable or self.receivable
        return f'€{self.amount} — {self.date} [{parent}]'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.payable_id:
            self.payable.sync_status()
        if self.receivable_id:
            self.receivable.sync_status()

    def delete(self, *args, **kwargs):
        payable_id    = self.payable_id
        receivable_id = self.receivable_id
        super().delete(*args, **kwargs)
        if payable_id:
            try:
                Payable.objects.get(pk=payable_id).sync_status()
            except Payable.DoesNotExist:
                pass
        if receivable_id:
            try:
                Receivable.objects.get(pk=receivable_id).sync_status()
            except Receivable.DoesNotExist:
                pass
