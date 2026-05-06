import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from suppliers.models import Supplier
from projects.models import Project

from accounts.decorators import perm_required
from .models import Payable, Payment, Receivable


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@perm_required('finance.view_payable')
def dashboard(request):
    today = datetime.date.today()
    in_30  = today + datetime.timedelta(days=30)
    in_60  = today + datetime.timedelta(days=60)
    in_90  = today + datetime.timedelta(days=90)

    active_pay = Payable.objects.exclude(status__in=['paid', 'cancelled'])
    active_rec = Receivable.objects.exclude(status__in=['paid', 'cancelled'])

    overdue_payables    = active_pay.filter(due_date__lt=today).select_related('supplier', 'project')
    due_30_payables     = active_pay.filter(due_date__gte=today, due_date__lte=in_30).select_related('supplier', 'project')
    overdue_receivables = active_rec.filter(due_date__lt=today).select_related('invoice__client', 'client', 'project')
    due_30_receivables  = active_rec.filter(due_date__gte=today, due_date__lte=in_30).select_related('invoice__client', 'client', 'project')

    def _sum(qs): return qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')

    total_overdue_pay   = _sum(overdue_payables)
    total_due30_pay     = _sum(due_30_payables)
    total_overdue_rec   = _sum(overdue_receivables)
    total_due30_rec     = _sum(due_30_receivables)
    total_pending_pay   = _sum(active_pay)
    total_pending_rec   = _sum(active_rec)

    return render(request, 'finance/dashboard.html', {
        'today':               today,
        'overdue_payables':    overdue_payables[:10],
        'due_30_payables':     due_30_payables[:10],
        'overdue_receivables': overdue_receivables[:10],
        'due_30_receivables':  due_30_receivables[:10],
        'total_overdue_pay':   total_overdue_pay,
        'total_due30_pay':     total_due30_pay,
        'total_overdue_rec':   total_overdue_rec,
        'total_due30_rec':     total_due30_rec,
        'total_pending_pay':   total_pending_pay,
        'total_pending_rec':   total_pending_rec,
        'balance_30':          total_due30_rec - total_due30_pay,
    })


# ── PAYABLES LIST ─────────────────────────────────────────────────────────────
@perm_required('finance.view_payable')
def payable_list(request):
    qs = Payable.objects.select_related('supplier', 'project', 'supplier_invoice').order_by('due_date', '-amount')
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'finance/payable_list.html', {
        'payables':       qs,
        'status_filter':  status_filter,
        'status_choices': Payable.Status.choices,
        'suppliers':      Supplier.objects.filter(is_active=True).order_by('name'),
        'projects':       Project.objects.order_by('-created_at'),
        'method_choices': Payment.Method.choices,
    })


# ── AJAX: CREATE/UPDATE PAYABLE ───────────────────────────────────────────────
@perm_required('finance.change_payable')
@require_POST
def payable_save(request):
    data     = request.POST
    entry_pk = data.get('entry_pk') or None
    errors   = {}

    amount_raw = data.get('amount', '').strip()
    issue_date = data.get('issue_date', '').strip()
    if not amount_raw:
        errors['amount'] = ['Campo obrigatório.']
    if not issue_date:
        errors['issue_date'] = ['Campo obrigatório.']
    try:
        amount = Decimal(amount_raw) if amount_raw else Decimal('0')
    except InvalidOperation:
        errors['amount'] = ['Número inválido.']
        amount = Decimal('0')
    if errors:
        return JsonResponse({'ok': False, 'errors': errors})

    if entry_pk:
        obj = get_object_or_404(Payable, pk=entry_pk)
    else:
        obj = Payable(created_by=request.user)

    supplier_id = data.get('supplier_id', '').strip()
    obj.supplier    = Supplier.objects.get(pk=supplier_id) if supplier_id else None
    project_id = data.get('project_id', '').strip()
    obj.project     = Project.objects.get(pk=project_id) if project_id else None
    obj.description = data.get('description', '').strip()
    obj.reference   = data.get('reference', '').strip()
    obj.amount      = amount
    obj.issue_date  = issue_date
    obj.due_date    = data.get('due_date') or None
    obj.notes       = data.get('notes', '').strip()
    obj.save()

    return JsonResponse({'ok': True, 'entry': _payable_json(obj)})


@perm_required('finance.delete_payable')
@require_POST
def payable_delete(request, pk):
    obj = get_object_or_404(Payable, pk=pk)
    if obj.payments.exists():
        return JsonResponse({'ok': False, 'error': 'Possui pagamentos. Elimine os pagamentos primeiro.'})
    obj.delete()
    return JsonResponse({'ok': True})


