import uuid
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class WorkRegistrationType(models.Model):
    name = models.CharField(_("Name"), max_length=100)

    class Meta:
        verbose_name = _("Work Registration Type")
        verbose_name_plural = _("Work Registration Types")

    def __str__(self):
        return self.name


class Project(models.Model):

    class Status(models.TextChoices):
        PLANNING = 'planning', _('Planning')
        ACTIVE   = 'active',   _('Active')
        PAUSED   = 'paused',   _('Paused')
        FINISHED = 'finished', _('Finished')

    external_id = models.UUIDField(
        _('External ID'), default=uuid.uuid4, editable=False, unique=True,
    )
    name = models.CharField(_("Name"), max_length=255)

    client = models.ForeignKey(
        'clients.Client',
        verbose_name=_("Client"),
        on_delete=models.PROTECT,
        related_name='projects'
    )

    contacts = models.ManyToManyField(
        'clients.ClientContact',
        verbose_name=_("Contacts"),
        related_name='projects',
        blank=True
    )

    # ── Address (structured) ──────────────────────────────────────────────────
    address_street     = models.CharField(_("Street"), max_length=255, blank=True, default='')
    address_number     = models.CharField(_("Number"), max_length=20, blank=True, default='')
    address_complement = models.CharField(_("Complement"), max_length=100, blank=True, default='')
    address_postcode   = models.CharField(_("Postcode"), max_length=20, blank=True, default='')
    address_city       = models.CharField(_("City"), max_length=100, blank=True, default='')
    address_country    = models.CharField(_("Country"), max_length=100, blank=True, default='Bélgica')

    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Managers"),
        related_name='managed_projects',
        blank=True
    )

    start_date = models.DateField(_("Start date"), null=True, blank=True)
    end_date = models.DateField(_("End date"), null=True, blank=True)

    notes = models.TextField(_("Notes"), blank=True, null=True)

    has_work_registration = models.BooleanField(
        _("Has work registration"),
        default=False
    )

    work_registration_type = models.ForeignKey(
        'projects.WorkRegistrationType',
        verbose_name=_("Registration type"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    work_registration_number = models.CharField(
        _("Registration number"),
        max_length=100,
        blank=True,
        null=True
    )

    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Created by"),
        on_delete=models.PROTECT,
        related_name='projects_created'
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Updated by"),
        on_delete=models.PROTECT,
        related_name='projects_updated',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def clean(self):
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({
                    'end_date': _("End date cannot be before start date.")
                })

        if self.has_work_registration:
            if not self.work_registration_type:
                raise ValidationError({
                    'work_registration_type': _("Select a registration type.")
                })
            if not self.work_registration_number:
                raise ValidationError({
                    'work_registration_number': _("Enter the registration number.")
                })
        else:
            self.work_registration_type = None
            self.work_registration_number = None

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['status']),
        ]

    @property
    def address(self):
        """Formatted single-line address for display compatibility."""
        parts = []
        if self.address_street:
            parts.append(self.address_street + (' ' + self.address_number if self.address_number else ''))
        if self.address_complement:
            parts.append(self.address_complement)
        if self.address_postcode or self.address_city:
            parts.append(' '.join(filter(None, [self.address_postcode, self.address_city])))
        if self.address_country:
            parts.append(self.address_country)
        return ', '.join(parts)

    def __str__(self):
        return self.name


# ── CIAW — Árvore de participantes ───────────────────────────────────────────

