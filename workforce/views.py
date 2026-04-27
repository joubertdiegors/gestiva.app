import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
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

@login_required
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

@login_required
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

@login_required
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

@login_required
def collaborator_update(request, pk):
    collaborator = get_object_or_404(Collaborator, pk=pk)
    next_path    = _safe_next_path(request, (request.GET.get('next') or request.POST.get('next') or '').strip() or None)
    form = CollaboratorForm(request.POST or None, request.FILES or None, instance=collaborator)
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
    })


# ── Toggle de status (AJAX) ────────────────────────────────────────────────────

@login_required
@require_POST
def collaborator_status_toggle(request, pk):
    collaborator = get_object_or_404(Collaborator, pk=pk)
    collaborator.status = 'inactive' if collaborator.status == 'active' else 'active'
    collaborator.save(update_fields=['status'])
    return JsonResponse({'ok': True, 'status': collaborator.status, 'status_display': collaborator.get_status_display()})


# ── Autocomplete Nacionalidade ─────────────────────────────────────────────────

@login_required
def nationality_autocomplete(request):
    q      = request.GET.get('q', '').strip()
    limit  = 15
    qs     = Nationality.objects.filter(name__icontains=q).values('id', 'name')[:limit] if q else []
    return JsonResponse({'results': list(qs)})


# ── Autocomplete Idioma ────────────────────────────────────────────────────────

@login_required
def language_autocomplete(request):
    q     = request.GET.get('q', '').strip()
    limit = 15
    qs    = Language.objects.filter(name__icontains=q).values('id', 'name')[:limit] if q else []
    return JsonResponse({'results': list(qs)})


# ── Notas de seguro (AJAX) ─────────────────────────────────────────────────────

@login_required
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


@login_required
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

@login_required
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


@login_required
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

@login_required
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


@login_required
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

@login_required
def nationality_list(request):
    qs = Nationality.objects.order_by('name')
    return render(request, 'workforce/nationality_list.html', {'nationalities': qs})


@login_required
def nationality_create(request):
    form = NationalityForm(request.POST or None)
    if form.is_valid():
        form.save()
        from django.contrib import messages
        messages.success(request, _('Nacionalidade criada com sucesso.'))
        return redirect('workforce:nationality_list')
    return render(request, 'workforce/nationality_form.html', {'form': form, 'title': _('Nova Nacionalidade')})


@login_required
def nationality_edit(request, pk):
    obj = get_object_or_404(Nationality, pk=pk)
    form = NationalityForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        from django.contrib import messages
        messages.success(request, _('Nacionalidade actualizada.'))
        return redirect('workforce:nationality_list')
    return render(request, 'workforce/nationality_form.html', {'form': form, 'title': obj.name, 'obj': obj})


@login_required
@require_POST
def nationality_delete(request, pk):
    obj = get_object_or_404(Nationality, pk=pk)
    obj.delete()
    from django.contrib import messages
    messages.success(request, _('Nacionalidade eliminada.'))
    return redirect('workforce:nationality_list')


# ── Idiomas ────────────────────────────────────────────────────────────────────

@login_required
def language_list(request):
    qs = Language.objects.order_by('name')
    return render(request, 'workforce/language_list.html', {'languages': qs})


@login_required
def language_create(request):
    form = LanguageForm(request.POST or None)
    if form.is_valid():
        form.save()
        from django.contrib import messages
        messages.success(request, _('Idioma criado com sucesso.'))
        return redirect('workforce:language_list')
    return render(request, 'workforce/language_form.html', {'form': form, 'title': _('Novo Idioma')})


@login_required
def language_edit(request, pk):
    obj = get_object_or_404(Language, pk=pk)
    form = LanguageForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        from django.contrib import messages
        messages.success(request, _('Idioma actualizado.'))
        return redirect('workforce:language_list')
    return render(request, 'workforce/language_form.html', {'form': form, 'title': obj.name, 'obj': obj})


@login_required
@require_POST
def language_delete(request, pk):
    obj = get_object_or_404(Language, pk=pk)
    obj.delete()
    from django.contrib import messages
    messages.success(request, _('Idioma eliminado.'))
    return redirect('workforce:language_list')


# ── Caixas de Seguro ───────────────────────────────────────────────────────────

