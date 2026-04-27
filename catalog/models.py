from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class UnitOfMeasure(models.Model):
    symbol = models.CharField(max_length=20, unique=True, verbose_name=_('Symbol'))
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    description = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Description'))

    class Meta:
        verbose_name = _('Unit of measure')
        verbose_name_plural = _('Units of measure')
        ordering = ['symbol']

    def __str__(self):
        return f'{self.symbol} - {self.name}'


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='children',
        verbose_name=_('Parent category'),
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        verbose_name = _('Product category')
        verbose_name_plural = _('Product categories')
        unique_together = [('name', 'parent')]

    def __str__(self):
        return f'{self.parent} > {self.name}' if self.parent else self.name


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Product name'))
    brand = models.CharField(max_length=100, blank=True, default='', verbose_name=_('Brand'))
    barcode = models.CharField(max_length=100, blank=True, default='', verbose_name=_('Barcode'))
    category = models.ForeignKey(
        ProductCategory,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Category'),
    )
    unit = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Base unit'),
        help_text=_('Internal reference unit, e.g. kg, m², ea.'),
    )
    vat_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('21.00'),
        verbose_name=_('VAT rate (%)'),
    )
    sale_margin = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Sale margin (%)'),
    )
    notes = models.TextField(blank=True, default='', verbose_name=_('Notes'))
    is_active = models.BooleanField(default=True, verbose_name=_('Product active'))
    is_approved = models.BooleanField(
        default=False,
        verbose_name=_('Approved'),
        help_text=_('Only approved products appear in quotes.'),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='products_created',
        verbose_name=_('Created by'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'is_approved']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.name

    @property
    def best_purchase_price(self):
        offer = self.supplier_offers.filter(is_active=True).order_by('unit_price').first()
        return offer.unit_price if offer else Decimal('0.00')

    @property
    def sale_price_ht(self):
        base = self.best_purchase_price
        return base * (1 + self.sale_margin / 100)

    @property
    def sale_price_ttc(self):
        return self.sale_price_ht * (1 + self.vat_rate / 100)