class ProjectCiawParticipant(models.Model):
    """
    Nó da árvore hierárquica CIAW de um projeto.
    Cada nó aponta para exatamente UMA das três entidades possíveis:
      • subcontractor  — empresa subempreiteira
      • worker         — trabalhador (pertence a um subempreiteiro)
    O nó raiz (parent=None, order=0) é sempre o cliente do projeto
    (gerado automaticamente). O segundo nível fixo é a própria Construart.
    """

    TYPE_CLIENT        = 'client'
    TYPE_CONSTRUART    = 'construart'
    TYPE_SUBCONTRACTOR = 'subcontractor'
    TYPE_WORKER        = 'worker'

    TYPE_CHOICES = [
        (TYPE_CLIENT,        _('Client (project owner)')),
        (TYPE_CONSTRUART,    _('Construart')),
        (TYPE_SUBCONTRACTOR, _('Subcontractor')),
        (TYPE_WORKER,        _('Worker')),
    ]

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='ciaw_participants',
        verbose_name=_('Project'),
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='children',
        verbose_name=_('Parent node'),
    )
    node_type = models.CharField(
        _('Type'), max_length=20, choices=TYPE_CHOICES,
    )
    # Exatamente um destes campos será preenchido (excepto para client/construart)
    subcontractor = models.ForeignKey(
        'subcontractors.Subcontractor',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='ciaw_nodes',
        verbose_name=_('Subcontractor'),
    )
    worker = models.ForeignKey(
        'workforce.Collaborator',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='ciaw_nodes',
        verbose_name=_('Worker'),
    )
    order = models.PositiveSmallIntegerField(_('Order'), default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('CIAW Participant')
        verbose_name_plural = _('CIAW Participants')
        ordering = ['order', 'added_at']
        constraints = [
            # Coerência da árvore CIAW: cada nó preenche exactamente os
            # campos que o seu tipo exige. Nós 'client' e 'construart' são
            # sintéticos (sem FK); 'subcontractor' aponta para Subcontractor;
            # 'worker' aponta para Collaborator.
            models.CheckConstraint(
                name='ciaw_node_entity_xor',
                check=(
                    (
                        models.Q(node_type='client',
                                 subcontractor__isnull=True,
                                 worker__isnull=True)
                    ) | (
                        models.Q(node_type='construart',
                                 subcontractor__isnull=True,
                                 worker__isnull=True)
                    ) | (
                        models.Q(node_type='subcontractor',
                                 subcontractor__isnull=False,
                                 worker__isnull=True)
                    ) | (
                        models.Q(node_type='worker',
                                 subcontractor__isnull=True,
                                 worker__isnull=False)
                    )
                ),
            ),
        ]

    def __str__(self):
        if self.node_type == self.TYPE_CLIENT:
            return f'[Cliente] {self.project.client.name}'
        if self.node_type == self.TYPE_CONSTRUART:
            return '[Construart]'
        if self.node_type == self.TYPE_SUBCONTRACTOR and self.subcontractor:
            return self.subcontractor.name
        if self.node_type == self.TYPE_WORKER and self.worker:
            return self.worker.name
        return f'Node #{self.pk}'

    @property
    def label(self):
        return self.__str__()

    @property
    def entity_url(self):
        if self.node_type == self.TYPE_CLIENT:
            return f'/clients/{self.project.client_id}/'
        if self.node_type == self.TYPE_SUBCONTRACTOR and self.subcontractor_id:
            return f'/subcontractors/{self.subcontractor_id}/'
        if self.node_type == self.TYPE_WORKER and self.worker_id:
            return f'/workforce/{self.worker_id}/'
        return None


# ── MINI-CRM ──────────────────────────────────────────────────────────────────

class ProjectInteraction(models.Model):
    TYPE_MEETING = 'meeting'
    TYPE_EMAIL = 'email'
    TYPE_PHONE = 'phone'
    TYPE_VISIT = 'visit'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_MEETING, _('Meeting')),
        (TYPE_EMAIL,   _('Email')),
        (TYPE_PHONE,   _('Phone')),
        (TYPE_VISIT,   _('Site visit')),
        (TYPE_OTHER,   _('Other')),
    ]

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='interactions',
        verbose_name=_('Project'),
    )
    date = models.DateField(_('Date'))
    interaction_type = models.CharField(
        _('Type'), max_length=20, choices=TYPE_CHOICES, default=TYPE_OTHER,
    )
    subject = models.CharField(_('Subject'), max_length=255)
    body = models.TextField(_('Body'), blank=True, default='')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='project_interactions',
        verbose_name=_('Author'),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Project Interaction')
        verbose_name_plural = _('Project Interactions')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.project.name} — {self.get_interaction_type_display()} — {self.date}'


