from django.db import models
from django.utils.translation import gettext_lazy as _


class Subcontractor(models.Model):

    CATEGORY_CHOICES = [
        ('professional', _('Professional')),
        ('private', _('Private')),
    ]

    STATUS_CHOICES = [
        ('active',  _('Active')),
        ('paused',  _('Paused')),
        ('blocked', _('Blocked')),
    ]

    name = models.CharField(_("Name"), max_length=255, db_index=True)
    trade_name = models.CharField(_("Trade Name"), max_length=255, blank=True, null=True)

    category = models.CharField(
        _("Category"), max_length=20,
        choices=CATEGORY_CHOICES, default='professional'
    )

    vat_number = models.CharField(_("VAT Number"), max_length=50, blank=True, null=False)

    legal_form = models.ForeignKey(
        'workforce.LegalForm',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Legal Form"),
        related_name='subcontractors',
    )

    vat_rate = models.DecimalField(
        _("VAT Rate (%)"), max_digits=5, decimal_places=2, default=0
    )

    responsible = models.CharField(_("Responsible"), max_length=255, blank=True, null=True)

    status = models.CharField(
        _("Status"), max_length=20,
        choices=STATUS_CHOICES, default='active'
    )

    notes = models.TextField(_("Notes"), blank=True, null=True)

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Subcontractor")
        verbose_name_plural = _("Subcontractors")
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['vat_number'],
                name='unique_vat_number',
                condition=~models.Q(vat_number="")
            )
        ]

    def __str__(self):
        return self.name


class SubcontractorAddress(models.Model):
    subcontractor = models.ForeignKey(
        Subcontractor, on_delete=models.CASCADE,
        related_name='addresses', verbose_name=_("Subcontractor")
    )
    label       = models.CharField(_("Label"), max_length=100, blank=True, null=True)
    street      = models.CharField(_("Street"), max_length=255)
    number      = models.CharField(_("Number"), max_length=50, blank=True, null=True)
    complement  = models.CharField(_("Complement"), max_length=255, blank=True, null=True)
    city        = models.CharField(_("City"), max_length=100)
    postal_code = models.CharField(_("Postal Code"), max_length=20)
    state       = models.CharField(_("State"), max_length=100, blank=True, null=True)
    country = models.CharField(_('Country'), max_length=100, default='Brazil')
    is_default = models.BooleanField(_('Primary address'), default=False)

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    def __str__(self):
        return f"{self.subcontractor.name} - {self.city}"


class SubcontractorContact(models.Model):

    CONTACT_TYPE_CHOICES = [
        ('general', _('General')),
        ('financial', _('Financial')),
        ('commercial', _('Commercial')),
    ]

    subcontractor = models.ForeignKey(
        Subcontractor, on_delete=models.CASCADE,
        related_name='contacts', verbose_name=_("Subcontractor")
    )
    contact_type = models.CharField(
        _("Contact Type"), max_length=20,
        choices=CONTACT_TYPE_CHOICES, default='general'
    )
    name       = models.CharField(_("Name"), max_length=255)
    phone      = models.CharField(_("Phone"), max_length=50, blank=True, null=True)
    email      = models.EmailField(_("Email"), blank=True, null=True)
    website    = models.URLField(_("Website"), blank=True, null=True)
    is_default = models.BooleanField(_('Primary contact'), default=False)

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")

    def __str__(self):
        return f"{self.subcontractor.name} - {self.name}"
