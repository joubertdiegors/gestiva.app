from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


# ── Line types (shared with InvoiceLine structure) ────────────────────────────

LINE_TYPE_CHOICES = [
    ('line',       _('Line')),
    ('title',      _('Title (H1)')),
    ('h2',         _('Subtitle (H2)')),
    ('h3',         _('Heading H3')),
    ('h4',         _('Heading H4')),
    ('comment',    _('Comment')),
    ('page_break', _('Page break')),
]


# ── Contract ──────────────────────────────────────────────────────────────────

class Contract(models.Model):

    TYPE_CLIENT        = 'client'
    TYPE_SUBCONTRACTOR = 'subcontractor'
    TYPE_SUPPLIER      = 'supplier'
    TYPE_OTHER         = 'other'
    TYPE_CHOICES = [
        (TYPE_CLIENT,        _('Client contract')),
        (TYPE_SUBCONTRACTOR, _('Subcontractor contract')),
        (TYPE_SUPPLIER,      _('Supplier contract')),
        (TYPE_OTHER,         _('Other')),
    ]

    STATUS_DRAFT      = 'draft'
    STATUS_ACTIVE     = 'active'
    STATUS_TERMINATED = 'terminated'
    STATUS_CHOICES = [
        (STATUS_DRAFT,      _('Draft')),
        (STATUS_ACTIVE,     _('Active')),
        (STATUS_TERMINATED, _('Terminated')),
    ]

    contract_type = models.CharField(
        _('Type'), max_length=20, choices=TYPE_CHOICES, default=TYPE_CLIENT,
    )

    # ── Counterparts (only one should be set depending on type) ──────────────
    client = models.ForeignKey(
        'clients.Client',
        verbose_name=_('Client'),
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='contracts',
    )
    subcontractor = models.ForeignKey(
        'subcontractors.Subcontractor',
        verbose_name=_('Subcontractor'),
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='contracts',
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        verbose_name=_('Supplier'),
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='contracts',
    )

    project = models.ForeignKey(
        'projects.Project',
        verbose_name=_('Project'),
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='contracts',
    )

    reference   = models.CharField(_('Reference / number'), max_length=100, blank=True, default='')
    title       = models.CharField(_('Title'), max_length=255)
    signed_date = models.DateField(_('Signed date'), null=True, blank=True)
    start_date  = models.DateField(_('Start date'), null=True, blank=True)
    end_date    = models.DateField(_('End date'), null=True, blank=True)

    status = models.CharField(
        _('Status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
    )

    # Discount / VAT at document level (applied to all numeric lines)
    discount_percent = models.DecimalField(
        _('Discount (%)'), max_digits=6, decimal_places=2, default=Decimal('0'),
    )
    vat_rate = models.DecimalField(
        _('VAT rate (%)'), max_digits=6, decimal_places=2, default=Decimal('21.00'),
    )

    notes_internal = models.TextField(_('Internal notes'), blank=True, default='')
    notes_client   = models.TextField(_('Notes to counterpart'), blank=True, default='')

    # ── Prepared for future DocumentTemplate app ─────────────────────────────
    template_ref = models.ForeignKey(
        'document_templates.DocumentTemplate',
        verbose_name=_('Document template'),
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contracts',
    ) if False else models.CharField(  # swapped once app exists
        _('Template ref (future)'), max_length=100, blank=True, default='',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Created by'),
        on_delete=models.PROTECT,
        related_name='contracts_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Updated by'),
        on_delete=models.PROTECT,
        related_name='contracts_updated',
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Contract')
        verbose_name_plural = _('Contracts')
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['contract_type', 'status']),
        ]

    def __str__(self):
        counterpart = self.client or self.subcontractor or self.supplier or '—'
        return f'{self.title} — {counterpart}'

    @property
    def counterpart(self):
        return self.client or self.subcontractor or self.supplier

    @property
    def total_ht(self):
        return sum(
            ln.total_ht for ln in self.lines.all() if ln.line_type == 'line'
        )

    @property
    def status_colour(self):
        return {
            self.STATUS_DRAFT:      'grey',
            self.STATUS_ACTIVE:     'green',
            self.STATUS_TERMINATED: 'red',
        }.get(self.status, 'grey')


