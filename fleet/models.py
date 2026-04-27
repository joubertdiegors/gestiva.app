from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# ── CATEGORIA DE VEÍCULO ─────────────────────────────────────────────────────
class VehicleCategory(models.Model):
    name = models.CharField(_("Name"), max_length=100, unique=True)

    class Meta:
        verbose_name = _("Vehicle Category")
        verbose_name_plural = _("Vehicle Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name


# ── VEÍCULO ───────────────────────────────────────────────────────────────────
class Vehicle(models.Model):

    STATUS_ACTIVE = "active"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_SOLD = "sold"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, _("Active")),
        (STATUS_MAINTENANCE, _("In Maintenance")),
        (STATUS_SOLD, _("Sold")),
    ]

    FUEL_DIESEL = "diesel"
    FUEL_PETROL = "petrol"
    FUEL_ELECTRIC = "electric"
    FUEL_HYBRID = "hybrid"
    FUEL_CNG = "cng"
    FUEL_CHOICES = [
        (FUEL_DIESEL, _("Diesel")),
        (FUEL_PETROL, _("Petrol")),
        (FUEL_ELECTRIC, _("Electric")),
        (FUEL_HYBRID, _("Hybrid")),
        (FUEL_CNG, _("CNG")),
    ]

    license_plate = models.CharField(_("License Plate"), max_length=20, unique=True)
    brand = models.CharField(_("Brand"), max_length=80)
    model = models.CharField(_("Model"), max_length=80)
    year = models.PositiveSmallIntegerField(_("Year"))
    color = models.CharField(_("Color"), max_length=50, blank=True, default="")
    vin = models.CharField(_("VIN / Chassis"), max_length=50, blank=True, default="")
    category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.PROTECT,
        related_name="vehicles",
        verbose_name=_("Category"),
    )
    fuel_type = models.CharField(
        _("Fuel Type"), max_length=20, choices=FUEL_CHOICES, default=FUEL_DIESEL
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    current_km = models.PositiveIntegerField(_("Current KM"), default=0)
    default_driver = models.ForeignKey(
        "workforce.Collaborator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_vehicles",
        verbose_name=_("Default Driver"),
    )
    notes = models.TextField(_("Notes"), blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Vehicle")
        verbose_name_plural = _("Vehicles")
        ordering = ["license_plate"]

    def __str__(self):
        return f"{self.license_plate} — {self.brand} {self.model} ({self.year})"

    @property
    def display_name(self):
        return f"{self.license_plate} {self.brand} {self.model}"


# ── DOCUMENTO DO VEÍCULO ─────────────────────────────────────────────────────
class VehicleDocument(models.Model):
    """Documentos belgas com vencimento: seguro, controlo técnico, etc."""

    TYPE_INSURANCE = "insurance"
    TYPE_TECHNICAL_INSPECTION = "technical_inspection"  # Controlo técnico (AIB/GOCA)
    TYPE_REGISTRATION = "registration"                  # Certificado de matrícula (DIV)
    TYPE_ROAD_TAX = "road_tax"                          # Taxe de circulation
    TYPE_LEASING = "leasing"                            # Leasing / renting
    TYPE_TACHOGRAPH = "tachograph"                      # Tacógrafo (pesados)
    TYPE_ADR = "adr"                                    # Certificado ADR
    TYPE_OTHER = "other"

    TYPE_CHOICES = [
        (TYPE_INSURANCE, _("Insurance (RC / Omnium)")),
        (TYPE_TECHNICAL_INSPECTION, _("Technical inspection")),
        (TYPE_REGISTRATION, _("Registration certificate")),
        (TYPE_ROAD_TAX, _("Road tax / circulation tax")),
        (TYPE_LEASING, _("Leasing / Renting Contract")),
        (TYPE_TACHOGRAPH, _("Tachograph Calibration")),
        (TYPE_ADR, _("ADR Certificate")),
        (TYPE_OTHER, _("Other")),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Vehicle"),
    )
    doc_type = models.CharField(_("Type"), max_length=30, choices=TYPE_CHOICES)
    description = models.CharField(_("Description"), max_length=200, blank=True, default="")
    issue_date = models.DateField(_("Issue Date"), null=True, blank=True)
    expiry_date = models.DateField(_("Expiry Date"), null=True, blank=True)
    insurer_or_entity = models.CharField(
        _("Insurer / Entity"), max_length=120, blank=True, default=""
    )
    reference = models.CharField(_("Reference / Policy No."), max_length=100, blank=True, default="")
    cost = models.DecimalField(
        _("Cost (€)"), max_digits=14, decimal_places=4, null=True, blank=True
    )
    file = models.FileField(
        _("File"), upload_to="fleet/documents/", null=True, blank=True
    )
    notes = models.TextField(_("Notes"), blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Vehicle Document")
        verbose_name_plural = _("Vehicle Documents")
        ordering = ["vehicle", "expiry_date"]

    def __str__(self):
        return f"{self.vehicle.license_plate} — {self.get_doc_type_display()}"

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_until_expiry(self):
        if self.expiry_date:
            return (self.expiry_date - timezone.now().date()).days
        return None


# ── MANUTENÇÃO ────────────────────────────────────────────────────────────────
class VehicleMaintenance(models.Model):

    TYPE_PREVENTIVE = "preventive"
    TYPE_CORRECTIVE = "corrective"
    TYPE_CHOICES = [
        (TYPE_PREVENTIVE, _("Preventive")),
        (TYPE_CORRECTIVE, _("Corrective")),
    ]

    STATUS_SCHEDULED = "scheduled"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, _("Scheduled")),
        (STATUS_IN_PROGRESS, _("In Progress")),
        (STATUS_DONE, _("Done")),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="maintenances",
        verbose_name=_("Vehicle"),
    )
    maintenance_type = models.CharField(
        _("Type"), max_length=20, choices=TYPE_CHOICES, default=TYPE_PREVENTIVE
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED
    )
    description = models.TextField(_("Description"))
    scheduled_date = models.DateField(_("Scheduled Date"), null=True, blank=True)
    completed_date = models.DateField(_("Completed Date"), null=True, blank=True)
    km_at_service = models.PositiveIntegerField(_("KM at Service"), null=True, blank=True)
    next_service_km = models.PositiveIntegerField(_("Next Service KM"), null=True, blank=True)
    workshop = models.CharField(_("Workshop / Garage"), max_length=150, blank=True, default="")
    cost = models.DecimalField(
        _("Cost (€)"), max_digits=14, decimal_places=4, null=True, blank=True
    )
    invoice_reference = models.CharField(_("Invoice Ref."), max_length=80, blank=True, default="")
    notes = models.TextField(_("Notes"), blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Maintenance")
        verbose_name_plural = _("Maintenances")
        ordering = ["-scheduled_date"]

    def __str__(self):
        return (
            f"{self.vehicle.license_plate} — {self.get_maintenance_type_display()}"
            f" ({self.scheduled_date})"
        )


# ── ABASTECIMENTO ─────────────────────────────────────────────────────────────
class VehicleFueling(models.Model):

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="fuelings",
        verbose_name=_("Vehicle"),
    )
    driver = models.ForeignKey(
        "workforce.Collaborator",
        on_delete=models.PROTECT,
        related_name="fuelings",
        verbose_name=_("Driver"),
    )
    date = models.DateField(_("Date"))
    km = models.PositiveIntegerField(_("KM at Fueling"))
    liters = models.DecimalField(_("Liters"), max_digits=8, decimal_places=2)
    fuel_type = models.CharField(
        _("Fuel Type"),
        max_length=20,
        choices=Vehicle.FUEL_CHOICES,
        default=Vehicle.FUEL_DIESEL,
    )
    price_per_liter = models.DecimalField(
        _("Price / Liter (€)"), max_digits=8, decimal_places=4, null=True, blank=True
    )
    total_cost = models.DecimalField(_("Total Cost (€)"), max_digits=14, decimal_places=4)
    station = models.CharField(_("Station"), max_length=120, blank=True, default="")
    full_tank = models.BooleanField(_("Full Tank"), default=True)
    notes = models.TextField(_("Notes"), blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Fueling")
        verbose_name_plural = _("Fuelings")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.vehicle.license_plate} — {self.date} {self.liters}L"


# ── MULTA ─────────────────────────────────────────────────────────────────────
class VehicleFine(models.Model):

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CONTESTED = "contested"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_PAID, _("Paid")),
        (STATUS_CONTESTED, _("Contested")),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="fines",
        verbose_name=_("Vehicle"),
    )
    driver = models.ForeignKey(
        "workforce.Collaborator",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fines",
        verbose_name=_("Driver"),
    )
    date = models.DateField(_("Offence Date"))
    location = models.CharField(_("Location"), max_length=200, blank=True, default="")
    offence_description = models.TextField(_("Offence Description"))
    amount = models.DecimalField(_("Amount (€)"), max_digits=14, decimal_places=4)
    points = models.PositiveSmallIntegerField(_("Penalty Points"), default=0)
    reference = models.CharField(_("Reference / PV No."), max_length=80, blank=True, default="")
    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    paid_date = models.DateField(_("Payment Date"), null=True, blank=True)
    deduct_from_payroll = models.BooleanField(_("Deduct from Payroll"), default=False)
    payroll_deducted = models.BooleanField(_("Payroll Deducted"), default=False)
    payroll_deducted_date = models.DateField(_("Payroll Deduction Date"), null=True, blank=True)
    file = models.FileField(_("File"), upload_to="fleet/fines/", null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Fine")
        verbose_name_plural = _("Fines")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.vehicle.license_plate} — {self.date} — €{self.amount}"


