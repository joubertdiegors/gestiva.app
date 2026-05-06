from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DocumentTemplate(models.Model):
    """Reusable document template with HTML sections and variable placeholders."""

    # ── Document types ────────────────────────────────────────────────────────
    TYPE_QUOTE           = 'quote'
    TYPE_INVOICE         = 'invoice'
    TYPE_CONTRACT        = 'contract'
    TYPE_ADDENDUM        = 'addendum'
    TYPE_STATEMENT       = 'statement'
    TYPE_SUPPLIER_ORDER  = 'supplier_order'
    TYPE_SUB_ORDER       = 'sub_order'
    TYPE_CREDIT_NOTE     = 'credit_note'
    TYPE_OTHER           = 'other'

    TYPE_CHOICES = [
        (TYPE_QUOTE,          _('Quote')),
        (TYPE_INVOICE,        _('Invoice')),
        (TYPE_CONTRACT,       _('Client Contract')),
        (TYPE_ADDENDUM,       _('Addendum')),
        (TYPE_STATEMENT,      _('Progress Statement (EA)')),
        (TYPE_SUPPLIER_ORDER, _('Supplier Purchase Order')),
        (TYPE_SUB_ORDER,      _('Subcontractor Order')),
        (TYPE_CREDIT_NOTE,    _('Credit Note')),
        (TYPE_OTHER,          _('Other')),
    ]

    # ── Status ────────────────────────────────────────────────────────────────
    STATUS_ACTIVE   = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES  = [
        (STATUS_ACTIVE,   _('Active')),
        (STATUS_INACTIVE, _('Inactive')),
    ]

    # ── Core fields ───────────────────────────────────────────────────────────
    name          = models.CharField(_('Name'), max_length=200)
    document_type = models.CharField(_('Document type'), max_length=30, choices=TYPE_CHOICES)
    status        = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    is_system     = models.BooleanField(_('System template (non-editable)'), default=False)
    is_default    = models.BooleanField(_('Default for this type'), default=False)

    # ── HTML sections (each edited independently) ─────────────────────────────
    # Repeats on every page (header/footer bands in PDF)
    section_page_header = models.TextField(_('Page header (repeated)'), blank=True, default='')
    section_page_footer = models.TextField(_('Page footer (repeated)'), blank=True, default='')

    # Document-level sections
    section_header_generic  = models.TextField(_('Generic header (logo + parties)'), blank=True, default='')
    section_header_document = models.TextField(_('Document header (intro text)'), blank=True, default='')
    # Lines table is generated dynamically — only CSS/column config stored
    section_lines_config    = models.JSONField(_('Lines table config'), default=dict, blank=True)
    section_footer_document = models.TextField(_('Document footer (totals, conditions, signatures)'), blank=True, default='')

    # ── Styling ───────────────────────────────────────────────────────────────
    custom_css = models.TextField(_('Custom CSS'), blank=True, default='')

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Created by'),
        on_delete=models.PROTECT,
        related_name='doc_templates_created',
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Document Template')
        verbose_name_plural = _('Document Templates')
        ordering            = ['document_type', 'name']

    def __str__(self):
        return f'{self.get_document_type_display()} — {self.name}'

    def save(self, *args, **kwargs):
        # Ensure only one default per type
        if self.is_default:
            DocumentTemplate.objects.filter(
                document_type=self.document_type,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


# ── Variable registry ─────────────────────────────────────────────────────────

VARIABLES = {
    'document': [
        ('numDocument',     _('Document number')),
        ('dateCreation',    _('Creation date')),
        ('dateRevision',    _('Revision date')),
        ('validiteOffre',   _('Offer validity date')),
        ('conditionsReglement', _('Payment conditions')),
        ('acompte',         _('Deposit amount')),
        ('estAvenant',      _('Is addendum?')),
        ('numPage',         _('Page number')),
        ('nombrePages',     _('Total pages')),
        ('blocTotauxAvecTVA',  _('Totals block (with VAT)')),
        ('blocTotauxSansTVA',  _('Totals block (without VAT)')),
    ],
    'company': [
        ('nomEntreprise',   _('Company name')),
        ('adresseEntreprise', _('Company address')),
        ('CPEntreprise',    _('Company postal code')),
        ('villeEntreprise', _('Company city')),
        ('telEntreprise',   _('Company phone')),
        ('emailEntreprise', _('Company email')),
        ('numTVA',          _('Company VAT number')),
        ('statusJuridique', _('Legal status')),
        ('logoEntreprise',  _('Company logo')),
    ],
    'client': [
        ('nomTiers',        _('Client name')),
        ('civilite',        _('Civility')),
        ('nomComTiers',     _('Commercial contact name')),
        ('civiliteTiers',   _('Contact civility')),
        ('adresseTiers',    _('Client address')),
        ('CPTiers',         _('Client postal code')),
        ('villeTiers',      _('Client city')),
        ('numTVATiers',     _('Client VAT number')),
        ('emailTiers',      _('Client email')),
        ('telTiers',        _('Client phone')),
    ],
    'project': [
        ('nomChantier',     _('Project name')),
        ('adresseChantier', _('Project address')),
        ('CPChantier',      _('Project postal code')),
        ('villeChantier',   _('Project city')),
        ('refChantier',     _('Project reference')),
        ('chefProjet',      _('Project manager')),
    ],
    'other': [
        ('assurance',       _('General terms')),
        ('commentaireDechets', _('Waste comment')),
        ('coutDechets',     _('Waste cost')),
    ],
}
