from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext_lazy as _
from .models import Supplier, SupplierAddress, SupplierContact
from .forms import SupplierForm, SupplierAddressForm, SupplierContactForm
from catalog.models import Product, UnitOfMeasure
from procurement.models import ProductSupplier


@login_required
def supplier_list(request):
    suppliers = (
        Supplier.objects
        .prefetch_related('addresses', 'contacts')
        .annotate(
            product_offers_count=Count('product_offers', distinct=True),
            budget_material_usages_count=Count('budget_material_usages', distinct=True),
        )
        .order_by('name')
    )
    return render(request, 'suppliers/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if form.is_valid():
        supplier = form.save()
        return redirect('suppliers:detail', pk=supplier.pk)
    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'title': _("Novo fornecedor"),
    })


@login_required
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if form.is_valid():
        form.save()
        return redirect('suppliers:detail', pk=supplier.pk)
    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'title': supplier.name,
        'supplier': supplier,
    })


@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(
        Supplier.objects
        .prefetch_related(
            'addresses',
            'contacts',
            'product_offers',
        )
        .annotate(
            product_offers_count=Count('product_offers', distinct=True),
            budget_material_usages_count=Count('budget_material_usages', distinct=True),
        ),
        pk=pk,
    )
    can_delete = (supplier.product_offers_count == 0 and supplier.budget_material_usages_count == 0)
    offers = (
        ProductSupplier.objects
        .filter(supplier=supplier, is_active=True)
        .select_related('product', 'product__unit', 'package_unit')
        .order_by('product__name')
    )
    products = Product.objects.filter(is_active=True).order_by('name')
    units = UnitOfMeasure.objects.order_by('symbol')
    return render(request, 'suppliers/supplier_detail.html', {
        'supplier': supplier,
        'can_delete': can_delete,
        'offers': offers,
        'products': products,
        'units': units,
    })


@login_required
@require_POST
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)

    # Preferimos impedir antes, para feedback mais claro
    if supplier.product_offers.exists() or supplier.budget_material_usages.exists():
        messages.error(
            request,
            _(
                'Este fornecedor está em uso (ofertas de produto e/ou materiais em orçamento) e não pode ser eliminado.'
            ),
        )
        return redirect('suppliers:detail', pk=supplier.pk)

    try:
        supplier.delete()
    except ProtectedError:
        messages.error(
            request,
            _(
                'Este fornecedor está em uso noutro registo e não pode ser eliminado.'
            ),
        )
        return redirect('suppliers:detail', pk=supplier.pk)

    messages.success(request, _('Fornecedor eliminado com sucesso.'))
    return redirect('suppliers:list')


@login_required
@require_POST
def address_save(request, supplier_pk, pk=None):
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    instance = get_object_or_404(SupplierAddress, pk=pk, supplier=supplier) if pk else None
    form = SupplierAddressForm(request.POST, instance=instance)
    if form.is_valid():
        addr = form.save(commit=False)
        addr.supplier = supplier
        addr.save()
        return JsonResponse({'ok': True, 'address': _address_to_dict(addr)})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def address_delete(request, supplier_pk, pk):
    addr = get_object_or_404(SupplierAddress, pk=pk, supplier_id=supplier_pk)
    addr.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def contact_save(request, supplier_pk, pk=None):
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    instance = get_object_or_404(SupplierContact, pk=pk, supplier=supplier) if pk else None
    form = SupplierContactForm(request.POST, instance=instance)
    if form.is_valid():
        contact = form.save(commit=False)
        contact.supplier = supplier
        contact.save()
        return JsonResponse({'ok': True, 'contact': _contact_to_dict(contact)})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def contact_delete(request, supplier_pk, pk):
    contact = get_object_or_404(SupplierContact, pk=pk, supplier_id=supplier_pk)
    contact.delete()
    return JsonResponse({'ok': True})


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


def _contact_to_dict(contact):
    return {
        'id':                   contact.pk,
        'name':                 contact.name,
        'contact_type':         contact.contact_type,
        'contact_type_display': contact.get_contact_type_display(),
        'phone':                contact.phone or '',
        'email':                contact.email or '',
        'website':              contact.website or '',
        'is_default':           contact.is_default,
    }
