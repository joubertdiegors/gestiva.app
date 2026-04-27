from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from .models import Subcontractor, SubcontractorAddress
from .forms import SubcontractorForm, SubcontractorAddressForm
from workforce.models import Collaborator


# ── List / Create / Update / Detail ─────────────────────────────────────────

@login_required
def subcontractor_list(request):
    subcontractors = (
        Subcontractor.objects
        .annotate(team_count=Count('collaborators', distinct=True))
        .prefetch_related('addresses')
        .order_by('name')
    )
    return render(request, 'subcontractors/list.html', {'subcontractors': subcontractors})


@login_required
def subcontractor_create(request):
    form = SubcontractorForm(request.POST or None)
    if form.is_valid():
        sub = form.save()
        return redirect('subcontractors:detail', pk=sub.pk)
    return render(request, 'subcontractors/form.html', {
        'form': form,
        'title': _("Novo subcontratado"),
    })


@login_required
def subcontractor_update(request, pk):
    sub = get_object_or_404(Subcontractor, pk=pk)
    form = SubcontractorForm(request.POST or None, instance=sub)
    if form.is_valid():
        form.save()
        return redirect('subcontractors:detail', pk=sub.pk)
    return render(request, 'subcontractors/form.html', {
        'form': form,
        'title': sub.name,
        'subcontractor': sub,
    })


@login_required
def subcontractor_detail(request, pk):
    team = (
        Collaborator.objects
        .filter(company_id=pk)
        .select_related('insurance_fund', 'company')
        .prefetch_related('hourly_rates')
        .order_by('name')
    )
    sub = get_object_or_404(
        Subcontractor.objects.prefetch_related('addresses'),
        pk=pk,
    )
    return render(request, 'subcontractors/detail.html', {
        'subcontractor': sub,
        'team': team,
    })


# ── Address AJAX endpoints ───────────────────────────────────────────────────

@login_required
@require_POST
def address_save(request, sub_pk, pk=None):
    sub = get_object_or_404(Subcontractor, pk=sub_pk)
    instance = get_object_or_404(SubcontractorAddress, pk=pk, subcontractor=sub) if pk else None
    form = SubcontractorAddressForm(request.POST, instance=instance)
    if form.is_valid():
        addr = form.save(commit=False)
        addr.subcontractor = sub
        addr.save()
        return JsonResponse({'ok': True, 'address': _address_to_dict(addr)})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def address_delete(request, sub_pk, pk):
    addr = get_object_or_404(SubcontractorAddress, pk=pk, subcontractor_id=sub_pk)
    addr.delete()
    return JsonResponse({'ok': True})


# ── Serializers ──────────────────────────────────────────────────────────────

def _address_to_dict(addr):
    street_full = addr.street + (f', {addr.number}' if addr.number else '') + (f' — {addr.complement}' if addr.complement else '')
    return {
        'id':          addr.pk,
        'label':       addr.label or '',
        'street':      addr.street,
        'number':      addr.number or '',
        'complement':  addr.complement or '',
        'city':        addr.city,
        'postal_code': addr.postal_code,
        'state':       addr.state or '',
        'country':     addr.country,
        'is_default':  addr.is_default,
        'full':        f'{street_full} — {addr.postal_code} {addr.city}',
    }


