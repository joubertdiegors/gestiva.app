from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext_lazy as _

from .models import Product, ProductCategory, UnitOfMeasure
from .forms import ProductForm, ProductCategoryForm, UnitOfMeasureForm


PAGE_SIZE = 30


# ═══════════════════════════════════════════════════════════════════════════════
# UNITS OF MEASURE
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def unit_list(request):
    units = UnitOfMeasure.objects.annotate(
        product_count=Count('products')
    ).order_by('symbol')
    return render(request, 'catalog/unit_list.html', {'units': units})


@login_required
@require_POST
def unit_save(request, pk=None):
    instance = get_object_or_404(UnitOfMeasure, pk=pk) if pk else None
    form = UnitOfMeasureForm(request.POST, instance=instance)
    if form.is_valid():
        unit = form.save()
        return JsonResponse({
            'ok': True,
            'unit': {
                'id': unit.pk,
                'symbol': unit.symbol,
                'name': unit.name,
                'description': unit.description,
                'product_count': unit.products.count(),
            },
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def unit_delete(request, pk):
    unit = get_object_or_404(UnitOfMeasure, pk=pk)
    if unit.products.exists():
        return JsonResponse(
            {
                'ok': False,
                'error': str(
                    _('Esta unidade está em uso por produtos e não pode ser eliminada.')
                ),
            },
            status=400,
        )
    unit.delete()
    return JsonResponse({'ok': True})


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCT CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def category_list(request):
    qs = (
        ProductCategory.objects
        .select_related('parent')
        .annotate(
            product_count=Count('products'),
            children_count=Count('children'),
        )
    )

    # ERPs normalmente exibem categorias como árvore (pai seguido de filhos),
    # não em ordem alfabética plana — evita "separar" subcategorias do pai.
    by_parent = {}
    all_cats = list(qs)
    for cat in all_cats:
        by_parent.setdefault(cat.parent_id, []).append(cat)

    for siblings in by_parent.values():
        siblings.sort(key=lambda c: (c.name or '').lower())

    nodes = []

    def walk(parent_id, level):
        for cat in by_parent.get(parent_id, []):
            nodes.append({
                'cat': cat,
                'level': level,
                'indent': ('— ' * level),
            })
            walk(cat.pk, level + 1)

    walk(None, 0)

    return render(request, 'catalog/category_list.html', {
        'categories': nodes,  # lista linear com level/indent para exibição em árvore
    })


@login_required
@require_POST
def category_save(request, pk=None):
    instance = get_object_or_404(ProductCategory, pk=pk) if pk else None
    form = ProductCategoryForm(request.POST, instance=instance)
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
                'product_count': cat.products.count(),
                'has_children': cat.children.exists(),
            },
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def category_delete(request, pk):
    cat = get_object_or_404(ProductCategory, pk=pk)
    if cat.products.exists():
        return JsonResponse(
            {'ok': False, 'error': str(_('Esta categoria tem produtos associados.'))},
            status=400,
        )
    if cat.children.exists():
        return JsonResponse(
            {
                'ok': False,
                'error': str(
                    _('Esta categoria tem subcategorias. Elimine-as primeiro.')
                ),
            },
            status=400,
        )
    cat.delete()
    return JsonResponse({'ok': True})


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCTS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def product_list(request):
    qs = (
        Product.objects
        .select_related('category', 'unit')
        .annotate(
            supplier_offers_count=Count('supplier_offers', distinct=True),
            service_usages_count=Count('service_usages', distinct=True),
            budget_usages_count=Count('budget_usages', distinct=True),
        )
        .order_by('name')
    )

    q        = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    status   = request.GET.get('status', '')

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(barcode__icontains=q))
    if category:
        qs = qs.filter(category_id=category)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    elif status == 'approved':
        qs = qs.filter(is_approved=True, is_active=True)
    elif status == 'pending':
        qs = qs.filter(is_approved=False, is_active=True)

    paginator = Paginator(qs, PAGE_SIZE)
    page      = paginator.get_page(request.GET.get('page'))

    categories = ProductCategory.objects.filter(is_active=True).order_by('name')

    statuses = [
        ('',        _('Todos')),
        ('active',  _('Activos')),
        ('inactive',_('Inactivos')),
        ('approved',_('Aprovados')),
        ('pending', _('Pendentes')),
    ]

    return render(request, 'catalog/product_list.html', {
        'page':       page,
        'categories': categories,
        'statuses':   statuses,
        'q':          q,
        'sel_cat':    category,
        'sel_status': status,
        'total':      paginator.count,
    })


@login_required
def product_create(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        product = form.save(commit=False)
        product.created_by = request.user
        product.save()
        messages.success(request, _('Produto criado com sucesso.'))
        return redirect('catalog:product_detail', pk=product.pk)
    return render(request, 'catalog/product_form.html', {
        'form':  form,
        'title': _('Novo produto'),
    })


@login_required
def product_detail(request, pk):
    from procurement.models import ProductSupplier
    from suppliers.models import Supplier
    product = get_object_or_404(
        Product.objects
        .select_related('category', 'unit', 'created_by')
        .prefetch_related(
            Prefetch(
                'supplier_offers',
                queryset=ProductSupplier.objects
                    .filter(is_active=True)
                    .select_related('supplier', 'package_unit')
                    .order_by('unit_price'),
            )
        ),
        pk=pk,
    )
    can_delete = not (
        product.supplier_offers.exists()
        or product.service_usages.exists()
        or product.budget_usages.exists()
    )
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    units = UnitOfMeasure.objects.order_by('symbol')
    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'can_delete': can_delete,
        'suppliers': suppliers,
        'units': units,
    })


@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        form.save()
        messages.success(request, _('Produto actualizado.'))
        return redirect('catalog:product_detail', pk=product.pk)
    return render(request, 'catalog/product_form.html', {
        'form':    form,
        'product': product,
        'title':   product.name,
    })


@login_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    in_use = (
        product.supplier_offers.exists()
        or product.service_usages.exists()
        or product.budget_usages.exists()
    )
    if in_use:
        messages.error(
            request,
            _(
                'Este produto está a ser usado (fornecedores/serviços/devis) e não pode ser eliminado.'
            ),
        )
        return redirect('catalog:product_detail', pk=product.pk)

    try:
        product.delete()
    except ProtectedError:
        # fallback caso surja um novo relacionamento PROTECT no futuro
        messages.error(
            request,
            _(
                'Este produto está a ser usado noutro registo e não pode ser eliminado.'
            ),
        )
        return redirect('catalog:product_detail', pk=product.pk)

    messages.success(request, _('Produto eliminado com sucesso.'))
    return redirect('catalog:product_list')


@login_required
@require_POST
def product_toggle_approved(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_approved = not product.is_approved
    product.save(update_fields=['is_approved'])
    return JsonResponse({'ok': True, 'is_approved': product.is_approved})


@login_required
@require_POST
def product_toggle_active(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=['is_active'])
    return JsonResponse({'ok': True, 'is_active': product.is_active})
