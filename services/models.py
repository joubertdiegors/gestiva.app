from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class ServiceCategory(models.Model):
    name      = models.CharField(max_length=100, verbose_name=_("Nom"))
    parent    = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='children',
        verbose_name=_("Categorie parente")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name        = _("Categorie de service")
        verbose_name_plural = _("Categories de services")
        unique_together     = [('name', 'parent')]

    def __str__(self):
        return f"{self.parent} > {self.name}" if self.parent else self.name


class Service(models.Model):
    code        = models.CharField(max_length=30, unique=True, verbose_name=_("Code"))
    name        = models.CharField(max_length=200, verbose_name=_("Nom"))
    description = models.TextField(blank=True, default='', verbose_name=_("Description technique"))
    category    = models.ForeignKey(
        ServiceCategory, null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='services',
        verbose_name=_("Categorie")
    )
    unit = models.ForeignKey(
        'catalog.UnitOfMeasure',
        on_delete=models.PROTECT,
        related_name='services',
        verbose_name=_("Unite du service"),
        help_text=_("Unite dans laquelle le service est mesure. Ex: m2, m3, ml, un.")
    )
    # Tempo estimado de execução por unidade (campo de duração em minutos)
    time_per_unit = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Tempo de execução / unidade (min)"),
        help_text=_("Tempo estimado em minutos para executar uma unidade do serviço.")
    )
    labor_cost_per_unit = models.DecimalField(
        max_digits=14, decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name=_("Cout M.O. / unite")
    )
    # Preço de venda definido manualmente (pode ser 0 para usar o sugerido)
    sale_price_per_unit = models.DecimalField(
        max_digits=14, decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name=_("Preço de venda / unidade"),
        help_text=_("Preço cobrado ao cliente por unidade. 0 = usar preço sugerido.")
    )
    default_margin_percent = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=Decimal('30.00'),
        verbose_name=_("Marge par defaut (%)"),
        help_text=_("Peut etre ajustee dans le devis.")
    )
    is_active  = models.BooleanField(default=True, verbose_name=_("Actif"))
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
        """Preço de venda efectivo: manual se definido, senão sugerido."""
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
        verbose_name=_("Produit")
    )
    quantity_per_unit = models.DecimalField(
        max_digits=12, decimal_places=4,
        verbose_name=_("Quantite par unite de service")
    )
    waste_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Perte technique (%)")
    )
    note = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Observation"))

    class Meta:
        verbose_name        = _("Materiau du service")
        verbose_name_plural = _("Materiaux du service")
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
