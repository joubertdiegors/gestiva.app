from django.db import models
from django.utils.translation import gettext_lazy as _


class Supplier(models.Model):

    class Category(models.TextChoices):
        PROFESSIONAL = 'professional', _('Professionnel')
        PRIVATE      = 'private',      _('Prive')

    name        = models.CharField(max_length=255, verbose_name=_("Raison sociale"))
    trade_name  = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Nom commercial"))
    category    = models.CharField(max_length=20, choices=Category.choices, default=Category.PROFESSIONAL, verbose_name=_("Categorie"))
    legal_form  = models.ForeignKey(
        'workforce.LegalForm',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Forme juridique"),
        related_name='suppliers',
    )
    vat_number  = models.CharField(max_length=50, blank=True, default='', verbose_name=_("Numero TVA"))
    vat_rate    = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name=_("Taux TVA (%)"))
    responsible = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Responsable"))
    notes       = models.TextField(blank=True, default='', verbose_name=_("Informations"))
    is_active   = models.BooleanField(default=True, verbose_name=_("Actif"))
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name=_("Cree le"))
    updated_at  = models.DateTimeField(auto_now=True, verbose_name=_("Mis a jour le"))

    class Meta:
        verbose_name        = _("Fournisseur")
        verbose_name_plural = _("Fournisseurs")
        ordering            = ['name']

    def __str__(self):
        return self.trade_name or self.name


class SupplierAddress(models.Model):
    supplier    = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='addresses', verbose_name=_("Fournisseur"))
    label       = models.CharField(max_length=100, blank=True, default='', verbose_name=_("Libelle"))
    street      = models.CharField(max_length=255, verbose_name=_("Rue"))
    number      = models.CharField(max_length=50, blank=True, default='', verbose_name=_("Numero"))
    complement  = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Complement"))
    city        = models.CharField(max_length=100, verbose_name=_("Ville"))
    postal_code = models.CharField(max_length=20, verbose_name=_("Code postal"))
    state       = models.CharField(max_length=100, blank=True, default='', verbose_name=_("Region"))
    country     = models.CharField(max_length=100, default='Belgium', verbose_name=_("Pays"))
    is_default  = models.BooleanField(default=False, verbose_name=_("Adresse par defaut"))

    class Meta:
        verbose_name        = _("Adresse")
        verbose_name_plural = _("Adresses")

    def __str__(self):
        return f"{self.supplier.name} - {self.city}"


class SupplierContact(models.Model):

    class ContactType(models.TextChoices):
        GENERAL    = 'general',    _('General')
        FINANCIAL  = 'financial',  _('Finance')
        COMMERCIAL = 'commercial', _('Commercial')

    supplier     = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='contacts', verbose_name=_("Fournisseur"))
    contact_type = models.CharField(max_length=20, choices=ContactType.choices, default=ContactType.GENERAL, verbose_name=_("Type"))
    name         = models.CharField(max_length=255, verbose_name=_("Nom"))
    phone        = models.CharField(max_length=50, blank=True, default='', verbose_name=_("Telephone"))
    email        = models.EmailField(blank=True, default='', verbose_name=_("Email"))
    website      = models.URLField(blank=True, default='', verbose_name=_("Site web"))
    is_default   = models.BooleanField(default=False, verbose_name=_("Contact principal"))

    class Meta:
        verbose_name        = _("Contact")
        verbose_name_plural = _("Contacts")

    def __str__(self):
        return f"{self.supplier.name} - {self.name}"
