from django.db import models
from django.utils.translation import gettext_lazy as _


class Client(models.Model):

    CATEGORY_CHOICES = [
        ('private', _('Privé')),
        ('professional', _('Professionnel')),
    ]

    # Cadastro base
    name = models.CharField(max_length=255, verbose_name=_("Raison sociale"))
    trade_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Nom commercial"))

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='professional',
        verbose_name=_("Catégorie")
    )

    legal_form = models.ForeignKey(
        'workforce.LegalForm',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Forme juridique"),
        related_name='clients',
    )

    vat_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("TVA"))
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_("Taxe TVA (%)"))

    responsible = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Responsable"))

    notes = models.TextField(blank=True, null=True, verbose_name=_("Informations"))

    is_active = models.BooleanField(default=True, verbose_name=_("Actif"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Créé le"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Mis à jour le"))

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")

    def __str__(self):
        return self.name


class ClientAddress(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name=_("Client")
    )

    label = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Libellé"))

    street = models.CharField(max_length=255, verbose_name=_("Rue"))
    number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Numéro"))
    complement = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Complément"))

    city = models.CharField(max_length=100, verbose_name=_("Ville"))
    postal_code = models.CharField(max_length=20, verbose_name=_("Code postal"))
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Région"))
    country = models.CharField(max_length=100, default="Belgium", verbose_name=_("Pays"))

    is_default = models.BooleanField(default=False, verbose_name=_("Adresse par défaut"))

    class Meta:
        verbose_name = _("Adresse")
        verbose_name_plural = _("Adresses")

    def __str__(self):
        return f"{self.client.name} - {self.city}"


class ClientContact(models.Model):

    CONTACT_TYPE_CHOICES = [
        ('general', _('Général')),
        ('financial', _('Finance')),
        ('commercial', _('Commercial')),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='contacts',
        verbose_name=_("Client")
    )

    contact_type = models.CharField(
        max_length=20,
        choices=CONTACT_TYPE_CHOICES,
        default='general',
        verbose_name=_("Type de contact")
    )

    name = models.CharField(max_length=255, verbose_name=_("Nom"))
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Téléphone"))
    email = models.EmailField(blank=True, null=True, verbose_name=_("Email"))
    website = models.URLField(blank=True, null=True, verbose_name=_("Site web"))

    is_default = models.BooleanField(default=False, verbose_name=_("Contact principal"))

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")

    def __str__(self):
        return f"{self.client.name} - {self.name}"
