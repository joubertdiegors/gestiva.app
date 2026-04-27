from django.db import models
from django.utils.translation import gettext_lazy as _


class Client(models.Model):

    CATEGORY_CHOICES = [
        ('private', _('Private')),
        ('professional', _('Professional')),
    ]

    name = models.CharField(max_length=255, verbose_name=_('Legal name'))
    trade_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Trade name'))

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='professional',
        verbose_name=_('Category'),
    )

    legal_form = models.ForeignKey(
        'workforce.LegalForm',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Legal form'),
        related_name='clients',
    )

    vat_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('VAT number'))
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('VAT rate (%)'))

    responsible = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Account manager'))

    notes = models.TextField(blank=True, null=True, verbose_name=_('Notes'))

    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    class Meta:
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')

    def __str__(self):
        return self.name


class ClientAddress(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name=_('Client'),
    )

    label = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Label'))

    street = models.CharField(max_length=255, verbose_name=_('Street'))
    number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Number'))
    complement = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Complement'))

    city = models.CharField(max_length=100, verbose_name=_('City'))
    postal_code = models.CharField(max_length=20, verbose_name=_('Postal code'))
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('State'))
    country = models.CharField(max_length=100, default='Brazil', verbose_name=_('Country'))

    is_default = models.BooleanField(default=False, verbose_name=_('Primary address'))

    class Meta:
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')

    def __str__(self):
        return f'{self.client.name} - {self.city}'


class ClientContact(models.Model):

    CONTACT_TYPE_CHOICES = [
        ('general', _('General')),
        ('financial', _('Financial')),
        ('commercial', _('Commercial')),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='contacts',
        verbose_name=_('Client'),
    )

    contact_type = models.CharField(
        max_length=20,
        choices=CONTACT_TYPE_CHOICES,
        default='general',
        verbose_name=_('Contact type'),
    )

    name = models.CharField(max_length=255, verbose_name=_('Name'))
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Phone'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('Email'))
    website = models.URLField(blank=True, null=True, verbose_name=_('Website'))

    is_default = models.BooleanField(default=False, verbose_name=_('Primary contact'))

    class Meta:
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')

    def __str__(self):
        return f'{self.client.name} - {self.name}'
