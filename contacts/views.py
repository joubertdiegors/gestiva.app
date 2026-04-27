from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _

from clients.models import ClientContact
from suppliers.models import SupplierContact
from workforce.models import Collaborator


@login_required
def contacts_list(request):
    source = request.GET.get('source', 'all')

    rows = []

    if source in ('all', 'clients'):
        for c in ClientContact.objects.select_related('client').order_by('client__name', 'name'):
            rows.append({
                'source':            'clients',
                'source_label':      _('Cliente'),
                'entity_name':       c.client.name,
                'entity_url':        f'/clients/{c.client.pk}/',
                'name':              c.name,
                'contact_type':      c.contact_type,
                'contact_type_label': c.get_contact_type_display(),
                'phone':             c.phone or '',
                'email':             c.email or '',
                'website':           c.website or '',
                'is_default':        c.is_default,
            })

    if source in ('all', 'suppliers'):
        for c in SupplierContact.objects.select_related('supplier').order_by('supplier__name', 'name'):
            rows.append({
                'source':            'suppliers',
                'source_label':      _('Fornecedor'),
                'entity_name':       c.supplier.name,
                'entity_url':        f'/suppliers/{c.supplier.pk}/',
                'name':              c.name,
                'contact_type':      c.contact_type,
                'contact_type_label': c.get_contact_type_display(),
                'phone':             c.phone or '',
                'email':             c.email or '',
                'website':           c.website or '',
                'is_default':        c.is_default,
            })

    if source in ('all', 'subcontractors'):
        # Equipe (colaboradores) do subcontratado — substitui contactos duplicados
        for c in Collaborator.objects.select_related('company').order_by('company__name', 'name'):
            rows.append({
                'source':             'subcontractors',
                'source_label':       _('Subcontratado'),
                'entity_name':        c.company.name,
                'entity_url':         f'/subcontractors/{c.company.pk}/',
                'name':               c.name,
                'contact_type':       c.status,
                'contact_type_label': c.role or c.get_status_display(),
                'phone':              c.phone or '',
                'email':              c.email or '',
                'website':            '',
                'is_default':         False,
            })

    rows.sort(key=lambda r: (r['entity_name'].lower(), r['name'].lower()))

    return render(request, 'contacts/contacts_list.html', {
        'rows':   rows,
        'source': source,
    })
