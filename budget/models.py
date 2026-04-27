from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from decimal import Decimal


class Budget(models.Model):

    class Status(models.TextChoices):
        DRAFT    = 'draft',    _('Rascunho')
        SENT     = 'sent',     _('Enviado')
        APPROVED = 'approved', _('Aprovado')
        REJECTED = 'rejected', _('Recusado')
        EXPIRED  = 'expired',  _('Expirado')

    number     = models.CharField(max_length=30, unique=True, verbose_name=_("Número"))
    title      = models.CharField(max_length=200, verbose_name=_("Título"))

    client = models.ForeignKey(
        'clients.Client', null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='budgets',
        verbose_name=_("Cliente")
    )
    project = models.ForeignKey(
        'projects.Project', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='budgets',
        verbose_name=_("Obra / Projecto")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Estado")
    )
    issue_date = models.DateField(
        null=True, blank=True,
        verbose_name=_("Data de emissão")
    )
    valid_until = models.DateField(
        null=True, blank=True,
        verbose_name=_("Válido até")
    )
    global_margin_percent = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        verbose_name=_("Margem global (%)"),
        help_text=_("Se preenchida, substitui a margem de cada linha.")
    )
    discount_percent = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Desconto global (%)")
    )
    # IVA global — aplicado quando item não tem IVA próprio
    vat_rate = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=Decimal('23.00'),
        verbose_name=_("IVA padrão (%)"),
        help_text=_("Usado como padrão para novos itens. Cada item pode ter IVA próprio.")
    )
    notes        = models.TextField(blank=True, default='', verbose_name=_("Notas internas"))
    notes_client = models.TextField(blank=True, default='', verbose_name=_("Notas para o cliente"))

    # Condições de pagamento — texto descritivo (fase 1); estruturado na fase 2
    payment_terms = models.TextField(
        blank=True, default='',
        verbose_name=_("Condições de pagamento"),
        help_text=_("Ex: 30% na assinatura, 40% no início, 30% na entrega.")
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='budgets_created',
        verbose_name=_("Criado por")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at    = models.DateTimeField(null=True, blank=True, verbose_name=_("Enviado em"))

    class Meta:
        verbose_name        = _("Orçamento")
        verbose_name_plural = _("Orçamentos")
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.number} — {self.title}"

    # ── aggregates ──────────────────────────────────────────────────────────

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
        """Soma o IVA de cada item (cada um tem o seu próprio rate)."""
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

    # ── auto-number ──────────────────────────────────────────────────────────
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
    Capítulo / lote hierárquico de um orçamento.
    Suporta até 4 níveis via FK recursiva.
    """
    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name='chapters',
        verbose_name=_("Orçamento")
    )
    parent = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name=_("Capítulo pai")
    )
    title = models.CharField(max_length=200, verbose_name=_("Título"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Ordem"))

    class Meta:
        verbose_name        = _("Capítulo")
        verbose_name_plural = _("Capítulos")
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
        verbose_name=_("Capítulo")
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='budget_items',
        verbose_name=_("Serviço")
    )
    service_name_snapshot = models.CharField(max_length=200, verbose_name=_("Serviço"))
    service_code_snapshot = models.CharField(max_length=30,  verbose_name=_("Código"))
    service_unit_snapshot = models.CharField(max_length=20,  verbose_name=_("Unidade"))
    description           = models.TextField(blank=True, default='', verbose_name=_("Descrição (override)"))
    quantity              = models.DecimalField(max_digits=12, decimal_places=4, verbose_name=_("Quantidade"))
    unit_price_override   = models.DecimalField(
        max_digits=14, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Preço unit. (override)"),
        help_text=_("Se preenchido, substitui o preço calculado pelo catálogo.")
    )
    labor_cost_per_unit   = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0'), verbose_name=_("Custo M.O. / unidade"))
    margin_percent        = models.DecimalField(max_digits=6, decimal_places=2, verbose_name=_("Margem (%)"))
    discount_percent      = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0'), verbose_name=_("Desconto (%)"))
    vat_rate              = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('23.00'), verbose_name=_("IVA (%)"))
    order                 = models.PositiveIntegerField(default=0, verbose_name=_("Ordem"))

    class Meta:
        verbose_name        = _("Linha de orçamento")
        verbose_name_plural = _("Linhas de orçamento")
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
        """Preço unitário calculado a partir do custo + margem."""
        if not self.quantity:
            return Decimal('0')
        margin = Decimal('1') + (self.margin_percent / Decimal('100'))
        return (self.total_cost / self.quantity) * margin

    @property
    def effective_unit_price(self):
        """Usa override se definido, senão o calculado."""
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
        verbose_name=_("Produto")
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='budget_material_usages',
        verbose_name=_("Fornecedor")
    )
    product_name_snapshot = models.CharField(max_length=255, verbose_name=_("Produto (snapshot)"))
    unit_snapshot         = models.CharField(max_length=20,  verbose_name=_("Unidade (snapshot)"))
    quantity              = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Quantidade"))
    unit_price_snapshot   = models.DecimalField(
        max_digits=14, decimal_places=4,
        verbose_name=_("Preço unit. HT (snapshot)"),
        help_text=_("Preço congelado no momento da emissão do orçamento.")
    )

    class Meta:
        verbose_name        = _("Material da linha")
        verbose_name_plural = _("Materiais da linha")

    def __str__(self):
        return f"{self.product_name_snapshot} × {self.quantity}"

    @property
    def total_cost(self):
        return self.quantity * self.unit_price_snapshot
