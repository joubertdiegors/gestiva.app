from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError


# ── CATEGORIA DE EQUIPAMENTO ──────────────────────────────────────────────────
class EquipmentCategory(models.Model):
    name = models.CharField(_("Name"), max_length=100, unique=True)

    class Meta:
        verbose_name = _("Equipment Category")
        verbose_name_plural = _("Equipment Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name


# ── EQUIPAMENTO ───────────────────────────────────────────────────────────────
class Equipment(models.Model):

    STATUS_AVAILABLE = "available"
    STATUS_LOANED = "loaned"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_SOLD = "sold"
    STATUS_WRITTEN_OFF = "written_off"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, _("Available")),
        (STATUS_LOANED, _("Loaned")),
        (STATUS_MAINTENANCE, _("In Maintenance")),
        (STATUS_SOLD, _("Sold")),
        (STATUS_WRITTEN_OFF, _("Written Off")),
    ]

    CONDITION_NEW = "new"
    CONDITION_GOOD = "good"
    CONDITION_FAIR = "fair"
    CONDITION_POOR = "poor"
    CONDITION_CHOICES = [
        (CONDITION_NEW, _("New")),
        (CONDITION_GOOD, _("Good")),
        (CONDITION_FAIR, _("Fair")),
        (CONDITION_POOR, _("Poor")),
    ]

    category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.PROTECT,
        related_name="equipments",
        verbose_name=_("Category"),
    )
    name = models.CharField(_("Name"), max_length=150)
    brand = models.CharField(_("Brand"), max_length=80, blank=True, default="")
    model = models.CharField(_("Model"), max_length=80, blank=True, default="")
    serial_number = models.CharField(_("Serial Number"), max_length=100, blank=True, default="")
    internal_code = models.CharField(
        _("Internal Code"), max_length=30, blank=True, default="",
        help_text=_("Optional internal reference (e.g. EQ-001)"),
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE, db_index=True
    )
    condition = models.CharField(
        _("Condition"), max_length=10, choices=CONDITION_CHOICES, default=CONDITION_GOOD
    )
    purchase_date = models.DateField(_("Purchase Date"), null=True, blank=True)
    purchase_price = models.DecimalField(
        _("Purchase Price (€)"), max_digits=14, decimal_places=4, null=True, blank=True
    )
    notes = models.TextField(_("Notes"), blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Equipment")
        verbose_name_plural = _("Equipments")
        ordering = ["category", "name"]

    def __str__(self):
        code = f"[{self.internal_code}] " if self.internal_code else ""
        brand_model = f" {self.brand} {self.model}".strip()
        return f"{code}{self.name}{brand_model}"

    @property
    def display_name(self):
        code = f"[{self.internal_code}] " if self.internal_code else ""
        return f"{code}{self.name}"

    @property
    def active_loan(self):
        return self.loans.filter(returned_at__isnull=True).first()


# ── EMPRÉSTIMO A FUNCIONÁRIO ──────────────────────────────────────────────────
class EquipmentLoan(models.Model):
    """
    Regista a entrega de um equipamento a um funcionário.
    O funcionário assina um ticket impresso neste momento.
    """

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name="loans",
        verbose_name=_("Equipment"),
    )
    collaborator = models.ForeignKey(
        "workforce.Collaborator",
        on_delete=models.PROTECT,
        related_name="equipment_loans",
        verbose_name=_("Collaborator"),
    )
    loaned_at = models.DateTimeField(_("Loaned At"), default=timezone.now)
    expected_return = models.DateField(_("Expected Return"), null=True, blank=True)
    returned_at = models.DateTimeField(_("Returned At"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True, default="")
    ticket_printed = models.BooleanField(_("Ticket Printed"), default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Equipment Loan")
        verbose_name_plural = _("Equipment Loans")
        ordering = ["-loaned_at"]

    def __str__(self):
        return f"{self.equipment} → {self.collaborator} ({self.loaned_at.date()})"

    @property
    def is_active(self):
        return self.returned_at is None

    @property
    def is_overdue(self):
        if self.expected_return and self.returned_at is None:
            return self.expected_return < timezone.now().date()
        return False

    def clean(self):
        if self.pk:
            return
        # Ao criar: verificar se o equipamento já está emprestado
        if self.equipment_id:
            active = EquipmentLoan.objects.filter(
                equipment_id=self.equipment_id,
                returned_at__isnull=True,
            ).exclude(pk=self.pk)
            if active.exists():
                raise ValidationError(
                    _("This equipment is already on loan and has not been returned.")
                )


# ── VENDA A FUNCIONÁRIO ───────────────────────────────────────────────────────
class EquipmentSale(models.Model):
    """
    O equipamento é comprado pela empresa e vendido/cedido ao funcionário,
    podendo ser parcelado (desconto em folha).
    """

    STATUS_PENDING = "pending"
    STATUS_PARTIAL = "partial"
    STATUS_PAID = "paid"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_PARTIAL, _("Partial")),
        (STATUS_PAID, _("Paid Off")),
    ]

    equipment = models.OneToOneField(
        Equipment,
        on_delete=models.PROTECT,
        related_name="sale",
        verbose_name=_("Equipment"),
    )
    collaborator = models.ForeignKey(
        "workforce.Collaborator",
        on_delete=models.PROTECT,
        related_name="equipment_purchases",
        verbose_name=_("Collaborator"),
    )
    sale_date = models.DateField(_("Sale Date"), default=timezone.now)
    sale_price = models.DecimalField(_("Sale Price (€)"), max_digits=14, decimal_places=4)
    installments = models.PositiveSmallIntegerField(_("Installments"), default=1)
    amount_paid = models.DecimalField(
        _("Amount Paid (€)"), max_digits=14, decimal_places=4, default=0
    )
    status = models.CharField(
        _("Status"), max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    notes = models.TextField(_("Notes"), blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Equipment Sale")
        verbose_name_plural = _("Equipment Sales")
        ordering = ["-sale_date"]

    def __str__(self):
        return f"{self.equipment} → {self.collaborator} ({self.sale_date})"

    @property
    def balance_due(self):
        return self.sale_price - self.amount_paid

    @property
    def installment_value(self):
        if self.installments and self.installments > 0:
            return self.sale_price / self.installments
        return self.sale_price
