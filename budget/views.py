from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from decimal import Decimal, InvalidOperation

from .models import Budget, BudgetChapter, BudgetItem, BudgetItemMaterial
from .forms import BudgetForm, BudgetChapterForm, BudgetItemForm
from clients.models import Client
from projects.models import Project
from services.models import Service


# ─── helpers ────────────────────────────────────────────────────────────────

def _dec(val, default='0'):
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def _budget_totals(budget):
    budget.refresh_from_db()
    return {
        'subtotal_cost':   str(budget.subtotal_cost.quantize(Decimal('0.01'))),
        'subtotal_ht':     str(budget.subtotal_ht.quantize(Decimal('0.01'))),
        'discount_amount': str(budget.discount_amount),
        'total_ht':        str(budget.total_ht.quantize(Decimal('0.01'))),
        'total_vat':       str(budget.total_vat.quantize(Decimal('0.01'))),
        'total_ttc':       str(budget.total_ttc.quantize(Decimal('0.01'))),
        'margin_amount':   str(budget.gross_margin_amount.quantize(Decimal('0.01'))),
        'margin_pct':      str(budget.gross_margin_percent),
    }


def _item_dict(item):
    return {
        'id':                   item.pk,
        'chapter_id':           item.chapter_id,
        'service_id':           item.service_id,
        'service_name':         item.service_name_snapshot,
        'service_code':         item.service_code_snapshot,
        'service_unit':         item.service_unit_snapshot,
        'description':          item.description,
        'quantity':             str(item.quantity),
        'unit_price_override':  str(item.unit_price_override or ''),
        'effective_unit_price': str(item.effective_unit_price.quantize(Decimal('0.0001'))),
        'labor_cost_per_unit':  str(item.labor_cost_per_unit),
        'margin_percent':       str(item.margin_percent),
        'discount_percent':     str(item.discount_percent),
        'vat_rate':             str(item.vat_rate),
        'total_cost':           str(item.total_cost.quantize(Decimal('0.01'))),
        'total_price':          str(item.total_price.quantize(Decimal('0.01'))),
        'vat_amount':           str(item.vat_amount.quantize(Decimal('0.01'))),
        'total_ttc':            str(item.total_ttc.quantize(Decimal('0.01'))),
        'order':                item.order,
    }


def _chapter_dict(ch):
    return {
        'id':        ch.pk,
        'title':     ch.title,
        'parent_id': ch.parent_id,
        'order':     ch.order,
        'depth':     ch.depth,
    }


# ─── list ────────────────────────────────────────────────────────────────────

