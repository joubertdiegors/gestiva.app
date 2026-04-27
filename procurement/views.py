from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from catalog.models import Product
from suppliers.models import Supplier, SupplierContact

from .forms import ProductSupplierForm
from .models import (
    ProductSupplier,
    ProductSupplierPriceHistory,
    RFQ,
    RFQItem,
    RFQVendor,
    RFQVendorLine,
)
from .utils import format_eur


def _offer_to_dict(offer: ProductSupplier):
    return {
        'id': offer.pk,
        'product_id': offer.product_id,
        'product_name': offer.product.name,
        'supplier_id': offer.supplier_id,
        'supplier_name': offer.supplier.trade_name or offer.supplier.name,
        'supplier_ref': offer.supplier_ref or '',
        'supplier_description': offer.supplier_description or '',
        'unit_price': str(offer.unit_price),
        'package_qty': str(offer.package_qty),
        'package_unit_id': offer.package_unit_id or '',
        'package_unit_symbol': offer.package_unit.symbol if offer.package_unit else '',
        'minimum_order_qty': str(offer.minimum_order_qty),
        'lead_time_days': offer.lead_time_days,
        'is_preferred': offer.is_preferred,
        'is_active': offer.is_active,
        'valid_from': offer.valid_from.isoformat() if offer.valid_from else '',
        'valid_until': offer.valid_until.isoformat() if offer.valid_until else '',
    }


def _save_offer(request, *, fixed_product=None, fixed_supplier=None, instance=None):
    form = ProductSupplierForm(request.POST, instance=instance)

    # Force binding based on context (product screen or supplier screen)
    if fixed_product is not None:
        form.data = form.data.copy()
        form.data['product'] = str(fixed_product.pk)
    if fixed_supplier is not None:
        form.data = form.data.copy()
        form.data['supplier'] = str(fixed_supplier.pk)

    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    with transaction.atomic():
        old_price = None
        if instance and instance.pk:
            old_price = ProductSupplier.objects.filter(pk=instance.pk).values_list('unit_price', flat=True).first()

        try:
            offer = form.save()
        except IntegrityError:
            # Unique constraint (product, supplier)
            return JsonResponse(
                {
                    'ok': False,
                    'errors': {
                        'supplier': [_('Já existe um preço cadastrado para este fornecedor neste produto.')],
                    },
                },
                status=400,
            )

        new_price = offer.unit_price
        note = (form.cleaned_data.get('price_note') or '').strip()
        if old_price is None or new_price != old_price:
            ProductSupplierPriceHistory.objects.create(
                product_supplier=offer,
                price=new_price,
                changed_by=getattr(request, 'user', None) if request.user.is_authenticated else None,
                note=note,
            )

    offer = (
        ProductSupplier.objects
        .select_related('product', 'supplier', 'package_unit')
        .get(pk=offer.pk)
    )
    return JsonResponse({'ok': True, 'offer': _offer_to_dict(offer)})


@login_required
@require_POST
def product_offer_save(request, product_pk, pk=None):
    product = get_object_or_404(Product, pk=product_pk)
    instance = None
    if pk:
        instance = get_object_or_404(ProductSupplier, pk=pk, product=product)
    return _save_offer(request, fixed_product=product, instance=instance)


@login_required
@require_POST
def product_offer_delete(request, product_pk, pk):
    product = get_object_or_404(Product, pk=product_pk)
    offer = get_object_or_404(ProductSupplier, pk=pk, product=product)
    offer.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def supplier_offer_save(request, supplier_pk, pk=None):
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    instance = None
    if pk:
        instance = get_object_or_404(ProductSupplier, pk=pk, supplier=supplier)
    return _save_offer(request, fixed_supplier=supplier, instance=instance)


@login_required
@require_POST
def supplier_offer_delete(request, supplier_pk, pk):
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    offer = get_object_or_404(ProductSupplier, pk=pk, supplier=supplier)
    offer.delete()
    return JsonResponse({'ok': True})


