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
        verbose_name=_("Produit")
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.PROTECT,
        related_name='product_offers',
        verbose_name=_("Fournisseur")
    )
    supplier_ref         = models.CharField(max_length=100, blank=True, default='', verbose_name=_("Ref. fournisseur"))
    supplier_description = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Description fournisseur"))
    unit_price = models.DecimalField(
        max_digits=14, decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name=_("Prix unitaire HT"),
        help_text=_("Prix par unite de base du produit.")
    )
    package_qty  = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal('1'),
        verbose_name=_("Qte par emballage")
    )
    package_unit = models.ForeignKey(
        'catalog.UnitOfMeasure', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='package_offers',
        verbose_name=_("Unite d'emballage")
    )
    minimum_order_qty = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal('1'),
        verbose_name=_("Quantite minimale de commande")
    )
    lead_time_days = models.PositiveIntegerField(default=0, verbose_name=_("Delai de livraison (jours)"))
    is_preferred   = models.BooleanField(default=False, verbose_name=_("Fournisseur prefere"))
    is_active      = models.BooleanField(default=True, verbose_name=_("Actif"))
    valid_from     = models.DateField(null=True, blank=True, verbose_name=_("Valide du"))
    valid_until    = models.DateField(null=True, blank=True, verbose_name=_("Valide jusqu'au"))
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Offre fournisseur")
        verbose_name_plural = _("Offres fournisseurs")
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
        verbose_name=_("Offre")
    )
    price          = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Prix HT"))
    effective_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))
    changed_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Modifie par")
    )
    note = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Motif"))

    class Meta:
        verbose_name        = _("Historique de prix")
        verbose_name_plural = _("Historique des prix")
        ordering            = ['-effective_date']

    def __str__(self):
        return f"{self.product_supplier} @ {self.price}"


class RFQ(models.Model):
    class Status(models.TextChoices):
        DRAFT     = 'draft',     _('Rascunho')
        SENT      = 'sent',      _('Enviado')
        PARTIAL   = 'partial',   _('Parcial')
        CLOSED    = 'closed',    _('Fechado')
        CANCELLED = 'cancelled', _('Cancelado')

    number = models.CharField(max_length=30, unique=True, blank=True, default='', verbose_name=_("Número"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name=_("Estado"))

    due_date = models.DateField(null=True, blank=True, verbose_name=_("Prazo para resposta"))
    notes    = models.TextField(blank=True, default='', verbose_name=_("Observações"))

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rfqs_requested',
        verbose_name=_("Solicitado por"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Criado em"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Atualizado em"))

    class Meta:
        verbose_name = _("Cotação (RFQ)")
        verbose_name_plural = _("Cotações (RFQ)")
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
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='rfq_items', verbose_name=_("Produto"))
    selected_vendor = models.ForeignKey(
        'procurement.RFQVendor',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='selected_items',
        verbose_name=_("Fornecedor selecionado"),
    )

    qty = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=Decimal('1'),
        verbose_name=_("Quantidade"),
    )
    notes = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Observações"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Item da cotação")
        verbose_name_plural = _("Itens da cotação")
        unique_together = [('rfq', 'product')]
        ordering = ['id']
        indexes = [
            models.Index(fields=['rfq', 'product']),
        ]

    def __str__(self):
        return f"{self.rfq} - {self.product.name}"


class RFQVendor(models.Model):
    class Status(models.TextChoices):
        PENDING  = 'pending',  _('Pendente')
        SENT     = 'sent',     _('Enviado')
        ANSWERED = 'answered', _('Respondido')
        DECLINED = 'declined', _('Recusado')

    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='vendors', verbose_name=_("RFQ"))
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.PROTECT, related_name='rfq_invitations', verbose_name=_("Fornecedor"))

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("Estado"))
    message = models.TextField(blank=True, default='', verbose_name=_("Mensagem"))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Enviado em"))

    payment_term = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name=_("Prazo de pagamento"),
    )
    quote_validity = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Validade do orçamento"),
    )

    quote_contact = models.ForeignKey(
        'suppliers.SupplierContact',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rfq_vendors',
        verbose_name=_("Responsável (contacto)"),
    )

    quote_contact_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name=_("Responsável pelo orçamento"),
        help_text=_("Contacto comercial a tratar desta cotação junto do fornecedor."),
    )
    quote_contact_phone = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("Telefone (orçamento)"),
    )
    quote_contact_email = models.EmailField(
        blank=True,
        default='',
        verbose_name=_("E-mail (orçamento)"),
    )

    class Meta:
        verbose_name = _("Fornecedor convidado")
        verbose_name_plural = _("Fornecedores convidados")
        unique_together = [('rfq', 'supplier')]
        ordering = ['id']
        indexes = [
            models.Index(fields=['rfq', 'supplier']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.rfq} - {self.supplier}"


class RFQVendorLine(models.Model):
    rfq_vendor = models.ForeignKey(RFQVendor, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Fornecedor"))
    rfq_item   = models.ForeignKey(RFQItem, on_delete=models.CASCADE, related_name='vendor_lines', verbose_name=_("Item"))

    unit_price = models.DecimalField(
        max_digits=14, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Preço unit. HT"),
    )
    package_qty = models.DecimalField(
        max_digits=12, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Qtd por embalagem"),
    )
    minimum_order_qty = models.DecimalField(
        max_digits=12, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Qtd mínima"),
    )
    lead_time_days = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Lead time (dias)"))
    valid_until = models.DateField(null=True, blank=True, verbose_name=_("Válido até"))

    answered_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Respondido em"))
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Linha de resposta")
        verbose_name_plural = _("Linhas de resposta")
        unique_together = [('rfq_vendor', 'rfq_item')]
        indexes = [
            models.Index(fields=['rfq_vendor', 'rfq_item']),
        ]

    def __str__(self):
        return f"{self.rfq_vendor} - {self.rfq_item.product.name}"

    def mark_answered_now(self):
        self.answered_at = timezone.now()
        self.save(update_fields=['answered_at'])