class ContractLine(models.Model):
    """Structured line in a contract — mirrors InvoiceLine structure."""

    contract   = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='lines')
    order      = models.PositiveIntegerField(_('Order'), default=0)
    line_type  = models.CharField(_('Type'), max_length=20, choices=LINE_TYPE_CHOICES, default='line')
    description = models.CharField(_('Description'), max_length=255, blank=True, default='')
    detail      = models.TextField(_('Detail'), blank=True, default='')

    # Numeric fields — only relevant when line_type == 'line'
    quantity         = models.DecimalField(_('Quantity'), max_digits=12, decimal_places=4, default=Decimal('1'))
    unit             = models.CharField(_('Unit'), max_length=30, blank=True, default='')
    unit_price       = models.DecimalField(_('Unit price (€)'), max_digits=14, decimal_places=4, default=Decimal('0'))
    discount_percent = models.DecimalField(_('Discount (%)'), max_digits=6, decimal_places=2, default=Decimal('0'))
    vat_rate         = models.DecimalField(_('VAT rate (%)'), max_digits=6, decimal_places=2, default=Decimal('21.00'))

    class Meta:
        verbose_name        = _('Contract Line')
        verbose_name_plural = _('Contract Lines')
        ordering            = ['order', 'id']

    def __str__(self):
        return f'[{self.line_type}] {self.description}'

    @property
    def is_numeric(self):
        return self.line_type == 'line'

    @property
    def is_section(self):
        return self.line_type in ('title', 'h2', 'h3', 'h4')

    @property
    def total_ht_before_discount(self):
        return self.quantity * self.unit_price

    @property
    def line_discount(self):
        return self.total_ht_before_discount * self.discount_percent / 100

    @property
    def total_ht(self):
        return self.total_ht_before_discount - self.line_discount

    @property
    def vat_amount(self):
        return self.total_ht * self.vat_rate / 100

    @property
    def total_ttc(self):
        return self.total_ht + self.vat_amount


# ── Addendum ──────────────────────────────────────────────────────────────────

