from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone


# ── FORMA JURÍDICA ─────────────────────────────────────────────────────────────
class LegalForm(models.Model):
    name         = models.CharField(_("Name"), max_length=100, unique=True, db_index=True)
    abbreviation = models.CharField(_("Abbreviation"), max_length=20, blank=True, default='')
    notes        = models.TextField(_("Notes"), blank=True, default='')

    class Meta:
        verbose_name        = _("Legal Form")
        verbose_name_plural = _("Legal Forms")
        ordering            = ['name']

    def __str__(self):
        if self.abbreviation:
            return f"{self.abbreviation} — {self.name}"
        return self.name

    @property
    def display_name(self):
        return self.abbreviation or self.name


# ── NACIONALIDADE ──────────────────────────────────────────────────────────────
class Nationality(models.Model):
    name = models.CharField(_("Name"), max_length=100, unique=True, db_index=True)

    class Meta:
        verbose_name = _("Nationality")
        verbose_name_plural = _("Nationalities")
        ordering = ['name']

    def __str__(self):
        return self.name


# ── IDIOMA ─────────────────────────────────────────────────────────────────────
class Language(models.Model):
    name = models.CharField(_("Name"), max_length=100, unique=True, db_index=True)

    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")
        ordering = ['name']

    def __str__(self):
        return self.name