@login_required
def budget_list(request):
    qs = Budget.objects.select_related('client', 'project').order_by('-created_at')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    client_id = request.GET.get('client', '')

    if q:
        from django.db.models import Q
        qs = qs.filter(Q(number__icontains=q) | Q(title__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if client_id:
        qs = qs.filter(client_id=client_id)

    clients = Client.objects.filter(is_active=True).order_by('name')

    return render(request, 'budget/budget_list.html', {
        'budgets':  qs,
        'clients':  clients,
        'statuses': Budget.Status.choices,
        'q':        q,
        'status':   status,
        'client_id': client_id,
    })


# ─── create ──────────────────────────────────────────────────────────────────

@login_required
def budget_create(request):
    initial = {'number': Budget.next_number()}
    form = BudgetForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        budget = form.save(commit=False)
        budget.created_by = request.user
        budget.save()
        return redirect('budget:budget_detail', pk=budget.pk)

    clients  = Client.objects.filter(is_active=True).order_by('name')
    projects = Project.objects.order_by('name')
    return render(request, 'budget/budget_form.html', {
        'form':     form,
        'clients':  clients,
        'projects': projects,
        'is_create': True,
    })


# ─── detail ──────────────────────────────────────────────────────────────────

@login_required
def budget_detail(request, pk):
    budget = get_object_or_404(
        Budget.objects.select_related('client', 'project', 'created_by'),
        pk=pk
    )
    # Capítulos em árvore ordenados
    chapters = BudgetChapter.objects.filter(budget=budget).order_by('order')
    items    = BudgetItem.objects.filter(budget=budget).select_related('service', 'chapter').order_by('chapter__order', 'order')

    return render(request, 'budget/budget_detail.html', {
        'budget':   budget,
        'chapters': chapters,
        'items':    items,
        'totals':   _budget_totals(budget),
    })


# ─── update ──────────────────────────────────────────────────────────────────

@login_required
def budget_update(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    form   = BudgetForm(request.POST or None, instance=budget)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('budget:budget_detail', pk=budget.pk)

    clients  = Client.objects.filter(is_active=True).order_by('name')
    projects = Project.objects.order_by('name')
    chapters = BudgetChapter.objects.filter(budget=budget).order_by('order')
    items    = BudgetItem.objects.filter(budget=budget).select_related('service', 'chapter').order_by('chapter__order', 'order')
    services = Service.objects.filter(is_active=True).select_related('unit', 'category').order_by('name')

    return render(request, 'budget/budget_edit.html', {
        'form':     form,
        'budget':   budget,
        'clients':  clients,
        'projects': projects,
        'chapters': chapters,
        'items':    items,
        'services': services,
        'totals':   _budget_totals(budget),
    })


# ─── delete ──────────────────────────────────────────────────────────────────

@login_required
@require_POST
def budget_delete(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    budget.delete()
    return redirect('budget:budget_list')


# ─── AJAX: project list by client ────────────────────────────────────────────

@login_required
def ajax_projects_by_client(request):
    client_id = request.GET.get('client_id')
    if not client_id:
        return JsonResponse([], safe=False)
    projects = Project.objects.filter(client_id=client_id).order_by('name').values('id', 'name')
    return JsonResponse(list(projects), safe=False)


# ─── AJAX: project quick-create ──────────────────────────────────────────────

@login_required
@require_POST
def ajax_project_create(request):
    client_id = request.POST.get('client_id')
    name      = request.POST.get('name', '').strip()
    if not client_id or not name:
        return JsonResponse({'ok': False, 'error': str(_('Cliente e nome são obrigatórios.'))})
    try:
        project = Project.objects.create(
            name=name,
            client_id=client_id,
            created_by=request.user,
        )
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': True, 'id': project.pk, 'name': project.name})


# ─── AJAX: chapter CRUD ───────────────────────────────────────────────────────

@login_required
@require_POST
def chapter_save(request, budget_pk, pk=None):
    budget = get_object_or_404(Budget, pk=budget_pk)
    instance = get_object_or_404(BudgetChapter, pk=pk, budget=budget) if pk else None
    form = BudgetChapterForm(request.POST, instance=instance, budget=budget)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors})
    ch = form.save(commit=False)
    ch.budget = budget
    if not ch.order:
        ch.order = BudgetChapter.objects.filter(budget=budget).count()
    ch.save()
    return JsonResponse({'ok': True, 'chapter': _chapter_dict(ch)})


@login_required
@require_POST
def chapter_delete(request, budget_pk, pk):
    budget = get_object_or_404(Budget, pk=budget_pk)
    ch = get_object_or_404(BudgetChapter, pk=pk, budget=budget)
    if ch.items.exists():
        return JsonResponse({'ok': False, 'error': str(_('Capítulo tem itens associados.'))})
    if ch.children.exists():
        return JsonResponse({'ok': False, 'error': str(_('Capítulo tem sub-capítulos. Elimine-os primeiro.'))})
    ch.delete()
    return JsonResponse({'ok': True, 'totals': _budget_totals(budget)})


# ─── AJAX: item CRUD ─────────────────────────────────────────────────────────

@login_required
@require_POST
def item_save(request, budget_pk, pk=None):
    budget   = get_object_or_404(Budget, pk=budget_pk)
    instance = get_object_or_404(BudgetItem, pk=pk, budget=budget) if pk else None

    # Resolve service first to auto-fill snapshots
    service_id = request.POST.get('service')
    service    = get_object_or_404(Service, pk=service_id) if service_id else None

    form = BudgetItemForm(request.POST, instance=instance, budget=budget)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors})

    with transaction.atomic():
        item = form.save(commit=False)
        item.budget = budget
        if service and not instance:
            item.service_name_snapshot = service.name
            item.service_code_snapshot = service.code
            item.service_unit_snapshot = service.unit.symbol if service.unit else ''
            item.labor_cost_per_unit   = service.labor_cost_per_unit
            if not item.margin_percent:
                item.margin_percent = service.default_margin_percent
        elif service and instance:
            item.service_name_snapshot = service.name
            item.service_code_snapshot = service.code
            item.service_unit_snapshot = service.unit.symbol if service.unit else ''
        if not item.order:
            item.order = BudgetItem.objects.filter(budget=budget).count()
        item.save()

        # If new item, clone materials from service catalogue
        if not instance and service:
            for mat in service.materials.select_related('product').all():
                price = mat.product.best_purchase_price or Decimal('0')
                BudgetItemMaterial.objects.create(
                    budget_item           = item,
                    product               = mat.product,
                    product_name_snapshot = mat.product.name,
                    unit_snapshot         = mat.product.unit.symbol if mat.product.unit else '',
                    quantity              = mat.effective_quantity * item.quantity,
                    unit_price_snapshot   = price,
                )

    return JsonResponse({
        'ok':     True,
        'item':   _item_dict(item),
        'totals': _budget_totals(budget),
    })


@login_required
@require_POST
def item_delete(request, budget_pk, pk):
    budget = get_object_or_404(Budget, pk=budget_pk)
    item   = get_object_or_404(BudgetItem, pk=pk, budget=budget)
    item.delete()
    return JsonResponse({'ok': True, 'totals': _budget_totals(budget)})


# ─── AJAX: service info ───────────────────────────────────────────────────────

@login_required
def service_info(request, pk):
    s = get_object_or_404(Service.objects.select_related('unit', 'category'), pk=pk)
    return JsonResponse({
        'ok':                    True,
        'name':                  s.name,
        'code':                  s.code,
        'unit':                  s.unit.symbol if s.unit else '',
        'labor_cost_per_unit':   str(s.labor_cost_per_unit),
        'default_margin_percent':str(s.default_margin_percent),
        'effective_sale_price':  str(s.effective_sale_price),
        'total_cost_per_unit':   str(s.total_cost_per_unit),
    })