# ── RECEIVABLES LIST ──────────────────────────────────────────────────────────
@perm_required('finance.view_receivable')
def receivable_list(request):
    qs = Receivable.objects.select_related('invoice', 'client', 'project').order_by('due_date', '-amount')
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'finance/receivable_list.html', {
        'receivables':    qs,
        'status_filter':  status_filter,
        'status_choices': Receivable.Status.choices,
        'method_choices': Payment.Method.choices,
    })


# ── AJAX: PAYMENT SAVE (works for both Payable and Receivable) ────────────────
@perm_required('finance.change_payable')
@require_POST
def payment_save(request):
    data     = request.POST
    entry_pk = data.get('entry_pk') or None
    errors   = {}

    amount_raw = data.get('amount', '').strip()
    date_raw   = data.get('date', '').strip()
    if not amount_raw:
        errors['amount'] = ['Campo obrigatório.']
    if not date_raw:
        errors['date'] = ['Campo obrigatório.']
    try:
        amount = Decimal(amount_raw) if amount_raw else Decimal('0')
    except InvalidOperation:
        errors['amount'] = ['Número inválido.']
        amount = Decimal('0')
    if errors:
        return JsonResponse({'ok': False, 'errors': errors})

    payable_id    = data.get('payable_id', '').strip()
    receivable_id = data.get('receivable_id', '').strip()

    if entry_pk:
        pmt = get_object_or_404(Payment, pk=entry_pk)
    else:
        pmt = Payment(created_by=request.user)
        if payable_id:
            pmt.payable_id = payable_id
        elif receivable_id:
            pmt.receivable_id = receivable_id

    pmt.date      = date_raw
    pmt.amount    = amount
    pmt.method    = data.get('method', Payment.Method.TRANSFER)
    pmt.reference = data.get('reference', '').strip()
    pmt.notes     = data.get('notes', '').strip()
    pmt.save()  # save() triggers sync_status on parent

    # Return updated parent
    if pmt.payable_id:
        parent = Payable.objects.select_related('supplier', 'project').get(pk=pmt.payable_id)
        parent_json = _payable_json(parent)
    else:
        parent = Receivable.objects.select_related('invoice', 'client', 'project').get(pk=pmt.receivable_id)
        parent_json = _receivable_json(parent)

    return JsonResponse({'ok': True, 'payment': {
        'id':        pmt.pk,
        'date':      str(pmt.date),
        'amount':    str(pmt.amount),
        'method':    pmt.get_method_display(),
        'reference': pmt.reference,
    }, 'parent': parent_json})


@perm_required('finance.delete_payable')
@require_POST
def payment_delete(request, pk):
    pmt = get_object_or_404(Payment, pk=pk)
    payable_id    = pmt.payable_id
    receivable_id = pmt.receivable_id
    pmt.delete()  # delete() triggers sync_status on parent

    if payable_id:
        parent = Payable.objects.select_related('supplier', 'project').get(pk=payable_id)
        return JsonResponse({'ok': True, 'parent': _payable_json(parent)})
    else:
        parent = Receivable.objects.select_related('invoice', 'client', 'project').get(pk=receivable_id)
        return JsonResponse({'ok': True, 'parent': _receivable_json(parent)})


# ── Helpers ───────────────────────────────────────────────────────────────────
def _payable_json(obj):
    return {
        'id':             obj.pk,
        'supplier':       str(obj.supplier) if obj.supplier else '—',
        'project':        obj.project.name if obj.project else '—',
        'description':    obj.description,
        'reference':      obj.reference,
        'amount':         str(obj.amount),
        'amount_paid':    str(obj.amount_paid),
        'amount_remaining': str(obj.amount_remaining),
        'issue_date':     str(obj.issue_date),
        'due_date':       str(obj.due_date) if obj.due_date else '',
        'status':         obj.status,
        'status_display': obj.get_status_display(),
        'is_overdue':     obj.is_overdue,
    }


def _receivable_json(obj):
    return {
        'id':               obj.pk,
        'invoice_number':   obj.invoice.number,
        'client':           obj.client.name,
        'project':          obj.project.name if obj.project else '—',
        'amount':           str(obj.amount),
        'amount_paid':      str(obj.amount_paid),
        'amount_remaining': str(obj.amount_remaining),
        'issue_date':       str(obj.issue_date),
        'due_date':         str(obj.due_date) if obj.due_date else '',
        'status':           obj.status,
        'status_display':   obj.get_status_display(),
        'is_overdue':       obj.is_overdue,
    }
