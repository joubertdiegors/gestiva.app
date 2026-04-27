from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal, InvalidOperation

from .models import Service, ServiceCategory, ServiceMaterial
from .forms import ServiceForm, ServiceCategoryForm, ServiceMaterialForm
from catalog.models import Product, UnitOfMeasure


PAGE_SIZE = 30


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def category_list(request):
    qs = (
        ServiceCategory.objects
        .select_related('parent')
        .annotate(
            service_count=Count('services'),
            children_count=Count('children'),
        )
    )

    by_parent = {}
    all_cats = list(qs)
    for cat in all_cats:
        by_parent.setdefault(cat.parent_id, []).append(cat)

    for siblings in by_parent.values():
        siblings.sort(key=lambda c: (c.name or '').lower())

    nodes = []

    def walk(parent_id, level):
        for cat in by_parent.get(parent_id, []):
            nodes.append({'cat': cat, 'level': level, 'indent': ('— ' * level)})
            walk(cat.pk, level + 1)

    walk(None, 0)
    return render(request, 'services/category_list.html', {'categories': nodes})


@login_required
@require_POST
def category_save(request, pk=None):
    instance = get_object_or_404(ServiceCategory, pk=pk) if pk else None
    form = ServiceCategoryForm(request.POST, instance=instance)
    if form.is_valid():
        cat = form.save()
        return JsonResponse({
            'ok': True,
            'category': {
                'id': cat.pk,
                'name': cat.name,
                'parent_id': cat.parent_id or '',
                'parent_name': cat.parent.name if cat.parent else '',
                'is_active': cat.is_active,
                'service_count': cat.services.count(),
                'has_children': cat.children.exists(),
            },
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def category_delete(request, pk):
    cat = get_object_or_404(ServiceCategory, pk=pk)
    if cat.services.exists():
        return JsonResponse(
            {'ok': False, 'error': str(_('Esta categoria tem serviços associados.'))},
            status=400,
        )
    if cat.children.exists():
        return JsonResponse(
            {'ok': False, 'error': str(_('Esta categoria tem subcategorias. Elimine-as primeiro.'))},
            status=400,
        )
    cat.delete()
    return JsonResponse({'ok': True})


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICES
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def service_list(request):
    qs = (
        Service.objects
        .select_related('category', 'unit')
        .annotate(material_count=Count('materials', distinct=True))
        .order_by('code')
    )

    q        = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    status   = request.GET.get('status', '')

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q))
    if category:
        qs = qs.filter(category_id=category)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)

    paginator = Paginator(qs, PAGE_SIZE)
    page      = paginator.get_page(request.GET.get('page'))

    categories = ServiceCategory.objects.filter(is_active=True).order_by('name')

    statuses = [
        ('',         _('Todos')),
        ('active',   _('Activos')),
        ('inactive', _('Inactivos')),
    ]

    return render(request, 'services/service_list.html', {
        'page':       page,
        'categories': categories,
        'statuses':   statuses,
        'q':          q,
        'sel_cat':    category,
        'sel_status': status,
        'total':      paginator.count,
    })


@login_required
def service_create(request):
    form = ServiceForm(request.POST or None)
    if form.is_valid():
        service = form.save()
        messages.success(request, _('Serviço criado com sucesso.'))
        return redirect('services:service_detail', pk=service.pk)
    products = (
        Product.objects.filter(is_active=True)
        .select_related('unit')
        .order_by('name')
    )
    return render(request, 'services/service_form.html', {
        'form':     form,
        'title':    _('Novo serviço'),
        'products': products,
    })


@login_required
def service_detail(request, pk):
    service = get_object_or_404(
        Service.objects
        .select_related('category', 'unit')
        .prefetch_related('materials__product__unit'),
        pk=pk,
    )
    can_delete = not service.materials.exists()
    return render(request, 'services/service_detail.html', {
        'service':    service,
        'can_delete': can_delete,
    })


@login_required
def service_update(request, pk):
    service = get_object_or_404(Service, pk=pk)
    form = ServiceForm(request.POST or None, instance=service)
    if form.is_valid():
        form.save()
        messages.success(request, _('Serviço actualizado.'))
        return redirect('services:service_detail', pk=service.pk)
    products = (
        Product.objects.filter(is_active=True)
        .select_related('unit')
        .order_by('name')
    )
    return render(request, 'services/service_form.html', {
        'form':     form,
        'service':  service,
        'title':    service.name,
        'products': products,
    })


@login_required
@require_POST
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    try:
        service.delete()
    except ProtectedError:
        messages.error(request, _('Este serviço está em uso e não pode ser eliminado.'))
        return redirect('services:service_detail', pk=service.pk)
    messages.success(request, _('Serviço eliminado com sucesso.'))
    return redirect('services:service_list')


@login_required
@require_POST
def service_toggle_active(request, pk):
    service = get_object_or_404(Service, pk=pk)
    service.is_active = not service.is_active
    service.save(update_fields=['is_active'])
    return JsonResponse({'ok': True, 'is_active': service.is_active})


# ═══════════════════════════════════════════════════════════════════════════════
# MATERIALS (AJAX)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def material_save(request, service_pk, pk=None):
    service = get_object_or_404(Service, pk=service_pk)
    instance = get_object_or_404(ServiceMaterial, pk=pk, service=service) if pk else None
    form = ServiceMaterialForm(request.POST, instance=instance)
    if form.is_valid():
        mat = form.save(commit=False)
        mat.service = service
        mat.save()
        price = mat.product.best_purchase_price or Decimal('0')
        return JsonResponse({
            'ok': True,
            'material': {
                'id':                mat.pk,
                'product_id':        mat.product_id,
                'product_name':      mat.product.name,
                'product_unit':      mat.product.unit.symbol,
                'quantity_per_unit': str(mat.quantity_per_unit),
                'waste_percent':     str(mat.waste_percent),
                'effective_quantity':str(mat.effective_quantity),
                'unit_price':        str(price),
                'unit_cost':         str(mat.unit_cost),
                'note':              mat.note,
            },
            'totals': _service_totals(service),
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def material_delete(request, service_pk, pk):
    service = get_object_or_404(Service, pk=service_pk)
    mat = get_object_or_404(ServiceMaterial, pk=pk, service=service)
    mat.delete()
    return JsonResponse({'ok': True, 'totals': _service_totals(service)})


@login_required
def material_list(request, service_pk):
    service = get_object_or_404(
        Service.objects.prefetch_related('materials__product__unit'),
        pk=service_pk,
    )
    items = []
    for mat in service.materials.all():
        price = mat.product.best_purchase_price or Decimal('0')
        items.append({
            'id':                mat.pk,
            'product_id':        mat.product_id,
            'product_name':      mat.product.name,
            'product_unit':      mat.product.unit.symbol,
            'quantity_per_unit': str(mat.quantity_per_unit),
            'waste_percent':     str(mat.waste_percent),
            'effective_quantity':str(mat.effective_quantity),
            'unit_price':        str(price),
            'unit_cost':         str(mat.unit_cost),
            'note':              mat.note,
        })
    return JsonResponse({'ok': True, 'materials': items, 'totals': _service_totals(service)})


def _service_totals(service):
    """Recalcula totais e devolve dict JSON-serializável."""
    service.refresh_from_db()
    return {
        'material_cost': str(service.material_cost_per_unit),
        'labor_cost':    str(service.labor_cost_per_unit),
        'total_cost':    str(service.total_cost_per_unit),
        'suggested':     str(service.suggested_price_per_unit),
        'sale_price':    str(service.effective_sale_price),
    }
