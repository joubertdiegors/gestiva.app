from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from decimal import Decimal
from django.utils import timezone


class ProductSupplier(models.Model):
    product  = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='supplier_offers',
        verbose_name=_("Product")
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.PROTECT,
        related_name='product_offers',
        verbose_name=_("Supplier")
    )
    supplier_ref         = models.CharField(max_length=100, blank=True, default='', verbose_name=_("Supplier reference"))
    supplier_description = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Supplier description"))
    unit_price = models.DecimalField(
        max_digits=14, decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name=_("Unit price excl. VAT"),
        help_text=_("Price per base unit of the product.")
    )
    package_qty  = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal('1'),
        verbose_name=_("Quantity per package")
    )
    package_unit = models.ForeignKey(
        'catalog.UnitOfMeasure', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='package_offers',
        verbose_name=_("Package unit")
    )
    minimum_order_qty = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal('1'),
        verbose_name=_("Minimum order quantity")
    )
    lead_time_days = models.PositiveIntegerField(default=0, verbose_name=_("Lead time (days)"))
    is_preferred   = models.BooleanField(default=False, verbose_name=_("Preferred supplier"))
    is_active      = models.BooleanField(default=True, verbose_name=_("Active"))
    valid_from     = models.DateField(null=True, blank=True, verbose_name=_("Valid from"))
    valid_until    = models.DateField(null=True, blank=True, verbose_name=_("Valid until"))
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Supplier offer")
        verbose_name_plural = _("Supplier offers")
        unique_together     = [('product', 'supplier')]
        ordering            = ['unit_price']
        indexes = [
            models.Index(fields=['product', 'is_active', 'unit_price']),
            models.Index(fields=['supplier', 'is_active']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.supplier.name} @ {self.unit_price}"

    @property
    def package_price(self):
        return self.unit_price * self.package_qty


class ProductSupplierPriceHistory(models.Model):
    product_supplier = models.ForeignKey(
        ProductSupplier,
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name=_("Offer")
    )
    price          = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Price excl. VAT"))
    effective_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))
    changed_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Changed by")
    )
    note = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Reason"))

    class Meta:
        verbose_name        = _("Price history entry")
        verbose_name_plural = _("Price history")
        ordering            = ['-effective_date']

    def __str__(self):
        return f"{self.product_supplier} @ {self.price}"


class RFQ(models.Model):
    class Status(models.TextChoices):
        DRAFT     = 'draft',     _('Draft')
        SENT      = 'sent',      _('Sent')
        PARTIAL   = 'partial',   _('Partial')
        CLOSED    = 'closed',    _('Closed')
        CANCELLED = 'cancelled', _('Cancelled')

    number = models.CharField(max_length=30, unique=True, blank=True, default='', verbose_name=_("Number"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name=_("Status"))

    due_date = models.DateField(null=True, blank=True, verbose_name=_("Response due date"))
    notes    = models.TextField(blank=True, default='', verbose_name=_("Notes"))

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rfqs_requested',
        verbose_name=_("Requested by"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Request for quotation (RFQ)")
        verbose_name_plural = _("Requests for quotation (RFQ)")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return self.number or f"RFQ #{self.pk}"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating and not self.number:
            self.number = f"RFQ-{self.pk:06d}"
            super().save(update_fields=['number'])


class RFQItem(models.Model):
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='items', verbose_name=_("RFQ"))
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='rfq_items', verbose_name=_("Product"))
    selected_vendor = models.ForeignKey(
        'procurement.RFQVendor',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='selected_items',
        verbose_name=_("Selected vendor"),
    )

    qty = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=Decimal('1'),
        verbose_name=_("Quantity"),
    )
    notes = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Notes"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("RFQ line")
        verbose_name_plural = _("RFQ lines")
        unique_together = [('rfq', 'product')]
        ordering = ['id']
        indexes = [
            models.Index(fields=['rfq', 'product']),
        ]

    def __str__(self):
        return f"{self.rfq} - {self.product.name}"


class RFQVendor(models.Model):
    class Status(models.TextChoices):
        PENDING  = 'pending',  _('Pending')
        SENT     = 'sent',     _('Sent')
        ANSWERED = 'answered', _('Answered')
        DECLINED = 'declined', _('Declined')

    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='vendors', verbose_name=_("RFQ"))
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.PROTECT, related_name='rfq_invitations', verbose_name=_("Supplier"))

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("Status"))
    message = models.TextField(blank=True, default='', verbose_name=_("Message"))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Sent at"))

    payment_term = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name=_("Payment term"),
    )
    quote_validity = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Quote valid until"),
    )

    quote_contact = models.ForeignKey(
        'suppliers.SupplierContact',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rfq_vendors',
        verbose_name=_("Quote contact"),
    )

    quote_contact_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name=_("Quote contact name"),
        help_text=_("Commercial contact at the supplier for this RFQ."),
    )
    quote_contact_phone = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("Quote contact phone"),
    )
    quote_contact_email = models.EmailField(
        blank=True,
        default='',
        verbose_name=_("Quote contact email"),
    )

    class Meta:
        verbose_name = _("Invited supplier")
        verbose_name_plural = _("Invited suppliers")
        unique_together = [('rfq', 'supplier')]
        ordering = ['id']
        indexes = [
            models.Index(fields=['rfq', 'supplier']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.rfq} - {self.supplier}"


class RFQVendorLine(models.Model):
    rfq_vendor = models.ForeignKey(RFQVendor, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Supplier"))
    rfq_item   = models.ForeignKey(RFQItem, on_delete=models.CASCADE, related_name='vendor_lines', verbose_name=_("Item"))

    unit_price = models.DecimalField(
        max_digits=14, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Unit price excl. VAT"),
    )
    package_qty = models.DecimalField(
        max_digits=12, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Quantity per package"),
    )
    minimum_order_qty = models.DecimalField(
        max_digits=12, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Minimum order quantity"),
    )
    lead_time_days = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Lead time (days)"))
    valid_until = models.DateField(null=True, blank=True, verbose_name=_("Valid until"))

    answered_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Answered at"))
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Response line")
        verbose_name_plural = _("Response lines")
        unique_together = [('rfq_vendor', 'rfq_item')]
        indexes = [
            models.Index(fields=['rfq_vendor', 'rfq_item']),
        ]

    def __str__(self):
        return f"{self.rfq_vendor} - {self.rfq_item.product.name}"

    def mark_answered_now(self):
        self.answered_at = timezone.now()
        self.save(update_fields=['answered_at'])
