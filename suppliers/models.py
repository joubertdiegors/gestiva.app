from django.db import models
from django.utils.translation import gettext_lazy as _


class Supplier(models.Model):

    class Category(models.TextChoices):
        PROFESSIONAL = 'professional', _('Professional')
        PRIVATE = 'private', _('Private')

    name = models.CharField(max_length=255, verbose_name=_('Legal name'))
    trade_name = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Trade name'))
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.PROFESSIONAL,
        verbose_name=_('Category'),
    )
    legal_form = models.ForeignKey(
        'workforce.LegalForm',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Legal form'),
        related_name='suppliers',
    )
    vat_number = models.CharField(max_length=50, blank=True, default='', verbose_name=_('VAT number'))
    vat_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name=_('VAT rate (%)'))
    responsible = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Account manager'))
    notes = models.TextField(blank=True, default='', verbose_name=_('Notes'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    class Meta:
        verbose_name = _('Supplier')
        verbose_name_plural = _('Suppliers')
        ordering = ['name']

    def __str__(self):
        return self.trade_name or self.name


class SupplierAddress(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name=_('Supplier'),
    )
    label = models.CharField(max_length=100, blank=True, default='', verbose_name=_('Label'))
    street = models.CharField(max_length=255, verbose_name=_('Street'))
    number = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Number'))
    complement = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Complement'))
    city = models.CharField(max_length=100, verbose_name=_('City'))
    postal_code = models.CharField(max_length=20, verbose_name=_('Postal code'))
    state = models.CharField(max_length=100, blank=True, default='', verbose_name=_('State'))
    country = models.CharField(max_length=100, default='Brazil', verbose_name=_('Country'))
    is_default = models.BooleanField(default=False, verbose_name=_('Primary address'))

    class Meta:
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')

    def __str__(self):
        return f'{self.supplier.name} - {self.city}'


class SupplierContact(models.Model):

    class ContactType(models.TextChoices):
        GENERAL = 'general', _('General')
        FINANCIAL = 'financial', _('Financial')
        COMMERCIAL = 'commercial', _('Commercial')

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='contacts',
        verbose_name=_('Supplier'),
    )
    contact_type = models.CharField(
        max_length=20,
        choices=ContactType.choices,
        default=ContactType.GENERAL,
        verbose_name=_('Contact type'),
    )
    name = models.CharField(max_length=255, verbose_name=_('Name'))
    phone = models.CharField(max_length=50, blank=True, default='', verbose_name=_('Phone'))
    email = models.EmailField(blank=True, default='', verbose_name=_('Email'))
    website = models.URLField(blank=True, default='', verbose_name=_('Website'))
    is_default = models.BooleanField(default=False, verbose_name=_('Primary contact'))

    class Meta:
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')

    def __str__(self):
        return f'{self.supplier.name} - {self.name}'