@login_required
def offer_price_history(request, pk):
    offer = get_object_or_404(
        ProductSupplier.objects.select_related('product', 'supplier'),
        pk=pk,
    )
    items = (
        ProductSupplierPriceHistory.objects
        .filter(product_supplier=offer)
        .select_related('changed_by')
        .order_by('-effective_date')[:30]
    )
    return JsonResponse({
        'ok': True,
        'offer': {
            'id': offer.pk,
            'product': offer.product.name,
            'supplier': offer.supplier.trade_name or offer.supplier.name,
        },
        'items': [
            {
                'price': format_eur(i.price),
                'effective_date': i.effective_date.isoformat(),
                'changed_by': (
                    (i.changed_by.get_full_name() or i.changed_by.username)
                    if i.changed_by else ''
                ),
                'note': i.note or '',
            }
            for i in items
        ],
    })


# ═══════════════════════════════════════════════════════════════════════════════
# RFQ (Request for Quotation)
# ═══════════════════════════════════════════════════════════════════════════════

PAGE_SIZE = 30


@login_required
def rfq_list(request):
    qs = RFQ.objects.select_related('requested_by').order_by('-created_at')
    status = request.GET.get('status', '').strip()
    q = request.GET.get('q', '').strip()

    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(number__icontains=q)

    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'procurement/rfq_list.html', {
        'page': page,
        'q': q,
        'sel_status': status,
        'statuses': RFQ.Status.choices,
        'total': paginator.count,
    })


@login_required
def rfq_create(request):
    rfq = RFQ.objects.create(requested_by=request.user)
    return redirect('procurement:rfq_detail', pk=rfq.pk)


@login_required
def rfq_detail(request, pk):
    rfq = get_object_or_404(
        RFQ.objects
        .select_related('requested_by')
        .prefetch_related(
            'items__product__unit',
            'vendors__supplier',
        ),
        pk=pk,
    )
    items = list(
        RFQItem.objects
        .filter(rfq=rfq)
        .select_related('product__unit', 'selected_vendor__supplier')
        .order_by('id')
    )
    vendors = list(
        RFQVendor.objects
        .filter(rfq=rfq)
        .select_related('supplier', 'quote_contact')
        .order_by('id')
    )

    supplier_ids = [v.supplier_id for v in vendors]
    all_contacts = []
    contact_counts = {sid: 0 for sid in supplier_ids}
    if supplier_ids:
        all_contacts = list(
            SupplierContact.objects
            .filter(supplier_id__in=supplier_ids)
            .order_by('name')
        )
        for c in all_contacts:
            contact_counts[c.supplier_id] += 1
    vendor_contact_counts = {v.id: contact_counts.get(v.supplier_id, 0) for v in vendors}

    lines = {}
    if rfq.status != RFQ.Status.DRAFT and items and vendors:
        qs = (
            RFQVendorLine.objects
            .filter(rfq_vendor__rfq=rfq, rfq_item__rfq=rfq)
            .select_related('rfq_vendor', 'rfq_item')
        )
        for ln in qs:
            lines[(ln.rfq_item_id, ln.rfq_vendor_id)] = ln

    products = Product.objects.filter(is_active=True).select_related('unit').order_by('name')
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')

    existing_product_ids = {i.product_id for i in items}
    existing_supplier_ids = {v.supplier_id for v in vendors}

    return render(request, 'procurement/rfq_detail.html', {
        'rfq': rfq,
        'items': items,
        'vendors': vendors,
        'all_contacts': all_contacts,
        'contact_counts': contact_counts,
        'vendor_contact_counts': vendor_contact_counts,
        'lines': lines,
        'products': products,
        'suppliers': suppliers,
        'existing_product_ids': existing_product_ids,
        'existing_supplier_ids': existing_supplier_ids,
    })