# ── CAISSE D'ASSURANCE ─────────────────────────────────────────────────────────
class InsuranceFund(models.Model):

    name    = models.CharField(_("Name"), max_length=255)
    phone   = models.CharField(_("Phone"), max_length=30, blank=True, null=True)
    email   = models.EmailField(_("Email"), blank=True, null=True)
    address = models.TextField(_("Address"), blank=True, null=True)
    notes   = models.TextField(_("Notes"), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Insurance Fund")
        verbose_name_plural = _("Insurance Funds")
        ordering = ['name']

    def __str__(self):
        return self.name


# ── CONTATOS DA CAISSE ─────────────────────────────────────────────────────────
class InsuranceFundContact(models.Model):

    fund  = models.ForeignKey(InsuranceFund, on_delete=models.CASCADE, related_name='contacts')
    name  = models.CharField(_("Name"), max_length=255)
    role  = models.CharField(_("Role"), max_length=100, blank=True, null=True)
    phone = models.CharField(_("Phone"), max_length=30, blank=True, null=True)
    email = models.EmailField(_("Email"), blank=True, null=True)
    notes = models.TextField(_("Notes"), blank=True, null=True)

    class Meta:
        verbose_name = _("Insurance Fund Contact")
        verbose_name_plural = _("Insurance Fund Contacts")

    def __str__(self):
        return f"{self.name} ({self.fund.name})"


# ── COLABORADOR ────────────────────────────────────────────────────────────────
class Collaborator(models.Model):

    STATUS_CHOICES = [
        ('active',   _('Active')),
        ('inactive', _('Inactive')),
    ]

    company = models.ForeignKey(
        'subcontractors.Subcontractor',
        verbose_name=_("Company"),
        on_delete=models.PROTECT,
        related_name='collaborators',
    )

    insurance_fund = models.ForeignKey(
        InsuranceFund,
        verbose_name=_("Insurance Fund"),
        on_delete=models.PROTECT,
        related_name='collaborators',
        db_index=True,
        blank=True, null=True,
    )

    # Identificação
    name       = models.CharField(_("Name"), max_length=255, db_index=True)
    role       = models.CharField(_("Role"), max_length=100, blank=True, null=True)
    photo      = models.ImageField(_("Photo"), upload_to='workforce/photos/', blank=True, null=True)
    id_number  = models.CharField(_("ID Number"), max_length=50, blank=True, null=True)
    id_expiry  = models.DateField(_("ID Expiry Date"), blank=True, null=True)
    birth_date = models.DateField(_("Birth Date"), blank=True, null=True)

    # Nacionalidade / Idiomas (M2M)
    nationalities = models.ManyToManyField(
        Nationality, verbose_name=_("Nationalities"), blank=True, related_name='collaborators'
    )
    languages = models.ManyToManyField(
        Language, verbose_name=_("Languages"), blank=True, related_name='collaborators'
    )

    # Contactos
    phone  = models.CharField(_("Phone"),   max_length=30, blank=True, null=True)
    phone2 = models.CharField(_("Phone 2"), max_length=30, blank=True, null=True)
    email  = models.EmailField(_("Email"),  blank=True, null=True)
    email2 = models.EmailField(_("Email 2"), blank=True, null=True)

    # Período de actividade
    entry_date = models.DateField(_("Entry Date"), blank=True, null=True)
    exit_date  = models.DateField(_("Exit Date"),  blank=True, null=True)

    status = models.CharField(
        _("Status"), max_length=20,
        choices=STATUS_CHOICES, default='active', db_index=True,
    )

    notes = models.TextField(_("Notes"), blank=True, null=True)

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Collaborator")
        verbose_name_plural = _("Collaborators")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if not update_fields and self.exit_date and self.status == 'active':
            self.status = 'inactive'
        super().save(*args, **kwargs)

    def get_current_hourly_rate(self):
        return self.hourly_rates.filter(end_date__isnull=True).first()

    def hourly_rate_amount_on_date(self, d):
        best = None
        for r in self.hourly_rates.all():
            if r.start_date > d:
                continue
            if r.end_date is not None and r.end_date < d:
                continue
            if best is None or r.start_date > best.start_date:
                best = r
        return best.hourly_rate if best else None

    def set_new_hourly_rate(self, hourly_rate, start_date):
        from datetime import timedelta
        current = self.hourly_rates.filter(end_date__isnull=True).first()
        if current:
            current.end_date = start_date - timedelta(days=1)
            current.save()
        CollaboratorHourlyRate.objects.create(
            collaborator=self, hourly_rate=hourly_rate, start_date=start_date,
        )

    def get_current_insurance_note(self):
        return self.insurance_notes.filter(resolved_at__isnull=True).order_by('-created_at').first()


# ── HISTÓRICO DE VALOR DA HORA ─────────────────────────────────────────────────
class CollaboratorHourlyRate(models.Model):

    collaborator = models.ForeignKey(Collaborator, on_delete=models.CASCADE, related_name='hourly_rates')
    hourly_rate  = models.DecimalField(_("Hourly Rate"), max_digits=10, decimal_places=2)
    start_date   = models.DateField(_("Start Date"))
    end_date     = models.DateField(_("End Date"), blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Hourly Rate")
        verbose_name_plural = _("Hourly Rates")
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.collaborator.name} - {self.hourly_rate} ({self.start_date})"

    def clean(self):
        overlapping = CollaboratorHourlyRate.objects.filter(
            collaborator=self.collaborator
        ).exclude(pk=self.pk)
        for rate in overlapping:
            if not self.end_date or not rate.end_date:
                raise ValidationError(_("There is already an active hourly rate."))
            if self.start_date <= rate.end_date and (
                self.end_date is None or self.end_date >= rate.start_date
            ):
                raise ValidationError(_("Overlapping hourly rate periods are not allowed."))


# ── HISTÓRICO DE ENDEREÇOS ─────────────────────────────────────────────────────
class CollaboratorAddress(models.Model):

    collaborator = models.ForeignKey(Collaborator, on_delete=models.CASCADE, related_name='addresses')
    street       = models.CharField(_("Street"), max_length=255)
    number       = models.CharField(_("Number"), max_length=20, blank=True, null=True)
    complement   = models.CharField(_("Complement"), max_length=100, blank=True, null=True)
    city         = models.CharField(_("City"), max_length=100)
    postal_code  = models.CharField(_("Postal Code"), max_length=20)
    state        = models.CharField(_("State/Region"), max_length=100, blank=True, null=True)
    country      = models.CharField(_("Country"), max_length=100, default="Belgium")
    valid_from   = models.DateField(_("Valid From"), default=timezone.now)
    valid_until  = models.DateField(_("Valid Until"), blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Collaborator Address")
        verbose_name_plural = _("Collaborator Addresses")
        ordering = ['-valid_from']

    def __str__(self):
        return f"{self.street}, {self.city} ({self.collaborator.name})"

    @property
    def is_current(self):
        return self.valid_until is None

    @property
    def full_address(self):
        parts = [self.street]
        if self.number:
            parts[0] += f', {self.number}'
        if self.complement:
            parts[0] += f' — {self.complement}'
        parts.append(f'{self.postal_code} {self.city}')
        if self.state:
            parts.append(self.state)
        if self.country and self.country != 'Belgium':
            parts.append(self.country)
        return ', '.join(parts)


# ── CARTA DE CONDUÇÃO ─────────────────────────────────────────────────────────
class DriverLicense(models.Model):
    """Carta de condução belga do colaborador (categorias AM→DE)."""

    collaborator = models.OneToOneField(
        Collaborator,
        on_delete=models.CASCADE,
        related_name='driver_license',
        verbose_name=_("Collaborator"),
    )
    license_number = models.CharField(_("License Number"), max_length=50, blank=True, default='')
    # Categorias separadas por vírgula: B,BE,C,CE …
    categories = models.CharField(
        _("Categories"),
        max_length=100,
        blank=True,
        default='',
        help_text=_("Comma-separated BE categories, e.g. B,BE,C"),
    )
    issue_date = models.DateField(_("Issue Date"), null=True, blank=True)
    expiry_date = models.DateField(_("Expiry Date"), null=True, blank=True)
    issuing_municipality = models.CharField(
        _("Issuing Municipality"), max_length=120, blank=True, default=''
    )
    scan = models.FileField(
        _("Scan"), upload_to='workforce/licenses/', null=True, blank=True
    )

    # ── Veículo em casa ────────────────────────────────────────────────────────
    takes_vehicle_home = models.BooleanField(
        _("Takes vehicle home"), default=False,
        help_text=_("Does the collaborator take a company vehicle home?"),
    )
    private_use_authorized = models.BooleanField(
        _("Private use authorized"), default=False,
        help_text=_("Is the collaborator authorized to use the vehicle for private purposes?"),
    )

    # ── Estacionamento ─────────────────────────────────────────────────────────
    has_garage = models.BooleanField(
        _("Has garage at home"), default=False,
    )
    has_fixed_parking = models.BooleanField(
        _("Has fixed parking space"), default=False,
    )
    needs_parking_card = models.BooleanField(
        _("Needs annual parking card"), default=False,
    )
    parking_paid_by_company = models.BooleanField(
        _("Parking paid by company"), default=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Driver License")
        verbose_name_plural = _("Driver Licenses")

    def __str__(self):
        return f"{self.collaborator} — {self.categories or '—'}"

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    def has_category(self, category):
        cats = [c.strip().upper() for c in self.categories.split(',') if c.strip()]
        return category.upper() in cats


# ── ESTACIONAMENTO ANUAL (histórico) ──────────────────────────────────────────
class ParkingPermit(models.Model):
    """Histórico de inscrições/renovações de cartão de estacionamento anual."""

    driver_license = models.ForeignKey(
        DriverLicense,
        on_delete=models.CASCADE,
        related_name='parking_permits',
        verbose_name=_("Driver License"),
    )
    registration_date = models.DateField(_("Registration Date"))
    expiry_date = models.DateField(_("Expiry Date"), null=True, blank=True)
    amount = models.DecimalField(
        _("Amount (€)"), max_digits=14, decimal_places=4, null=True, blank=True
    )
    notes = models.TextField(_("Notes"), blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Parking Permit")
        verbose_name_plural = _("Parking Permits")
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.driver_license.collaborator.name} — {self.registration_date}"

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False


# ── NOTAS DE SEGURO (histórico com switch de bloqueio) ─────────────────────────
class CollaboratorInsuranceNote(models.Model):

    collaborator      = models.ForeignKey(Collaborator, on_delete=models.CASCADE, related_name='insurance_notes')
    insurance_fund    = models.ForeignKey(InsuranceFund, on_delete=models.SET_NULL, null=True, blank=True, related_name='collab_notes')
    update_date       = models.DateField(_("Update Date"), default=timezone.now)
    note              = models.TextField(_("Note"), blank=True, null=True)
    # switch: bloqueia o trabalhador de trabalhar
    is_blocked        = models.BooleanField(_("Blocked"), default=False)
    # quando a pendência foi resolvida (null = ainda pendente)
    resolved_at       = models.DateField(_("Resolved At"), blank=True, null=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    created_by        = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='insurance_notes_created',
    )

    class Meta:
        verbose_name = _("Insurance Note")
        verbose_name_plural = _("Insurance Notes")
        ordering = ['-update_date', '-created_at']

    def __str__(self):
        status = "BLOQUEADO" if self.is_blocked else "ok"
        return f"{self.collaborator.name} [{status}] {self.update_date}"

    @property
    def is_pending(self):
        return self.resolved_at is None