# ── TABELAS DE CUSTO ──────────────────────────────────────────────────────────

class ProjectSupplierInvoice(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_PAID,    _('Paid')),
    ]

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='supplier_invoices',
        verbose_name=_('Project'),
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.PROTECT,
        related_name='project_invoices',
        verbose_name=_('Supplier'),
    )
    invoice_ref = models.CharField(_('Invoice reference'), max_length=100, blank=True, default='')
    description = models.CharField(_('Description'), max_length=255, blank=True, default='')
    date = models.DateField(_('Date'))
    amount_ht = models.DecimalField(_('Amount excl. VAT (€)'), max_digits=14, decimal_places=4, default=Decimal('0'))
    vat_rate = models.DecimalField(_('VAT rate (%)'), max_digits=6, decimal_places=2, default=Decimal('21.00'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(_('Notes'), blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Supplier Invoice')
        verbose_name_plural = _('Supplier Invoices')
        ordering = ['-date']

    def __str__(self):
        return f'{self.project.name} — {self.supplier} — {self.invoice_ref or self.date}'

    @property
    def amount_ttc(self):
        return self.amount_ht * (1 + self.vat_rate / 100)


class ProjectMaterial(models.Model):
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name=_('Project'),
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='project_materials',
        verbose_name=_('Product'),
    )
    description = models.CharField(_('Description'), max_length=255, blank=True, default='')
    quantity = models.DecimalField(_('Quantity'), max_digits=12, decimal_places=4, default=Decimal('1'))
    unit = models.CharField(_('Unit'), max_length=30, blank=True, default='')
    unit_price = models.DecimalField(_('Unit price (€)'), max_digits=14, decimal_places=4, default=Decimal('0'))
    date = models.DateField(_('Date'), null=True, blank=True)
    notes = models.TextField(_('Notes'), blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Project Material')
        verbose_name_plural = _('Project Materials')
        ordering = ['-date', 'description']

    def __str__(self):
        label = self.product.name if self.product else self.description
        return f'{self.project.name} — {label}'

    @property
    def total(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        if self.product and not self.description:
            self.description = self.product.name
        if self.product and not self.unit and self.product.unit:
            self.unit = self.product.unit.symbol
        super().save(*args, **kwargs)


class ProjectLabourEntry(models.Model):
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='labour_entries',
        verbose_name=_('Project'),
    )
    worker = models.ForeignKey(
        'workforce.Collaborator',
        on_delete=models.PROTECT,
        related_name='project_labour_entries',
        verbose_name=_('Worker'),
    )
    timesheet = models.OneToOneField(
        'timesheets.Timesheet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='labour_entry',
        verbose_name=_('Timesheet'),
    )
    date = models.DateField(_('Date'))
    hours = models.DecimalField(_('Hours'), max_digits=6, decimal_places=2, default=Decimal('0'))
    hourly_rate = models.DecimalField(_('Hourly rate (€)'), max_digits=10, decimal_places=2, default=Decimal('0'))
    is_overtime = models.BooleanField(_('Overtime'), default=False)
    overtime_multiplier = models.DecimalField(
        _('Overtime multiplier'), max_digits=4, decimal_places=2, default=Decimal('1.50'),
    )
    notes = models.TextField(_('Notes'), blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Labour Entry')
        verbose_name_plural = _('Labour Entries')
        ordering = ['-date', 'worker__name']

    def __str__(self):
        return f'{self.project.name} — {self.worker.name} — {self.date}'

    @property
    def effective_rate(self):
        if self.is_overtime:
            return self.hourly_rate * self.overtime_multiplier
        return self.hourly_rate

    @property
    def total_cost(self):
        return self.hours * self.effective_rate