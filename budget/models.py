from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from decimal import Decimal


class Budget(models.Model):

    class Status(models.TextChoices):
        DRAFT    = 'draft',    _('Draft')
        SENT     = 'sent',     _('Sent')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
        EXPIRED  = 'expired',  _('Expired')

    number     = models.CharField(max_length=30, unique=True, verbose_name=_("Number"))
    title      = models.CharField(max_length=200, verbose_name=_("Title"))

    client = models.ForeignKey(
        'clients.Client', null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='budgets',
        verbose_name=_("Client")
    )
    project = models.ForeignKey(
        'projects.Project', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='budgets',
        verbose_name=_("Project / site")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Status")
    )
    issue_date = models.DateField(
        null=True, blank=True,
        verbose_name=_("Issue date")
    )
    valid_until = models.DateField(
        null=True, blank=True,
        verbose_name=_("Valid until")
    )
    global_margin_percent = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        verbose_name=_("Global margin (%)"),
        help_text=_("If set, overrides each line's margin.")
    )
    discount_percent = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Global discount (%)")
    )
    vat_rate = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=Decimal('23.00'),
        verbose_name=_("Default VAT (%)"),
        help_text=_("Default for new items. Each item may have its own VAT rate.")
    )
    notes        = models.TextField(blank=True, default='', verbose_name=_("Internal notes"))
    notes_client = models.TextField(blank=True, default='', verbose_name=_("Notes for client"))

    payment_terms = models.TextField(
        blank=True, default='',
        verbose_name=_("Payment terms"),
        help_text=_("E.g. 30% on signature, 40% at start, 30% on delivery.")
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='budgets_created',
        verbose_name=_("Created by")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at    = models.DateTimeField(null=True, blank=True, verbose_name=_("Sent at"))

    class Meta:
        verbose_name        = _("Budget")
        verbose_name_plural = _("Budgets")
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.number} — {self.title}"

    @property
    def subtotal_cost(self):
        return sum((item.total_cost for item in self.items.all()), Decimal('0'))

    @property
    def subtotal_ht(self):
        return sum((item.total_price for item in self.items.all()), Decimal('0'))

    @property
    def discount_amount(self):
        return (self.subtotal_ht * self.discount_percent / Decimal('100')).quantize(Decimal('0.01'))

    @property
    def total_ht(self):
        return self.subtotal_ht - self.discount_amount

    @property
    def total_vat(self):
        """Sum VAT for each line (each line may have its own rate)."""
        return sum((item.vat_amount for item in self.items.all()), Decimal('0'))

    @property
    def total_ttc(self):
        return self.total_ht + self.total_vat

    @property
    def gross_margin_amount(self):
        return self.total_ht - self.subtotal_cost

    @property
    def gross_margin_percent(self):
        if not self.total_ht:
            return Decimal('0')
        return (self.gross_margin_amount / self.total_ht * Decimal('100')).quantize(Decimal('0.01'))

    @classmethod
    def next_number(cls):
        import datetime
        year = datetime.date.today().year
        prefix = f"ORC-{year}-"
        last = (
            cls.objects.filter(number__startswith=prefix)
            .order_by('-number')
            .values_list('number', flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"


class BudgetChapter(models.Model):
    """
    Hierarchical chapter / lot within a budget.
    Supports up to 4 levels via recursive FK.
    """
    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name='chapters',
        verbose_name=_("Budget")
    )
    parent = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name=_("Parent chapter")
    )
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Order"))

    class Meta:
        verbose_name        = _("Chapter")
        verbose_name_plural = _("Chapters")
        ordering            = ['budget', 'order']

    def __str__(self):
        return self.title

    @property
    def depth(self):
        d = 0
        p = self.parent
        while p:
            d += 1
            p = p.parent
        return d

    @property
    def subtotal_cost(self):
        return sum((item.total_cost for item in self.items.all()), Decimal('0'))

    @property
    def subtotal_ht(self):
        return sum((item.total_price for item in self.items.all()), Decimal('0'))


