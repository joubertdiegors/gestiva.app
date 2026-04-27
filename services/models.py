from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class ServiceCategory(models.Model):
    name      = models.CharField(max_length=100, verbose_name=_("Name"))
    parent    = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='children',
        verbose_name=_("Parent category")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name        = _("Service category")
        verbose_name_plural = _("Service categories")
        unique_together     = [('name', 'parent')]

    def __str__(self):
        return f"{self.parent} > {self.name}" if self.parent else self.name


class Service(models.Model):
    code        = models.CharField(max_length=30, unique=True, verbose_name=_("Code"))
    name        = models.CharField(max_length=200, verbose_name=_("Name"))
    description = models.TextField(blank=True, default='', verbose_name=_("Technical description"))
    category    = models.ForeignKey(
        ServiceCategory, null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='services',
        verbose_name=_("Category")
    )
    unit = models.ForeignKey(
        'catalog.UnitOfMeasure',
        on_delete=models.PROTECT,
        related_name='services',
        verbose_name=_("Service unit of measure"),
        help_text=_("Unit in which the service is measured, e.g. m², m³, m, ea.")
    )
    time_per_unit = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Execution time / unit (minutes)"),
        help_text=_("Estimated minutes to execute one unit of the service.")
    )
    labor_cost_per_unit = models.DecimalField(
        max_digits=14, decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name=_("Labor cost / unit")
    )
    sale_price_per_unit = models.DecimalField(
        max_digits=14, decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name=_("Sale price / unit"),
        help_text=_("Price charged to the client per unit. 0 = use suggested price.")
    )
    default_margin_percent = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=Decimal('30.00'),
        verbose_name=_("Default margin (%)"),
        help_text=_("Can be adjusted in the quote.")
    )
    is_active  = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Service")
        verbose_name_plural = _("Services")
        ordering            = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def material_cost_per_unit(self):
        total = Decimal('0')
        for item in self.materials.select_related('product'):
            price = item.product.best_purchase_price or Decimal('0')
            total += price * item.effective_quantity
        return total

    @property
    def total_cost_per_unit(self):
        return self.material_cost_per_unit + self.labor_cost_per_unit

    @property
    def suggested_price_per_unit(self):
        if self.total_cost_per_unit == 0:
            return Decimal('0')
        margin = Decimal('1') + (self.default_margin_percent / Decimal('100'))
        return self.total_cost_per_unit * margin

    @property
    def effective_sale_price(self):
        """Effective sale price: manual when set, otherwise suggested."""
        if self.sale_price_per_unit and self.sale_price_per_unit > 0:
            return self.sale_price_per_unit
        return self.suggested_price_per_unit


class ServiceMaterial(models.Model):
    service  = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name=_("Service")
    )
    product  = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='service_usages',
        verbose_name=_("Product")
    )
    quantity_per_unit = models.DecimalField(
        max_digits=12, decimal_places=4,
        verbose_name=_("Quantity per service unit")
    )
    waste_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Waste / scrap (%)")
    )
    note = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Note"))

    class Meta:
        verbose_name        = _("Service material")
        verbose_name_plural = _("Service materials")
        unique_together     = [('service', 'product')]

    def __str__(self):
        return f"{self.service.code}: {self.product.name} x {self.quantity_per_unit}"

    @property
    def effective_quantity(self):
        factor = Decimal('1') + (self.waste_percent / Decimal('100'))
        return self.quantity_per_unit * factor

    @property
    def unit_cost(self):
        price = self.product.best_purchase_price or Decimal('0')
        return price * self.effective_quantity
