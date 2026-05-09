import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from accounts.decorators import perm_required
from .models import Collaborator, CollaboratorAddress, CollaboratorInsuranceNote, InsuranceFund, InsuranceFundContact, Nationality, Language, LegalForm, DriverLicense, ParkingPermit
from .forms import (
    CollaboratorForm, CollaboratorHourlyRateCreateForm,
    CollaboratorAddressForm, CollaboratorInsuranceNoteForm,
    NationalityForm, LanguageForm,
    InsuranceFundForm, InsuranceFundContactForm,
    LegalFormForm, DriverLicenseForm, ParkingPermitForm,
)


def _safe_next_path(request, nxt):
    if not nxt or not nxt.startswith('/') or nxt.startswith('//'):
        return None
    if not url_has_allowed_host_and_scheme(url=nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return None
    return nxt


def _protected_workforce_upload_response(file_field):
    """
    Serve um ficheiro guardado em MEDIA_ROOT apenas se estiver sob pastas
    controladas (fotos de colaborador / scans da carta). Evita path traversal.
    """
    if file_field is None or not getattr(file_field, 'name', None):
        raise Http404()
    try:
        path = Path(file_field.path).resolve()
    except ValueError:
        raise Http404()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    try:
        rel = path.relative_to(media_root).as_posix()
    except ValueError:
        raise Http404()
    if not rel.startswith(('workforce/photos/', 'workforce/licenses/')):
        raise Http404()
    if not path.is_file():
        raise Http404()
    ctype, _ = mimetypes.guess_type(str(path))
    fh = path.open('rb')
    resp = FileResponse(fh, content_type=ctype or 'application/octet-stream')
    resp['Cache-Control'] = 'private, no-store'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp


# ── Lista ──────────────────────────────────────────────────────────────────────

@perm_required('workforce.view_collaborator')
def collaborator_list(request):
    qs = Collaborator.objects.select_related('company', 'insurance_fund').order_by('name')
    responsible = request.GET.get('responsible', '').strip()
    if responsible:
        qs = qs.filter(company__responsible__iexact=responsible)
    return render(request, 'workforce/collaborator_list.html', {
        'collaborators': qs,
        'filter_responsible': responsible,
    })


# ── Criar ──────────────────────────────────────────────────────────────────────

@perm_required('workforce.add_collaborator')
def collaborator_create(request):
    next_path  = _safe_next_path(request, (request.GET.get('next') or request.POST.get('next') or '').strip() or None)
    company_id = (request.GET.get('company') or request.POST.get('company') or '').strip()

    if request.method == 'GET' and company_id:
        form = CollaboratorForm(initial={'company': company_id})
    else:
        form = CollaboratorForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        form.save()
        if next_path:
            return redirect(next_path)
        return redirect('workforce:list')
    return render(request, 'workforce/collaborator_form.html', {
        'form': form, 'title': _('Novo colaborador'), 'redirect_next': next_path,
    })


# ── Detalhe ────────────────────────────────────────────────────────────────────

@perm_required('workforce.view_collaborator')
def collaborator_detail(request, pk):
    collaborator = get_object_or_404(
        Collaborator.objects.select_related('company', 'insurance_fund')
                            .prefetch_related('nationalities', 'languages'),
        pk=pk,
    )
    rates           = collaborator.hourly_rates.order_by('-start_date')
    addresses       = collaborator.addresses.order_by('-valid_from')
    insurance_notes = collaborator.insurance_notes.select_related('insurance_fund', 'created_by').order_by('-update_date', '-created_at')
    insurance_funds = InsuranceFund.objects.order_by('name')
    driver_license  = getattr(collaborator, 'driver_license', None)
    parking_permits = driver_license.parking_permits.order_by('-registration_date') if driver_license else []
    return render(request, 'workforce/collaborator_detail.html', {
        'collaborator':    collaborator,
        'rates':           rates,
        'addresses':       addresses,
        'insurance_notes': insurance_notes,
        'insurance_funds': insurance_funds,
        'driver_license':  driver_license,
        'parking_permits': parking_permits,
    })


# ── Editar ─────────────────────────────────────────────────────────────────────

def _collaborator_has_links(collaborator):
    """Retorna True se o colaborador tiver ligações em qualquer outro app."""
    relations = [
        'planning_assignments',
        'planning_day_offs',
        'driven_plannings',
        'vehicle_planning_assignments',
        'ciaw_nodes',
        'default_vehicles',
        'fuelings',
        'fines',
        'vehicle_expenses',
    ]
    if hasattr(collaborator, 'timesheets'):
        relations.append('timesheets')
    return any(getattr(collaborator, rel).exists() for rel in relations)


@perm_required('workforce.change_collaborator')
def collaborator_update(request, pk):
    collaborator   = get_object_or_404(Collaborator, pk=pk)
    next_path      = _safe_next_path(request, (request.GET.get('next') or request.POST.get('next') or '').strip() or None)
    company_locked = _collaborator_has_links(collaborator)
    form = CollaboratorForm(request.POST or None, request.FILES or None, instance=collaborator, company_locked=company_locked)
    if form.is_valid():
        obj = form.save(commit=False)
        if request.POST.get('photo-clear') and not request.FILES.get('photo'):
            if obj.photo:
                obj.photo.delete(save=False)
            obj.photo = None
        obj.save()
        form.save_m2m()
        if next_path:
            return redirect(next_path)
        return redirect('workforce:detail', pk=collaborator.pk)
    rates           = collaborator.hourly_rates.order_by('-start_date')
    insurance_notes = collaborator.insurance_notes.select_related('insurance_fund').order_by('-update_date', '-created_at')
    driver_license  = getattr(collaborator, 'driver_license', None)
    dl_form         = DriverLicenseForm(instance=driver_license)
    parking_permits = driver_license.parking_permits.order_by('-registration_date') if driver_license else []
    return render(request, 'workforce/collaborator_form.html', {
        'form': form, 'title': collaborator.name,
        'collaborator': collaborator, 'rates': rates,
        'insurance_notes': insurance_notes,
        'driver_license': driver_license,
        'dl_form': dl_form,
        'parking_permits': parking_permits,
        'redirect_next': next_path,
        'company_locked': company_locked,
    })


# ── Duplicar colaborador ───────────────────────────────────────────────────────

@perm_required('workforce.add_collaborator')
@require_POST
def collaborator_duplicate(request, pk):
    source = get_object_or_404(Collaborator, pk=pk)
    initial = {
        'name':       source.name,
        'birth_date': source.birth_date,
        'id_number':  source.id_number,
        'id_expiry':  source.id_expiry,
    }
    form = CollaboratorForm(initial=initial)
    # Pré-selecionar as M2M (nationalities e languages) via queryset inicial
    form.fields['nationalities'].initial = source.nationalities.values_list('pk', flat=True)
    form.fields['languages'].initial     = source.languages.values_list('pk', flat=True)
    return render(request, 'workforce/collaborator_form.html', {
        'form': form,
        'title': _('Novo colaborador (cópia de %(name)s)') % {'name': source.name},
        'duplicate_source': source,
    })


# ── Toggle de status (AJAX) ────────────────────────────────────────────────────

@perm_required('workforce.change_collaborator')
@require_POST
def collaborator_status_toggle(request, pk):
    collaborator = get_object_or_404(Collaborator, pk=pk)
    collaborator.status = 'inactive' if collaborator.status == 'active' else 'active'
    collaborator.save(update_fields=['status'])
    return JsonResponse({'ok': True, 'status': collaborator.status, 'status_display': collaborator.get_status_display()})


# ── Autocomplete Nacionalidade ─────────────────────────────────────────────────

@perm_required('workforce.view_collaborator')
def nationality_autocomplete(request):
    q      = request.GET.get('q', '').strip()
    limit  = 15
    qs     = Nationality.objects.filter(name__icontains=q).values('id', 'name')[:limit] if q else []
    return JsonResponse({'results': list(qs)})


# ── Autocomplete Idioma ────────────────────────────────────────────────────────

@perm_required('workforce.view_collaborator')
def language_autocomplete(request):
    q     = request.GET.get('q', '').strip()
    limit = 15
    qs    = Language.objects.filter(name__icontains=q).values('id', 'name')[:limit] if q else []
    return JsonResponse({'results': list(qs)})


# ── Notas de seguro (AJAX) ─────────────────────────────────────────────────────

@perm_required('workforce.change_collaborator')
@require_POST
def insurance_note_create(request, pk):
    collaborator = get_object_or_404(Collaborator, pk=pk)
    form = CollaboratorInsuranceNoteForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
    note = form.save(commit=False)
    note.collaborator = collaborator
    if request.user.is_authenticated:
        note.created_by = request.user
    note.save()
    return JsonResponse({'ok': True, 'note': _insurance_note_to_dict(note)})


@perm_required('workforce.change_collaborator')
@require_POST
def insurance_note_resolve(request, pk, note_pk):
    from django.utils.timezone import now
    collaborator = get_object_or_404(Collaborator, pk=pk)
    note = get_object_or_404(CollaboratorInsuranceNote, pk=note_pk, collaborator=collaborator)
    note.resolved_at = now().date()
    note.save(update_fields=['resolved_at'])
    return JsonResponse({'ok': True})


def _insurance_note_to_dict(note):
    return {
        'id':           note.pk,
        'update_date':  note.update_date.strftime('%d/%m/%Y'),
        'note':         note.note or '',
        'is_blocked':   note.is_blocked,
        'is_pending':   note.is_pending,
        'fund_name':    note.insurance_fund.name if note.insurance_fund else '',
        'resolved_at':  note.resolved_at.strftime('%d/%m/%Y') if note.resolved_at else '',
    }


# ── Valor/hora ─────────────────────────────────────────────────────────────────

@perm_required('workforce.change_collaborator')
@require_POST
def collaborator_hourly_rate_edit(request, pk, rate_pk):
    from .models import CollaboratorHourlyRate
    collaborator = get_object_or_404(Collaborator, pk=pk)
    rate = get_object_or_404(CollaboratorHourlyRate, pk=rate_pk, collaborator=collaborator)
    if rate.end_date is not None:
        return JsonResponse({'ok': False, 'error': _('Apenas a taxa atual pode ser editada.')}, status=400)
    form = CollaboratorHourlyRateCreateForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
    rate.hourly_rate = form.cleaned_data['hourly_rate']
    rate.start_date  = form.cleaned_data['start_date']
    rate.save()
    return JsonResponse({'ok': True, 'rate': {
        'id': rate.pk, 'hourly_rate': str(rate.hourly_rate),
        'start_date': rate.start_date.strftime('%Y-%m-%d'),
        'start_date_display': rate.start_date.strftime('%d/%m/%Y'),
    }})


@perm_required('workforce.change_collaborator')
@require_POST
def collaborator_hourly_rate_create(request, pk):
    collaborator = get_object_or_404(Collaborator, pk=pk)
    form = CollaboratorHourlyRateCreateForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
    collaborator.set_new_hourly_rate(
        hourly_rate=form.cleaned_data['hourly_rate'],
        start_date=form.cleaned_data['start_date'],
    )
    rate = collaborator.get_current_hourly_rate()
    return JsonResponse({'ok': True, 'rate': {
        'id': rate.pk, 'hourly_rate': str(rate.hourly_rate),
        'start_date': rate.start_date.strftime('%Y-%m-%d'),
        'start_date_display': rate.start_date.strftime('%d/%m/%Y'),
        'end_date': rate.end_date.strftime('%Y-%m-%d') if rate.end_date else '',
        'end_date_display': rate.end_date.strftime('%d/%m/%Y') if rate.end_date else '',
        'is_current': True, 'label_current': str(_('Atual')),
    }})


# ── Endereços do colaborador (AJAX) ────────────────────────────────────────────

@perm_required('workforce.change_collaborator')
@require_POST
def collaborator_address_save(request, pk, addr_pk=None):
    collaborator = get_object_or_404(Collaborator, pk=pk)
    instance = get_object_or_404(CollaboratorAddress, pk=addr_pk, collaborator=collaborator) if addr_pk else None
    form = CollaboratorAddressForm(request.POST, instance=instance)
    if form.is_valid():
        addr = form.save(commit=False)
        addr.collaborator = collaborator
        if not instance:
            CollaboratorAddress.objects.filter(
                collaborator=collaborator, valid_until__isnull=True
            ).update(valid_until=addr.valid_from)
        addr.save()
        return JsonResponse({'ok': True, 'address': _address_to_dict(addr)})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@perm_required('workforce.change_collaborator')
@require_POST
def collaborator_address_delete(request, pk, addr_pk):
    addr = get_object_or_404(CollaboratorAddress, pk=addr_pk, collaborator_id=pk)
    addr.delete()
    return JsonResponse({'ok': True})


def _address_to_dict(addr):
    return {
        'id': addr.pk, 'street': addr.street, 'number': addr.number or '',
        'complement': addr.complement or '', 'city': addr.city,
        'postal_code': addr.postal_code, 'state': addr.state or '',
        'country': addr.country,
        'valid_from': addr.valid_from.strftime('%Y-%m-%d'),
        'valid_from_display': addr.valid_from.strftime('%d/%m/%Y'),
        'valid_until': addr.valid_until.strftime('%Y-%m-%d') if addr.valid_until else '',
        'valid_until_display': addr.valid_until.strftime('%d/%m/%Y') if addr.valid_until else '',
        'is_current': addr.valid_until is None, 'full': addr.full_address,
    }


# ── Nacionalidades ─────────────────────────────────────────────────────────────

@perm_required('workforce.view_collaborator')
def nationality_list(request):
    qs = Nationality.objects.order_by('name')
    return render(request, 'workforce/nationality_list.html', {'nationalities': qs})


@perm_required('workforce.change_collaborator')
@require_POST
def nationality_save(request, pk=None):
    instance = get_object_or_404(Nationality, pk=pk) if pk else None
    form = NationalityForm(request.POST, instance=instance)
    if form.is_valid():
        obj = form.save()
        return JsonResponse({'ok': True, 'item': {
            'id': obj.pk, 'name': obj.name,
            'worker_count': obj.collaborators.count(),
        }})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@perm_required('workforce.delete_collaborator')
@require_POST
def nationality_delete(request, pk):
    obj = get_object_or_404(Nationality, pk=pk)
    obj.delete()
    from django.contrib import messages
    messages.success(request, _('Nacionalidade eliminada.'))
    return redirect('workforce:nationality_list')


# ── Idiomas ────────────────────────────────────────────────────────────────────

@perm_required('workforce.view_collaborator')
def language_list(request):
    qs = Language.objects.order_by('name')
    return render(request, 'workforce/language_list.html', {'languages': qs})


@perm_required('workforce.change_collaborator')
@require_POST
def language_save(request, pk=None):
    instance = get_object_or_404(Language, pk=pk) if pk else None
    form = LanguageForm(request.POST, instance=instance)
    if form.is_valid():
        obj = form.save()
        return JsonResponse({'ok': True, 'item': {
            'id': obj.pk, 'name': obj.name,
            'worker_count': obj.collaborators.count(),
        }})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@perm_required('workforce.delete_collaborator')
@require_POST
def language_delete(request, pk):
    obj = get_object_or_404(Language, pk=pk)
    obj.delete()
    from django.contrib import messages
    messages.success(request, _('Idioma eliminado.'))
    return redirect('workforce:language_list')


# ── Caixas de Seguro ───────────────────────────────────────────────────────────

@perm_required('workforce.view_collaborator')
def insurance_fund_list(request):
    qs = InsuranceFund.objects.prefetch_related('contacts').order_by('name')
    return render(request, 'workforce/insurance_fund_list.html', {'funds': qs})


@perm_required('workforce.change_collaborator')
@require_POST
def insurance_fund_save(request, pk=None):
    instance = get_object_or_404(InsuranceFund, pk=pk) if pk else None
    form = InsuranceFundForm(request.POST, instance=instance)
    if form.is_valid():
        obj = form.save()
        return JsonResponse({'ok': True, 'item': {
            'id': obj.pk, 'name': obj.name,
            'phone': obj.phone or '',
            'email': obj.email or '',
            'contact_count': obj.contacts.count(),
            'worker_count': obj.collaborators.count(),
        }})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@perm_required('workforce.view_collaborator')
def insurance_fund_detail(request, pk):
    fund = get_object_or_404(InsuranceFund, pk=pk)
    contacts = fund.contacts.order_by('name')
    collaborators = fund.collaborators.select_related('company').order_by('name')
    return render(request, 'workforce/insurance_fund_detail.html', {
        'fund': fund, 'contacts': contacts, 'collaborators': collaborators,
    })


@perm_required('workforce.delete_collaborator')
@require_POST
def insurance_fund_delete(request, pk):
    fund = get_object_or_404(InsuranceFund, pk=pk)
    fund.delete()
    from django.contrib import messages
    messages.success(request, _('Caixa de seguro eliminada.'))
    return redirect('workforce:insurance_fund_list')


@perm_required('workforce.change_collaborator')
@require_POST
def insurance_fund_contact_save(request, fund_pk, contact_pk=None):
    fund = get_object_or_404(InsuranceFund, pk=fund_pk)
    instance = get_object_or_404(InsuranceFundContact, pk=contact_pk, fund=fund) if contact_pk else None
    form = InsuranceFundContactForm(request.POST, instance=instance)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
    contact = form.save(commit=False)
    contact.fund = fund
    contact.save()
    return JsonResponse({'ok': True, 'contact': {
        'id': contact.pk, 'name': contact.name, 'role': contact.role or '',
        'phone': contact.phone or '', 'email': contact.email or '', 'notes': contact.notes or '',
    }})


@perm_required('workforce.change_collaborator')
@require_POST
def insurance_fund_contact_delete(request, fund_pk, contact_pk):
    contact = get_object_or_404(InsuranceFundContact, pk=contact_pk, fund_id=fund_pk)
    contact.delete()
    return JsonResponse({'ok': True})


# ── Formas Jurídicas ───────────────────────────────────────────────────────────

@perm_required('workforce.view_collaborator')
def legal_form_list(request):
    qs = LegalForm.objects.prefetch_related('clients', 'suppliers', 'subcontractors').order_by('name')
    return render(request, 'workforce/legal_form_list.html', {'legal_forms': qs})


@perm_required('workforce.change_collaborator')
@require_POST
def legal_form_save(request, pk=None):
    instance = get_object_or_404(LegalForm, pk=pk) if pk else None
    form = LegalFormForm(request.POST, instance=instance)
    if form.is_valid():
        obj = form.save()
        return JsonResponse({'ok': True, 'item': {
            'id': obj.pk, 'name': obj.name,
            'abbreviation': obj.abbreviation or '',
            'notes': obj.notes or '',
            'client_count': obj.clients.count(),
            'supplier_count': obj.suppliers.count(),
            'subcontractor_count': obj.subcontractors.count(),
        }})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@perm_required('workforce.delete_collaborator')
@require_POST
def legal_form_delete(request, pk):
    obj = get_object_or_404(LegalForm, pk=pk)
    obj.delete()
    from django.contrib import messages
    messages.success(request, _('Forma jurídica eliminada.'))
    return redirect('workforce:legal_form_list')


# ── Ficheiros sensíveis (só utilizador autenticado) ────────────────────────────

@perm_required('workforce.view_collaborator')
def collaborator_photo_serve(request, pk):
    collaborator = get_object_or_404(Collaborator, pk=pk)
    return _protected_workforce_upload_response(collaborator.photo)


@perm_required('workforce.view_collaborator')
def driver_license_scan_serve(request, pk):
    get_object_or_404(Collaborator, pk=pk)
    dl = DriverLicense.objects.filter(collaborator_id=pk).first()
    if not dl:
        raise Http404()
    return _protected_workforce_upload_response(dl.scan)


# ── CARTA DE CONDUÇÃO ──────────────────────────────────────────────────────────
@perm_required('workforce.change_collaborator')
def driver_license_save(request, pk):
    """Cria ou actualiza a carta de condução do colaborador (POST via modal)."""
    collaborator = get_object_or_404(Collaborator, pk=pk)
    instance = getattr(collaborator, 'driver_license', None)
    form = DriverLicenseForm(request.POST, request.FILES, instance=instance)
    if form.is_valid():
        dl = form.save(commit=False)
        dl.collaborator = collaborator
        dl.save()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'errors': form.errors})