@login_required
def supplier_contact_json(request, supplier_pk, contact_pk):
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    contact = get_object_or_404(SupplierContact, pk=contact_pk, supplier=supplier)
    return JsonResponse({
        'ok': True,
        'contact': {
            'id': contact.pk,
            'name': contact.name,
            'phone': contact.phone or '',
            'email': contact.email or '',
        },
    })


def _rfq_item_to_dict(item: RFQItem):
    return {
        'id': item.pk,
        'product_id': item.product_id,
        'product_name': item.product.name,
        'uom': item.product.unit.symbol if item.product.unit else '',
        'qty': str(item.qty),
        'notes': item.notes or '',
    }


@login_required
@require_POST
def rfq_item_save(request, rfq_pk, pk=None):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.status != RFQ.Status.DRAFT:
        return JsonResponse({'ok': False, 'error': str(_('RFQ não está em rascunho.'))}, status=400)

    product_id = (request.POST.get('product') or '').strip()
    qty = (request.POST.get('qty') or '').strip()
    notes = (request.POST.get('notes') or '').strip()

    errors = {}
    if not product_id:
        errors['product'] = [str(_('Selecione um produto.'))]
    if not qty:
        errors['qty'] = [str(_('Informe a quantidade.'))]

    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    product = get_object_or_404(Product, pk=product_id)
    instance = None
    if pk:
        instance = get_object_or_404(RFQItem, pk=pk, rfq=rfq)

    try:
        with transaction.atomic():
            if instance:
                instance.product = product
                instance.qty = qty
                instance.notes = notes
                instance.save()
                item = instance
            else:
                item = RFQItem.objects.create(rfq=rfq, product=product, qty=qty, notes=notes)
    except IntegrityError:
        return JsonResponse({'ok': False, 'errors': {'product': [str(_('Este produto já está na lista.'))]}}, status=400)

    item = RFQItem.objects.select_related('product__unit').get(pk=item.pk)
    return JsonResponse({'ok': True, 'item': _rfq_item_to_dict(item)})