@login_required
def insurance_fund_list(request):
    qs = InsuranceFund.objects.prefetch_related('contacts').order_by('name')
    return render(request, 'workforce/insurance_fund_list.html', {'funds': qs})


@login_required
def insurance_fund_create(request):
    form = InsuranceFundForm(request.POST or None)
    if form.is_valid():
        form.save()
        from django.contrib import messages
        messages.success(request, _('Caixa de seguro criada com sucesso.'))
        return redirect('workforce:insurance_fund_list')
    return render(request, 'workforce/insurance_fund_form.html', {'form': form, 'title': _('Nova Caixa de Seguro')})


@login_required
def insurance_fund_edit(request, pk):
    fund = get_object_or_404(InsuranceFund, pk=pk)
    form = InsuranceFundForm(request.POST or None, instance=fund)
    if form.is_valid():
        form.save()
        from django.contrib import messages
        messages.success(request, _('Caixa de seguro actualizada.'))
        return redirect('workforce:insurance_fund_detail', pk=fund.pk)
    contacts = fund.contacts.order_by('name')
    return render(request, 'workforce/insurance_fund_form.html', {
        'form': form, 'title': fund.name, 'fund': fund, 'contacts': contacts,
    })


@login_required
def insurance_fund_detail(request, pk):
    fund = get_object_or_404(InsuranceFund, pk=pk)
    contacts = fund.contacts.order_by('name')
    collaborators = fund.collaborators.select_related('company').order_by('name')
    return render(request, 'workforce/insurance_fund_detail.html', {
        'fund': fund, 'contacts': contacts, 'collaborators': collaborators,
    })


@login_required
@require_POST
def insurance_fund_delete(request, pk):
    fund = get_object_or_404(InsuranceFund, pk=pk)
    fund.delete()
    from django.contrib import messages
    messages.success(request, _('Caixa de seguro eliminada.'))
    return redirect('workforce:insurance_fund_list')


@login_required
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


@login_required
@require_POST
def insurance_fund_contact_delete(request, fund_pk, contact_pk):
    contact = get_object_or_404(InsuranceFundContact, pk=contact_pk, fund_id=fund_pk)
    contact.delete()
    return JsonResponse({'ok': True})


# ── Formas Jurídicas ───────────────────────────────────────────────────────────

@login_required
def legal_form_list(request):
    qs = LegalForm.objects.prefetch_related('clients', 'suppliers', 'subcontractors').order_by('name')
    return render(request, 'workforce/legal_form_list.html', {'legal_forms': qs})


@login_required
def legal_form_create(request):
    form = LegalFormForm(request.POST or None)
    if form.is_valid():
        form.save()
        from django.contrib import messages
        messages.success(request, _('Forma jurídica criada com sucesso.'))
        return redirect('workforce:legal_form_list')
    return render(request, 'workforce/legal_form_form.html', {'form': form, 'title': _('Nova Forma Jurídica')})


@login_required
def legal_form_edit(request, pk):
    obj = get_object_or_404(LegalForm, pk=pk)
    form = LegalFormForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        from django.contrib import messages
        messages.success(request, _('Forma jurídica actualizada.'))
        return redirect('workforce:legal_form_list')
    return render(request, 'workforce/legal_form_form.html', {'form': form, 'title': obj.display_name, 'obj': obj})


@login_required
@require_POST
def legal_form_delete(request, pk):
    obj = get_object_or_404(LegalForm, pk=pk)
    obj.delete()
    from django.contrib import messages
    messages.success(request, _('Forma jurídica eliminada.'))
    return redirect('workforce:legal_form_list')


# ── Ficheiros sensíveis (só utilizador autenticado) ────────────────────────────

@login_required
def collaborator_photo_serve(request, pk):
    collaborator = get_object_or_404(Collaborator, pk=pk)
    return _protected_workforce_upload_response(collaborator.photo)


@login_required
def driver_license_scan_serve(request, pk):
    get_object_or_404(Collaborator, pk=pk)
    dl = DriverLicense.objects.filter(collaborator_id=pk).first()
    if not dl:
        raise Http404()
    return _protected_workforce_upload_response(dl.scan)


# ── CARTA DE CONDUÇÃO ──────────────────────────────────────────────────────────
@login_required
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


@login_required
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


@login_required
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