# ── DESPESA AVULSA ────────────────────────────────────────────────────────────
class VehicleExpense(models.Model):
    """Portagens (Viapass), parques, lavagens, taxas, pneus, etc."""

    TYPE_TOLL = "toll"
    TYPE_PARKING = "parking"
    TYPE_WASH = "wash"
    TYPE_TAX = "tax"
    TYPE_TYRE = "tyre"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_TOLL, _("Toll (Viapass / Telepass)")),
        (TYPE_PARKING, _("Parking")),
        (TYPE_WASH, _("Car Wash")),
        (TYPE_TAX, _("Tax / Fee")),
        (TYPE_TYRE, _("Tyre")),
        (TYPE_OTHER, _("Other")),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="expenses",
        verbose_name=_("Vehicle"),
    )
    expense_type = models.CharField(_("Type"), max_length=20, choices=TYPE_CHOICES)
    date = models.DateField(_("Date"))
    description = models.CharField(_("Description"), max_length=200, blank=True, default="")
    amount = models.DecimalField(_("Amount (€)"), max_digits=14, decimal_places=4)
    driver = models.ForeignKey(
        "workforce.Collaborator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_expenses",
        verbose_name=_("Driver"),
    )
    notes = models.TextField(_("Notes"), blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Vehicle Expense")
        verbose_name_plural = _("Vehicle Expenses")
        ordering = ["-date"]

    def __str__(self):
        return (
            f"{self.vehicle.license_plate} — {self.get_expense_type_display()}"
            f" {self.date} €{self.amount}"
        )