@login_required
@require_POST
def rfq_item_batch_add(request, rfq_pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.status != RFQ.Status.DRAFT:
        return JsonResponse({'ok': False, 'error': str(_('RFQ não está em rascunho.'))}, status=400)

    raw_ids = [x.strip() for x in request.POST.getlist('product') if (x or '').strip()]
    # Preserva a ordem, remove duplicados
    seen = set()
    raw_ids = [x for x in raw_ids if not (x in seen or seen.add(x))]
    if not raw_ids:
        return JsonResponse({'ok': False, 'error': str(_('Selecione ao menos 1 produto.'))}, status=400)

    created = 0
    skipped = 0
    with transaction.atomic():
        for pid in raw_ids:
            if not Product.objects.filter(pk=pid, is_active=True).exists():
                continue
            if RFQItem.objects.filter(rfq=rfq, product_id=pid).exists():
                skipped += 1
                continue
            RFQItem.objects.create(
                rfq=rfq,
                product_id=pid,
                qty=Decimal('1'),
                notes='',
            )
            created += 1

    if created == 0 and skipped:
        return JsonResponse({
            'ok': False,
            'error': str(_('Os produtos selecionados já estão no pedido.')),
            'created': 0,
            'skipped': skipped,
        }, status=400)
    if created == 0:
        return JsonResponse({
            'ok': False,
            'error': str(_('Não foi possível adicionar produtos.')),
            'created': 0,
            'skipped': 0,
        }, status=400)

    return JsonResponse({'ok': True, 'created': created, 'skipped': skipped})


@login_required
@require_POST
def rfq_item_delete(request, rfq_pk, pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.status != RFQ.Status.DRAFT:
        return JsonResponse({'ok': False, 'error': str(_('RFQ não está em rascunho.'))}, status=400)
    item = get_object_or_404(RFQItem, pk=pk, rfq=rfq)
    item.delete()
    return JsonResponse({'ok': True})


def _rfq_vendor_to_dict(v: RFQVendor):
    return {
        'id': v.pk,
        'supplier_id': v.supplier_id,
        'supplier_name': v.supplier.trade_name or v.supplier.name,
        'status': v.status,
        'status_display': v.get_status_display(),
        'sent_at': v.sent_at.isoformat() if v.sent_at else '',
    }


@login_required
@require_POST
def rfq_vendor_add(request, rfq_pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.status != RFQ.Status.DRAFT:
        return JsonResponse({'ok': False, 'error': str(_('RFQ não está em rascunho.'))}, status=400)

    supplier_id = (request.POST.get('supplier') or '').strip()
    if not supplier_id:
        return JsonResponse({'ok': False, 'errors': {'supplier': [str(_('Selecione um fornecedor.'))]}}, status=400)

    supplier = get_object_or_404(Supplier, pk=supplier_id)

    try:
        vendor = RFQVendor.objects.create(rfq=rfq, supplier=supplier)
    except IntegrityError:
        return JsonResponse({'ok': False, 'errors': {'supplier': [str(_('Este fornecedor já foi adicionado.'))]}}, status=400)

    vendor = RFQVendor.objects.select_related('supplier').get(pk=vendor.pk)
    return JsonResponse({'ok': True, 'vendor': _rfq_vendor_to_dict(vendor)})


@login_required
@require_POST
def rfq_vendor_batch_add(request, rfq_pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.status != RFQ.Status.DRAFT:
        return JsonResponse({'ok': False, 'error': str(_('RFQ não está em rascunho.'))}, status=400)

    raw_ids = [x.strip() for x in request.POST.getlist('supplier') if (x or '').strip()]
    seen = set()
    raw_ids = [x for x in raw_ids if not (x in seen or seen.add(x))]
    if not raw_ids:
        return JsonResponse({'ok': False, 'error': str(_('Selecione ao menos 1 fornecedor.'))}, status=400)

    created = 0
    skipped = 0
    with transaction.atomic():
        for sid in raw_ids:
            if not Supplier.objects.filter(pk=sid, is_active=True).exists():
                continue
            if RFQVendor.objects.filter(rfq=rfq, supplier_id=sid).exists():
                skipped += 1
                continue
            RFQVendor.objects.create(rfq=rfq, supplier_id=sid)
            created += 1

    if created == 0 and skipped:
        return JsonResponse({
            'ok': False,
            'error': str(_('Os fornecedores selecionados já participam no pedido.')),
            'created': 0,
            'skipped': skipped,
        }, status=400)
    if created == 0:
        return JsonResponse({
            'ok': False,
            'error': str(_('Não foi possível adicionar fornecedores.')),
            'created': 0,
            'skipped': 0,
        }, status=400)

    return JsonResponse({'ok': True, 'created': created, 'skipped': skipped})


@login_required
@require_POST
def rfq_vendor_remove(request, rfq_pk, pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.status != RFQ.Status.DRAFT:
        return JsonResponse({'ok': False, 'error': str(_('RFQ não está em rascunho.'))}, status=400)
    vendor = get_object_or_404(RFQVendor, pk=pk, rfq=rfq)
    vendor.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def rfq_send(request, rfq_pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.status != RFQ.Status.DRAFT:
        return JsonResponse({'ok': False, 'error': str(_('RFQ já foi enviado ou fechado.'))}, status=400)

    items = list(RFQItem.objects.filter(rfq=rfq).select_related('product'))
    vendors = list(RFQVendor.objects.filter(rfq=rfq).select_related('supplier'))
    if not items:
        return JsonResponse({'ok': False, 'error': str(_('Adicione ao menos 1 produto.'))}, status=400)
    if not vendors:
        return JsonResponse({'ok': False, 'error': str(_('Adicione ao menos 1 fornecedor.'))}, status=400)

    now = timezone.now()
    with transaction.atomic():
        rfq.status = RFQ.Status.SENT
        rfq.save(update_fields=['status'])

        for v in vendors:
            v.status = RFQVendor.Status.SENT
            v.sent_at = now
            v.save(update_fields=['status', 'sent_at'])

        # Create response lines (one per vendor per item)
        for v in vendors:
            for it in items:
                RFQVendorLine.objects.get_or_create(rfq_vendor=v, rfq_item=it)

    return JsonResponse({'ok': True})


def _sync_vendor_and_rfq_status(rfq: RFQ, vendor: RFQVendor):
    # Vendor: answered if all lines have unit_price; else stay sent
    total = RFQVendorLine.objects.filter(rfq_vendor=vendor).count()
    answered = RFQVendorLine.objects.filter(rfq_vendor=vendor, unit_price__isnull=False).count()
    if total and answered == total:
        if vendor.status != RFQVendor.Status.ANSWERED:
            vendor.status = RFQVendor.Status.ANSWERED
            vendor.save(update_fields=['status'])
    else:
        if vendor.status == RFQVendor.Status.ANSWERED:
            vendor.status = RFQVendor.Status.SENT
            vendor.save(update_fields=['status'])

    # RFQ: partial if any vendor has at least one answer
    any_answer = RFQVendorLine.objects.filter(rfq_vendor__rfq=rfq, unit_price__isnull=False).exists()
    all_answered = not RFQVendorLine.objects.filter(rfq_vendor__rfq=rfq, unit_price__isnull=True).exists()
    if all_answered:
        new_status = RFQ.Status.CLOSED
    elif any_answer:
        new_status = RFQ.Status.PARTIAL
    else:
        new_status = RFQ.Status.SENT
    if rfq.status != new_status:
        rfq.status = new_status
        rfq.save(update_fields=['status'])


@login_required
@require_POST
def rfq_vendor_header_save(request, rfq_pk, pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)

    v = get_object_or_404(RFQVendor, pk=pk, rfq=rfq)
    payment_term = (request.POST.get('payment_term') or '').strip()
    quote_validity = (request.POST.get('quote_validity') or '').strip()
    contact_id = (request.POST.get('quote_contact_id') or '').strip()

    v.payment_term = payment_term
    v.quote_validity = quote_validity or None

    if not contact_id:
        v.quote_contact = None
        v.quote_contact_name = ''
        v.quote_contact_phone = ''
        v.quote_contact_email = ''
    else:
        contact = get_object_or_404(SupplierContact, pk=contact_id, supplier=v.supplier)
        v.quote_contact = contact
        v.quote_contact_name = contact.name
        v.quote_contact_phone = contact.phone or ''
        v.quote_contact_email = contact.email or ''

    v.save(update_fields=[
        'payment_term',
        'quote_validity',
        'quote_contact',
        'quote_contact_name',
        'quote_contact_phone',
        'quote_contact_email',
    ])

    # Propaga validade padrão para as linhas (quando ainda vazia)
    if v.quote_validity is not None and rfq.status != RFQ.Status.DRAFT:
        RFQVendorLine.objects.filter(
            rfq_vendor=v,
            valid_until__isnull=True,
        ).update(valid_until=v.quote_validity)

    return JsonResponse({'ok': True})


@login_required
@require_POST
def rfq_answer_save(request, rfq_pk, vendor_pk, item_pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.status == RFQ.Status.DRAFT:
        return JsonResponse({'ok': False, 'error': str(_('Envie o RFQ antes de registrar respostas.'))}, status=400)

    vendor = get_object_or_404(RFQVendor, pk=vendor_pk, rfq=rfq)
    item = get_object_or_404(RFQItem, pk=item_pk, rfq=rfq)
    line = get_object_or_404(RFQVendorLine, rfq_vendor=vendor, rfq_item=item)

    # Empty string => None (permite resposta parcial)
    def dec_or_none(key):
        v = (request.POST.get(key) or '').strip()
        return None if v == '' else v

    unit_price = dec_or_none('unit_price')

    errors = {}
    # unit_price pode ser None (não respondeu), mas se preenchido precisa ser >= 0
    if unit_price is not None:
        try:
            if float(unit_price) < 0:
                errors['unit_price'] = [str(_('Preço inválido.'))]
        except ValueError:
            errors['unit_price'] = [str(_('Preço inválido.'))]

    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    line.unit_price = unit_price
    if line.package_qty is None:
        line.package_qty = 1
    if line.minimum_order_qty is None:
        line.minimum_order_qty = 1
    if line.lead_time_days is None:
        line.lead_time_days = 0
    if line.valid_until is None and vendor.quote_validity is not None:
        line.valid_until = vendor.quote_validity
    if unit_price is not None and not line.answered_at:
        line.answered_at = timezone.now()
    line.save()

    _sync_vendor_and_rfq_status(rfq, vendor)

    return JsonResponse({
        'ok': True,
        'line': {
            'unit_price': format_eur(line.unit_price) if line.unit_price is not None else '',
        },
    })


@login_required
@require_POST
def rfq_select_vendor(request, rfq_pk, item_pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    item = get_object_or_404(RFQItem, pk=item_pk, rfq=rfq)
    vendor_id = (request.POST.get('vendor') or '').strip()
    if not vendor_id:
        item.selected_vendor = None
        item.save(update_fields=['selected_vendor'])
        return JsonResponse({'ok': True})

    vendor = get_object_or_404(RFQVendor, pk=vendor_id, rfq=rfq)
    item.selected_vendor = vendor
    item.save(update_fields=['selected_vendor'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def rfq_apply_selected(request, rfq_pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.status == RFQ.Status.DRAFT:
        return JsonResponse({'ok': False, 'error': str(_('Envie o RFQ antes de aplicar preços.'))}, status=400)

    items = list(
        RFQItem.objects
        .filter(rfq=rfq, selected_vendor__isnull=False)
        .select_related('product', 'selected_vendor__supplier')
    )
    if not items:
        return JsonResponse({'ok': False, 'error': str(_('Selecione um fornecedor vencedor em pelo menos 1 item.'))}, status=400)

    applied = 0
    with transaction.atomic():
        for it in items:
            vendor = it.selected_vendor
            supplier = vendor.supplier
            line = RFQVendorLine.objects.filter(rfq_vendor=vendor, rfq_item=it).first()
            if not line or line.unit_price is None:
                continue  # não aplicar se não tem preço

            offer, created = ProductSupplier.objects.get_or_create(
                product=it.product,
                supplier=supplier,
                defaults={
                    'unit_price': line.unit_price,
                    'package_qty': line.package_qty or 1,
                    'minimum_order_qty': line.minimum_order_qty or 1,
                    'lead_time_days': line.lead_time_days or 0,
                    'is_active': True,
                    'is_preferred': False,
                },
            )
            old = offer.unit_price
            offer.unit_price = line.unit_price
            if line.package_qty is not None:
                offer.package_qty = line.package_qty
            if line.minimum_order_qty is not None:
                offer.minimum_order_qty = line.minimum_order_qty
            if line.lead_time_days is not None:
                offer.lead_time_days = line.lead_time_days
            if line.valid_until is not None:
                offer.valid_until = line.valid_until
            elif vendor.quote_validity is not None:
                offer.valid_until = vendor.quote_validity
            offer.is_active = True
            offer.save()

            if created or offer.unit_price != old:
                ProductSupplierPriceHistory.objects.create(
                    product_supplier=offer,
                    price=offer.unit_price,
                    changed_by=request.user,
                    note=f'{rfq.number}',
                )
            applied += 1

    return JsonResponse({'ok': True, 'applied': applied})