@perm_required('workforce.change_collaborator')
@require_POST
def parking_permit_create(request, pk):
    """Regista uma nova inscrição/renovação de estacionamento (POST via modal)."""
    collaborator = get_object_or_404(Collaborator, pk=pk)
    driver_license = getattr(collaborator, 'driver_license', None)
    if not driver_license:
        return JsonResponse({'ok': False, 'error': 'Carta de condução não registada.'})
    form = ParkingPermitForm(request.POST)
    if form.is_valid():
        permit = form.save(commit=False)
        permit.driver_license = driver_license
        permit.save()
        return JsonResponse({
            'ok': True,
            'id': permit.pk,
            'registration_date': permit.registration_date.strftime('%d/%m/%Y'),
            'expiry_date': permit.expiry_date.strftime('%d/%m/%Y') if permit.expiry_date else '—',
            'amount': str(permit.amount) if permit.amount else '—',
            'notes': permit.notes,
        })
    return JsonResponse({'ok': False, 'errors': form.errors})


@perm_required('workforce.change_collaborator')
@require_POST
def parking_permit_delete(request, pk, permit_pk):
    """Remove um registo de estacionamento."""
    collaborator = get_object_or_404(Collaborator, pk=pk)
    driver_license = getattr(collaborator, 'driver_license', None)
    if not driver_license:
        return JsonResponse({'ok': False})
    permit = get_object_or_404(ParkingPermit, pk=permit_pk, driver_license=driver_license)
    permit.delete()
    return JsonResponse({'ok': True})
