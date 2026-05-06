import json
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from accounts.decorators import perm_required
from .models import Client, ClientAddress, ClientContact
from .forms import ClientForm, ClientAddressForm, ClientContactForm


# ── List / Create / Update / Detail ─────────────────────────────────────────

@perm_required('clients.view_client')
def client_list(request):
    qs = Client.objects.prefetch_related('addresses', 'contacts').order_by('name')
    q = request.GET.get('q', '').strip()
    is_active = request.GET.get('is_active', '')
    if q:
        qs = qs.filter(name__icontains=q)
    if is_active == 'active':
        qs = qs.filter(is_active=True)
    elif is_active == 'inactive':
        qs = qs.filter(is_active=False)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'clients/client_list.html', {
        'clients': page,
        'page_obj': page,
        'q': q,
        'is_active': is_active,
    })


@perm_required('clients.add_client')
def client_create(request):
    form = ClientForm(request.POST or None)
    if form.is_valid():
        client = form.save()
        return redirect('clients:detail', pk=client.pk)
    return render(request, 'clients/client_form.html', {
        'form': form,
        'title': _("Novo cliente"),
    })


@perm_required('clients.change_client')
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=client)
    if form.is_valid():
        form.save()
        return redirect('clients:detail', pk=client.pk)
    return render(request, 'clients/client_form.html', {
        'form': form,
        'title': client.name,
        'client': client,
    })


@perm_required('clients.view_client')
def client_detail(request, pk):
    client = get_object_or_404(
        Client.objects.prefetch_related('addresses', 'contacts', 'projects'), pk=pk
    )
    return render(request, 'clients/client_detail.html', {'client': client})


# ── Address AJAX endpoints ───────────────────────────────────────────────────

@perm_required('clients.change_client')
@require_POST
def address_save(request, client_pk, pk=None):
    client = get_object_or_404(Client, pk=client_pk)
    instance = get_object_or_404(ClientAddress, pk=pk, client=client) if pk else None
    form = ClientAddressForm(request.POST, instance=instance)
    if form.is_valid():
        addr = form.save(commit=False)
        addr.client = client
        addr.save()
        return JsonResponse({
            'ok': True,
            'address': _address_to_dict(addr),
            'update_url': reverse(
                'clients:address_update',
                kwargs={'client_pk': client.pk, 'pk': addr.pk},
            ),
            'delete_url': reverse(
                'clients:address_delete',
                kwargs={'client_pk': client.pk, 'pk': addr.pk},
            ),
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@perm_required('clients.change_client')
@require_POST
def address_delete(request, client_pk, pk):
    addr = get_object_or_404(ClientAddress, pk=pk, client_id=client_pk)
    addr.delete()
    return JsonResponse({'ok': True})


# ── Contact AJAX endpoints ───────────────────────────────────────────────────

@perm_required('clients.change_client')
@require_POST
def contact_save(request, client_pk, pk=None):
    client = get_object_or_404(Client, pk=client_pk)
    instance = get_object_or_404(ClientContact, pk=pk, client=client) if pk else None
    form = ClientContactForm(request.POST, instance=instance)
    if form.is_valid():
        contact = form.save(commit=False)
        contact.client = client
        contact.save()
        return JsonResponse({
            'ok': True,
            'contact': _contact_to_dict(contact),
            'update_url': reverse(
                'clients:contact_update',
                kwargs={'client_pk': client.pk, 'pk': contact.pk},
            ),
            'delete_url': reverse(
                'clients:contact_delete',
                kwargs={'client_pk': client.pk, 'pk': contact.pk},
            ),
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@perm_required('clients.change_client')
@require_POST
def contact_delete(request, client_pk, pk):
    contact = get_object_or_404(ClientContact, pk=pk, client_id=client_pk)
    contact.delete()
    return JsonResponse({'ok': True})


# ── Serializers ──────────────────────────────────────────────────────────────

def _address_to_dict(addr):
    parts = [addr.street]
    if addr.number:
        parts[0] += f', {addr.number}'
    if addr.complement:
        parts.append(addr.complement)
    full = ' — '.join(parts)
    return {
        'id':         addr.pk,
        'label':      addr.label or '',
        'street':     addr.street,
        'number':     addr.number or '',
        'complement': addr.complement or '',
        'city':       addr.city,
        'postal_code': addr.postal_code,
        'state':      addr.state or '',
        'country':    addr.country,
        'is_default': addr.is_default,
        'full':       f'{full} — {addr.postal_code} {addr.city}',
    }


def _contact_to_dict(contact):
    return {
        'id':           contact.pk,
        'name':         contact.name,
        'contact_type': contact.contact_type,
        'contact_type_display': contact.get_contact_type_display(),
        'phone':        contact.phone or '',
        'email':        contact.email or '',
        'website':      contact.website or '',
        'is_default':   contact.is_default,
    }