class Addendum(models.Model):
    """Addendum sent to a subcontractor, based on a client contract."""

    STATUS_DRAFT  = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_DRAFT,  _('Draft')),
        (STATUS_ACTIVE, _('Active')),
        (STATUS_CLOSED, _('Closed')),
    ]

    # The client contract this addendum is based on
    contract = models.ForeignKey(
        Contract,
        verbose_name=_('Client contract'),
        on_delete=models.PROTECT,
        related_name='addenda',
        limit_choices_to={'contract_type': 'client'},
    )
    subcontractor = models.ForeignKey(
        'subcontractors.Subcontractor',
        verbose_name=_('Subcontractor'),
        on_delete=models.PROTECT,
        related_name='addenda',
    )
    project = models.ForeignKey(
        'projects.Project',
        verbose_name=_('Project'),
        on_delete=models.PROTECT,
        related_name='addenda',
    )

    number      = models.CharField(_('Addendum number'), max_length=50)
    title       = models.CharField(_('Title'), max_length=255)
    signed_date = models.DateField(_('Signed date'), null=True, blank=True)
    start_date  = models.DateField(_('Start date'), null=True, blank=True)
    end_date    = models.DateField(_('End date'), null=True, blank=True)
    status      = models.CharField(
        _('Status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
    )

    discount_percent = models.DecimalField(
        _('Discount (%)'), max_digits=6, decimal_places=2, default=Decimal('0'),
    )
    vat_rate = models.DecimalField(
        _('VAT rate (%)'), max_digits=6, decimal_places=2, default=Decimal('21.00'),
    )

    notes_internal = models.TextField(_('Internal notes'), blank=True, default='')
    notes_sub      = models.TextField(_('Notes to subcontractor'), blank=True, default='')

    template_ref = models.CharField(_('Template ref (future)'), max_length=100, blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Created by'),
        on_delete=models.PROTECT,
        related_name='addenda_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Updated by'),
        on_delete=models.PROTECT,
        related_name='addenda_updated',
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Addendum')
        verbose_name_plural = _('Addenda')
        ordering            = ['contract', 'number']
        unique_together     = [('contract', 'number')]

    def __str__(self):
        return f'Adendo {self.number} — {self.subcontractor.name} — {self.title}'

    @property
    def total_ht(self):
        return sum(ln.total_ht for ln in self.lines.all() if ln.line_type == 'line')

    @property
    def status_colour(self):
        return {
            self.STATUS_DRAFT:  'grey',
            self.STATUS_ACTIVE: 'blue',
            self.STATUS_CLOSED: 'green',
        }.get(self.status, 'grey')


class AddendumLine(models.Model):
    """Structured line in an addendum — same structure as ContractLine."""

    addendum   = models.ForeignKey(Addendum, on_delete=models.CASCADE, related_name='lines')
    order      = models.PositiveIntegerField(_('Order'), default=0)
    line_type  = models.CharField(_('Type'), max_length=20, choices=LINE_TYPE_CHOICES, default='line')
    description = models.CharField(_('Description'), max_length=255, blank=True, default='')
    detail      = models.TextField(_('Detail'), blank=True, default='')

    quantity         = models.DecimalField(_('Quantity'), max_digits=12, decimal_places=4, default=Decimal('1'))
    unit             = models.CharField(_('Unit'), max_length=30, blank=True, default='')
    unit_price       = models.DecimalField(_('Unit price (€)'), max_digits=14, decimal_places=4, default=Decimal('0'))
    discount_percent = models.DecimalField(_('Discount (%)'), max_digits=6, decimal_places=2, default=Decimal('0'))
    vat_rate         = models.DecimalField(_('VAT rate (%)'), max_digits=6, decimal_places=2, default=Decimal('21.00'))

    # Tracks which contract line this was copied from (informational)
    source_contract_line = models.ForeignKey(
        ContractLine,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='addendum_copies',
        verbose_name=_('Source contract line'),
    )

    class Meta:
        verbose_name        = _('Addendum Line')
        verbose_name_plural = _('Addendum Lines')
        ordering            = ['order', 'id']

    def __str__(self):
        return f'[{self.line_type}] {self.description}'

    @property
    def is_numeric(self):
        return self.line_type == 'line'

    @property
    def is_section(self):
        return self.line_type in ('title', 'h2', 'h3', 'h4')

    @property
    def total_ht_before_discount(self):
        return self.quantity * self.unit_price

    @property
    def line_discount(self):
        return self.total_ht_before_discount * self.discount_percent / 100

    @property
    def total_ht(self):
        return self.total_ht_before_discount - self.line_discount

    @property
    def vat_amount(self):
        return self.total_ht * self.vat_rate / 100

    @property
    def total_ttc(self):
        return self.total_ht + self.vat_amount


# ── Statement (EA — Estado de Avanço) ─────────────────────────────────────────

class Statement(models.Model):
    """
    EA — Estado de Avanço.
    TYPE_CLIENT:        sent to client requesting payment, based on a Contract.
    TYPE_SUBCONTRACTOR: sent to subcontractor authorising invoicing, based on an Addendum.
    """

    TYPE_CLIENT        = 'client'
    TYPE_SUBCONTRACTOR = 'subcontractor'
    TYPE_CHOICES = [
        (TYPE_CLIENT,        _('EA to Client')),
        (TYPE_SUBCONTRACTOR, _('EA to Subcontractor')),
    ]

    STATUS_DRAFT    = 'draft'
    STATUS_SENT     = 'sent'
    STATUS_APPROVED = 'approved'
    STATUS_CHOICES = [
        (STATUS_DRAFT,    _('Draft')),
        (STATUS_SENT,     _('Sent')),
        (STATUS_APPROVED, _('Approved')),
    ]

    statement_type = models.CharField(
        _('Type'), max_length=20, choices=TYPE_CHOICES,
    )
    number = models.CharField(_('EA number'), max_length=20)

    # Only one of these will be set depending on type
    contract = models.ForeignKey(
        Contract,
        verbose_name=_('Contract'),
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='statements',
        limit_choices_to={'contract_type': 'client'},
    )
    addendum = models.ForeignKey(
        Addendum,
        verbose_name=_('Addendum'),
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='statements',
    )

    period_start = models.DateField(_('Period start'), null=True, blank=True)
    period_end   = models.DateField(_('Period end'), null=True, blank=True)
    issue_date   = models.DateField(_('Issue date'))
    due_date     = models.DateField(_('Due date'), null=True, blank=True)

    status = models.CharField(
        _('Status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
    )

    notes_internal = models.TextField(_('Internal notes'), blank=True, default='')
    notes_external = models.TextField(_('Notes to recipient'), blank=True, default='')

    template_ref = models.CharField(_('Template ref (future)'), max_length=100, blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Created by'),
        on_delete=models.PROTECT,
        related_name='statements_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Updated by'),
        on_delete=models.PROTECT,
        related_name='statements_updated',
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Statement')
        verbose_name_plural = _('Statements')
        ordering            = ['-issue_date']

    def __str__(self):
        return f'EA {self.number} — {self.get_statement_type_display()}'

    @property
    def total(self):
        return sum(ln.amount for ln in self.lines.all())

    @property
    def project(self):
        if self.contract:
            return self.contract.project
        if self.addendum:
            return self.addendum.project
        return None

    @property
    def counterpart_name(self):
        if self.statement_type == self.TYPE_CLIENT and self.contract:
            return str(self.contract.client or '—')
        if self.statement_type == self.TYPE_SUBCONTRACTOR and self.addendum:
            return str(self.addendum.subcontractor)
        return '—'

    @property
    def status_colour(self):
        return {
            self.STATUS_DRAFT:    'grey',
            self.STATUS_SENT:     'blue',
            self.STATUS_APPROVED: 'green',
        }.get(self.status, 'grey')


class StatementLine(models.Model):
    """Free-text line in an EA — description + amount."""

    statement   = models.ForeignKey(Statement, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(_('Description'), max_length=255)
    amount      = models.DecimalField(_('Amount (€)'), max_digits=14, decimal_places=2, default=Decimal('0'))
    notes       = models.TextField(_('Notes'), blank=True, default='')
    order       = models.PositiveSmallIntegerField(_('Order'), default=0)

    class Meta:
        verbose_name        = _('Statement Line')
        verbose_name_plural = _('Statement Lines')
        ordering            = ['order', 'id']

    def __str__(self):
        return f'{self.statement} — {self.description}'


# ── Subcontractor Invoice ─────────────────────────────────────────────────────

class SubcontractorInvoice(models.Model):
    """Invoice received from a subcontractor — creates a Payable in finance."""

    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_PAID     = 'paid'
    STATUS_CHOICES = [
        (STATUS_PENDING,  _('Pending')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_PAID,     _('Paid')),
    ]

    addendum = models.ForeignKey(
        Addendum,
        verbose_name=_('Addendum'),
        on_delete=models.PROTECT,
        related_name='subcontractor_invoices',
    )
    statement = models.ForeignKey(
        Statement,
        verbose_name=_('EA (statement)'),
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subcontractor_invoices',
        limit_choices_to={'statement_type': 'subcontractor'},
    )

    invoice_number = models.CharField(_('Invoice number'), max_length=100)
    invoice_date   = models.DateField(_('Invoice date'))
    due_date       = models.DateField(_('Due date'), null=True, blank=True)
    amount         = models.DecimalField(_('Amount (€)'), max_digits=14, decimal_places=2)

    status = models.CharField(
        _('Status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING,
    )
    notes = models.TextField(_('Notes'), blank=True, default='')

    # Link to the Payable created automatically
    payable = models.OneToOneField(
        'finance.Payable',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subcontractor_invoice',
        verbose_name=_('Payable'),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Created by'),
        on_delete=models.PROTECT,
        related_name='subcontractor_invoices_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Subcontractor Invoice')
        verbose_name_plural = _('Subcontractor Invoices')
        ordering            = ['-invoice_date']

    def __str__(self):
        return f'{self.invoice_number} — {self.addendum.subcontractor.name}'

    def create_payable(self):
        """Create or update a Payable entry in finance."""
        from finance.models import Payable
        desc = f'Fatura {self.invoice_number} — {self.addendum.subcontractor.name}'
        if self.payable:
            self.payable.amount     = self.amount
            self.payable.issue_date = self.invoice_date
            self.payable.due_date   = self.due_date
            self.payable.description = desc
            self.payable.save(update_fields=['amount', 'issue_date', 'due_date', 'description', 'updated_at'])
        else:
            payable = Payable.objects.create(
                description = desc,
                reference   = self.invoice_number,
                amount      = self.amount,
                issue_date  = self.invoice_date,
                due_date    = self.due_date,
                project     = self.addendum.project,
                subcontractor_invoice_ref = self,
                created_by  = self.created_by,
            )
            self.payable = payable
            self.save(update_fields=['payable'])


# ── Supplier Contract ─────────────────────────────────────────────────────────

class SupplierContract(models.Model):
    """Price agreement with a supplier — product lines with agreed prices and validity."""

    STATUS_ACTIVE     = 'active'
    STATUS_EXPIRED    = 'expired'
    STATUS_TERMINATED = 'terminated'
    STATUS_CHOICES = [
        (STATUS_ACTIVE,     _('Active')),
        (STATUS_EXPIRED,    _('Expired')),
        (STATUS_TERMINATED, _('Terminated')),
    ]

    supplier    = models.ForeignKey(
        'suppliers.Supplier',
        verbose_name=_('Supplier'),
        on_delete=models.PROTECT,
        related_name='supplier_contracts',
    )
    reference   = models.CharField(_('Reference'), max_length=100, blank=True, default='')
    title       = models.CharField(_('Title'), max_length=255)
    signed_date = models.DateField(_('Signed date'), null=True, blank=True)
    valid_from  = models.DateField(_('Valid from'), null=True, blank=True)
    valid_until = models.DateField(_('Valid until'), null=True, blank=True)
    status      = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    notes       = models.TextField(_('Notes'), blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('Created by'),
        on_delete=models.PROTECT, related_name='supplier_contracts_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('Updated by'),
        on_delete=models.PROTECT, related_name='supplier_contracts_updated',
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Supplier Contract')
        verbose_name_plural = _('Supplier Contracts')
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.supplier.name} — {self.title}'

    @property
    def status_colour(self):
        return {'active': 'green', 'expired': 'grey', 'terminated': 'red'}.get(self.status, 'grey')


class SupplierContractLine(models.Model):
    """Product price line in a supplier contract."""

    contract    = models.ForeignKey(SupplierContract, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(_('Product / Description'), max_length=255)
    unit        = models.CharField(_('Unit'), max_length=30, blank=True, default='')
    unit_price  = models.DecimalField(_('Unit price (€)'), max_digits=14, decimal_places=4, default=Decimal('0'))
    notes       = models.TextField(_('Notes'), blank=True, default='')
    order       = models.PositiveSmallIntegerField(_('Order'), default=0)

    class Meta:
        verbose_name        = _('Supplier Contract Line')
        verbose_name_plural = _('Supplier Contract Lines')
        ordering            = ['order', 'id']

    def __str__(self):
        return f'{self.contract} — {self.description}'