class BudgetItem(models.Model):
    budget  = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name='items'
    )
    chapter = models.ForeignKey(
        BudgetChapter,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='items',
        verbose_name=_("Chapter")
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='budget_items',
        verbose_name=_("Service")
    )
    service_name_snapshot = models.CharField(max_length=200, verbose_name=_("Service (snapshot)"))
    service_code_snapshot = models.CharField(max_length=30,  verbose_name=_("Code"))
    service_unit_snapshot = models.CharField(max_length=20,  verbose_name=_("Unit"))
    description           = models.TextField(blank=True, default='', verbose_name=_("Description (override)"))
    quantity              = models.DecimalField(max_digits=12, decimal_places=4, verbose_name=_("Quantity"))
    unit_price_override   = models.DecimalField(
        max_digits=14, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Unit price (override)"),
        help_text=_("If set, replaces the catalog-calculated unit price.")
    )
    labor_cost_per_unit   = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0'), verbose_name=_("Labor cost / unit"))
    margin_percent        = models.DecimalField(max_digits=6, decimal_places=2, verbose_name=_("Margin (%)"))
    discount_percent      = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0'), verbose_name=_("Discount (%)"))
    vat_rate              = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('23.00'), verbose_name=_("VAT (%)"))
    order                 = models.PositiveIntegerField(default=0, verbose_name=_("Order"))

    class Meta:
        verbose_name        = _("Budget line")
        verbose_name_plural = _("Budget lines")
        ordering            = ['budget', 'chapter', 'order']

    def __str__(self):
        return f"{self.budget.number} › {self.service_name_snapshot}"

    @property
    def total_material_cost(self):
        return sum((m.total_cost for m in self.materials.all()), Decimal('0'))

    @property
    def total_labor_cost(self):
        return self.labor_cost_per_unit * self.quantity

    @property
    def total_cost(self):
        return self.total_material_cost + self.total_labor_cost

    @property
    def computed_unit_price(self):
        """Unit price from cost + margin."""
        if not self.quantity:
            return Decimal('0')
        margin = Decimal('1') + (self.margin_percent / Decimal('100'))
        return (self.total_cost / self.quantity) * margin

    @property
    def effective_unit_price(self):
        """Uses override when set, otherwise computed."""
        if self.unit_price_override and self.unit_price_override > 0:
            return self.unit_price_override
        return self.computed_unit_price

    @property
    def total_price_before_discount(self):
        return self.effective_unit_price * self.quantity

    @property
    def item_discount_amount(self):
        return (self.total_price_before_discount * self.discount_percent / Decimal('100')).quantize(Decimal('0.0001'))

    @property
    def total_price(self):
        return self.total_price_before_discount - self.item_discount_amount

    @property
    def vat_amount(self):
        return (self.total_price * self.vat_rate / Decimal('100')).quantize(Decimal('0.0001'))

    @property
    def total_ttc(self):
        return self.total_price + self.vat_amount


class BudgetItemMaterial(models.Model):
    budget_item = models.ForeignKey(
        BudgetItem,
        on_delete=models.CASCADE,
        related_name='materials'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='budget_usages',
        verbose_name=_("Product")
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='budget_material_usages',
        verbose_name=_("Supplier")
    )
    product_name_snapshot = models.CharField(max_length=255, verbose_name=_("Product (snapshot)"))
    unit_snapshot         = models.CharField(max_length=20,  verbose_name=_("Unit (snapshot)"))
    quantity              = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Quantity"))
    unit_price_snapshot   = models.DecimalField(
        max_digits=14, decimal_places=4,
        verbose_name=_("Unit price excl. VAT (snapshot)"),
        help_text=_("Price frozen when the budget was issued.")
    )

    class Meta:
        verbose_name        = _("Line material")
        verbose_name_plural = _("Line materials")

    def __str__(self):
        return f"{self.product_name_snapshot} × {self.quantity}"

    @property
    def total_cost(self):
        return self.quantity * self.unit_price_snapshot
