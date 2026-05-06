from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from accounts.decorators import perm_required
from .forms import (
    ContractForm, ContractLineForm,
    AddendumForm, AddendumLineForm,
    StatementForm, StatementLineForm,
    SubcontractorInvoiceForm,
)
from .models import (
    Contract, ContractLine,
    Addendum, AddendumLine,
    Statement, StatementLine,
    SubcontractorInvoice,
)


# ══ CONTRACTS ═════════════════════════════════════════════════════════════════

@perm_required('contracts.view_contract')
def contract_list(request):
    qs = (
        Contract.objects
        .select_related('client', 'subcontractor', 'supplier', 'project')
        .order_by('-created_at')
    )
    ctype  = request.GET.get('type', '').strip()
    status = request.GET.get('status', '').strip()
    search = request.GET.get('q', '').strip()
    if ctype:
        qs = qs.filter(contract_type=ctype)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(title__icontains=search)
    return render(request, 'contracts/contract_list.html', {
        'contracts':       qs,
        'type_choices':    Contract.TYPE_CHOICES,
        'status_choices':  Contract.STATUS_CHOICES,
        'filter_type':     ctype,
        'filter_status':   status,
        'filter_q':        search,
    })


@perm_required('contracts.add_contract')
def contract_create(request):
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            return redirect('contracts:detail', pk=obj.pk)
    else:
        form = ContractForm(initial={
            'contract_type': request.GET.get('type', 'client'),
            'client':        request.GET.get('client'),
        })
    return render(request, 'contracts/contract_form.html', {'form': form, 'is_create': True})


@perm_required('contracts.view_contract')
def contract_detail(request, pk):
    contract = get_object_or_404(
        Contract.objects
        .select_related('client', 'subcontractor', 'supplier', 'project', 'created_by', 'updated_by')
        .prefetch_related('lines', 'addenda__subcontractor', 'addenda__project', 'statements'),
        pk=pk,
    )
    line_form = ContractLineForm()
    return render(request, 'contracts/contract_detail.html', {
        'contract':  contract,
        'line_form': line_form,
    })


@perm_required('contracts.change_contract')
def contract_edit(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.method == 'POST':
        form = ContractForm(request.POST, instance=contract)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            return redirect('contracts:detail', pk=pk)
    else:
        form = ContractForm(instance=contract)
    return render(request, 'contracts/contract_form.html', {
        'form': form, 'contract': contract, 'is_create': False,
    })


@perm_required('contracts.delete_contract')
@require_POST
def contract_delete(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    contract.delete()
    return redirect('contracts:list')


# ── Contract lines ─────────────────────────────────────────────────────────────

@perm_required('contracts.change_contract')
@require_POST
def contract_line_add(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    form = ContractLineForm(request.POST)
    if form.is_valid():
        line = form.save(commit=False)
        line.contract = contract
        # Auto-order: place after last line
        last = contract.lines.order_by('-order').first()
        line.order = (last.order + 10) if last else 10
        line.save()
    return redirect('contracts:detail', pk=pk)


@perm_required('contracts.change_contract')
@require_POST
def contract_line_delete(request, pk, line_pk):
    get_object_or_404(ContractLine, pk=line_pk, contract_id=pk).delete()
    return redirect('contracts:detail', pk=pk)


# ══ ADDENDA ═══════════════════════════════════════════════════════════════════

@perm_required('contracts.view_contract')
def addendum_list(request):
    qs = (
        Addendum.objects
        .select_related('contract__client', 'subcontractor', 'project')
        .order_by('-created_at')
    )
    status = request.GET.get('status', '').strip()
    search = request.GET.get('q', '').strip()
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(title__icontains=search) | qs.filter(subcontractor__name__icontains=search)
    return render(request, 'contracts/addendum_list.html', {
        'addenda':        qs,
        'status_choices': Addendum.STATUS_CHOICES,
        'filter_status':  status,
        'filter_q':       search,
    })


@perm_required('contracts.add_contract')
def addendum_create(request, contract_pk=None):
    contract = get_object_or_404(Contract, pk=contract_pk) if contract_pk else None
    if request.method == 'POST':
        form = AddendumForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if contract:
                obj.contract = contract
            obj.created_by = request.user
            obj.save()
            # Copy lines from contract if requested
            if request.POST.get('copy_lines') and obj.contract:
                _copy_contract_lines_to_addendum(obj.contract, obj)
            return redirect('contracts:addendum_detail', pk=obj.pk)
    else:
        form = AddendumForm()
    return render(request, 'contracts/addendum_form.html', {
        'form': form, 'contract': contract, 'is_create': True,
    })


def _copy_contract_lines_to_addendum(contract, addendum):
    for cl in contract.lines.order_by('order'):
        AddendumLine.objects.create(
            addendum             = addendum,
            order                = cl.order,
            line_type            = cl.line_type,
            description          = cl.description,
            detail               = cl.detail,
            quantity             = cl.quantity,
            unit                 = cl.unit,
            unit_price           = cl.unit_price,
            discount_percent     = cl.discount_percent,
            vat_rate             = cl.vat_rate,
            source_contract_line = cl,
        )


@perm_required('contracts.view_contract')
def addendum_detail(request, pk):
    addendum = get_object_or_404(
        Addendum.objects
        .select_related('contract__client', 'subcontractor', 'project', 'created_by', 'updated_by')
        .prefetch_related('lines', 'statements', 'subcontractor_invoices'),
        pk=pk,
    )
    line_form    = AddendumLineForm()
    invoice_form = SubcontractorInvoiceForm()
    # Limit statement choices to this addendum
    invoice_form.fields['statement'].queryset = addendum.statements.all()
    return render(request, 'contracts/addendum_detail.html', {
        'addendum':     addendum,
        'line_form':    line_form,
        'invoice_form': invoice_form,
    })


@perm_required('contracts.change_contract')
def addendum_edit(request, pk):
    addendum = get_object_or_404(Addendum, pk=pk)
    if request.method == 'POST':
        form = AddendumForm(request.POST, instance=addendum)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            return redirect('contracts:addendum_detail', pk=pk)
    else:
        form = AddendumForm(instance=addendum)
    return render(request, 'contracts/addendum_form.html', {
        'form': form, 'addendum': addendum, 'contract': addendum.contract, 'is_create': False,
    })


@perm_required('contracts.delete_contract')
@require_POST
def addendum_delete(request, pk):
    addendum = get_object_or_404(Addendum, pk=pk)
    contract_pk = addendum.contract_id
    addendum.delete()
    return redirect('contracts:detail', pk=contract_pk)


# ── Addendum lines ─────────────────────────────────────────────────────────────

@perm_required('contracts.change_contract')
@require_POST
def addendum_line_add(request, pk):
    addendum = get_object_or_404(Addendum, pk=pk)
    form = AddendumLineForm(request.POST)
    if form.is_valid():
        line = form.save(commit=False)
        line.addendum = addendum
        last = addendum.lines.order_by('-order').first()
        line.order = (last.order + 10) if last else 10
        line.save()
    return redirect('contracts:addendum_detail', pk=pk)


@perm_required('contracts.change_contract')
@require_POST
def addendum_line_delete(request, pk, line_pk):
    get_object_or_404(AddendumLine, pk=line_pk, addendum_id=pk).delete()
    return redirect('contracts:addendum_detail', pk=pk)


# ── Copy contract lines to addendum ───────────────────────────────────────────

@perm_required('contracts.change_contract')
@require_POST
def addendum_copy_lines(request, pk):
    addendum = get_object_or_404(Addendum, pk=pk)
    if addendum.contract_id:
        _copy_contract_lines_to_addendum(addendum.contract, addendum)
    return redirect('contracts:addendum_detail', pk=pk)


# ══ STATEMENTS (EA) ═══════════════════════════════════════════════════════════

@perm_required('contracts.view_contract')
def statement_list(request):
    qs = (
        Statement.objects
        .select_related('contract__client', 'addendum__subcontractor')
        .order_by('-issue_date')
    )
    stype  = request.GET.get('type', '').strip()
    status = request.GET.get('status', '').strip()
    if stype:
        qs = qs.filter(statement_type=stype)
    if status:
        qs = qs.filter(status=status)
    return render(request, 'contracts/statement_list.html', {
        'statements':     qs,
        'type_choices':   Statement.TYPE_CHOICES,
        'status_choices': Statement.STATUS_CHOICES,
        'filter_type':    stype,
        'filter_status':  status,
    })


@perm_required('contracts.add_contract')
def statement_create(request, contract_pk=None, addendum_pk=None):
    contract = get_object_or_404(Contract, pk=contract_pk) if contract_pk else None
    addendum = get_object_or_404(Addendum, pk=addendum_pk) if addendum_pk else None

    if request.method == 'POST':
        form = StatementForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            return redirect('contracts:statement_detail', pk=obj.pk)
    else:
        initial = {}
        if contract:
            initial = {'statement_type': Statement.TYPE_CLIENT, 'contract': contract}
        elif addendum:
            initial = {'statement_type': Statement.TYPE_SUBCONTRACTOR, 'addendum': addendum}
        form = StatementForm(initial=initial)

    return render(request, 'contracts/statement_form.html', {
        'form': form, 'contract': contract, 'addendum': addendum, 'is_create': True,
    })


@perm_required('contracts.view_contract')
def statement_detail(request, pk):
    statement = get_object_or_404(
        Statement.objects
        .select_related(
            'contract__client', 'contract__project',
            'addendum__subcontractor', 'addendum__project',
            'created_by', 'updated_by',
        )
        .prefetch_related('lines', 'subcontractor_invoices'),
        pk=pk,
    )
    line_form = StatementLineForm()
    return render(request, 'contracts/statement_detail.html', {
        'statement': statement,
        'line_form': line_form,
    })


@perm_required('contracts.change_contract')
def statement_edit(request, pk):
    statement = get_object_or_404(Statement, pk=pk)
    if request.method == 'POST':
        form = StatementForm(request.POST, instance=statement)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            return redirect('contracts:statement_detail', pk=pk)
    else:
        form = StatementForm(instance=statement)
    return render(request, 'contracts/statement_form.html', {
        'form': form, 'statement': statement, 'is_create': False,
    })


@perm_required('contracts.delete_contract')
@require_POST
def statement_delete(request, pk):
    statement = get_object_or_404(Statement, pk=pk)
    statement.delete()
    return redirect('contracts:statement_list')


@perm_required('contracts.change_contract')
@require_POST
def statement_send(request, pk):
    """Mark statement as sent and create finance entry if client EA."""
    statement = get_object_or_404(Statement, pk=pk)
    if statement.status == Statement.STATUS_DRAFT:
        statement.status = Statement.STATUS_SENT
        statement.updated_by = request.user
        statement.save(update_fields=['status', 'updated_by', 'updated_at'])
        if statement.statement_type == Statement.TYPE_CLIENT:
            _create_receivable(statement)
    return redirect('contracts:statement_detail', pk=pk)


def _create_receivable(statement):
    from finance.models import Receivable
    if hasattr(statement, 'receivable'):
        return
    client = statement.contract.client if statement.contract_id else None
    if not client:
        return
    Receivable.objects.create(
        statement  = statement,
        client     = client,
        project    = statement.project,
        amount     = statement.total,
        issue_date = statement.issue_date,
        due_date   = statement.due_date,
    )


# ── Statement lines ────────────────────────────────────────────────────────────

@perm_required('contracts.change_contract')
@require_POST
def statement_line_add(request, pk):
    statement = get_object_or_404(Statement, pk=pk)
    form = StatementLineForm(request.POST)
    if form.is_valid():
        line = form.save(commit=False)
        line.statement = statement
        last = statement.lines.order_by('-order').first()
        line.order = (last.order + 10) if last else 10
        line.save()
    return redirect('contracts:statement_detail', pk=pk)


@perm_required('contracts.change_contract')
@require_POST
def statement_line_delete(request, pk, line_pk):
    get_object_or_404(StatementLine, pk=line_pk, statement_id=pk).delete()
    return redirect('contracts:statement_detail', pk=pk)


# ══ SUBCONTRACTOR INVOICES ════════════════════════════════════════════════════

@perm_required('contracts.add_contract')
def subinvoice_create(request, addendum_pk):
    addendum = get_object_or_404(Addendum, pk=addendum_pk)
    if request.method == 'POST':
        form = SubcontractorInvoiceForm(request.POST)
        form.fields['statement'].queryset = addendum.statements.filter(
            statement_type=Statement.TYPE_SUBCONTRACTOR
        )
        if form.is_valid():
            with transaction.atomic():
                obj = form.save(commit=False)
                obj.addendum   = addendum
                obj.created_by = request.user
                obj.save()
                obj.create_payable()
            return redirect('contracts:addendum_detail', pk=addendum_pk)
    else:
        form = SubcontractorInvoiceForm()
        form.fields['statement'].queryset = addendum.statements.filter(
            statement_type=Statement.TYPE_SUBCONTRACTOR
        )
    return render(request, 'contracts/subinvoice_form.html', {
        'form': form, 'addendum': addendum,
    })


@perm_required('contracts.delete_contract')
@require_POST
def subinvoice_delete(request, pk):
    inv = get_object_or_404(SubcontractorInvoice, pk=pk)
    addendum_pk = inv.addendum_id
    if inv.payable:
        inv.payable.delete()
    inv.delete()
    return redirect('contracts:addendum_detail', pk=addendum_pk)


# ══ VIEWS BY ENTITY ═══════════════════════════════════════════════════════════

@perm_required('contracts.view_contract')
def client_contracts(request, client_pk):
    from clients.models import Client
    client = get_object_or_404(Client, pk=client_pk)
    contracts = (
        Contract.objects.filter(client=client, contract_type=Contract.TYPE_CLIENT)
        .prefetch_related('addenda')
        .order_by('-created_at')
    )
    return render(request, 'contracts/entity_contracts.html', {
        'entity': client,
        'entity_type': 'client',
        'entity_name': client.name,
        'contracts': contracts,
        'create_url': f"/pt-br/contracts/create/?type=client&client={client_pk}",
        'back_url': f"/pt-br/clients/{client_pk}/",
    })


@perm_required('contracts.view_contract')
def subcontractor_contracts(request, sub_pk):
    from subcontractors.models import Subcontractor
    sub = get_object_or_404(Subcontractor, pk=sub_pk)
    addenda = (
        Addendum.objects.filter(subcontractor=sub)
        .select_related('contract', 'project')
        .order_by('-created_at')
    )
    return render(request, 'contracts/subcontractor_contracts.html', {
        'sub': sub,
        'addenda': addenda,
    })


@perm_required('contracts.view_contract')
def supplier_contracts(request, supplier_pk):
    from suppliers.models import Supplier
    from .models import SupplierContract
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    contracts = SupplierContract.objects.filter(supplier=supplier).order_by('-created_at')
    return render(request, 'contracts/supplier_contracts.html', {
        'supplier': supplier,
        'contracts': contracts,
    })


# ── Supplier Contract CRUD ─────────────────────────────────────────────────────

@perm_required('contracts.add_contract')
def supplier_contract_create(request, supplier_pk):
    from suppliers.models import Supplier
    from .models import SupplierContract, SupplierContractLine
    from .forms import SupplierContractForm
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    if request.method == 'POST':
        form = SupplierContractForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.supplier   = supplier
            obj.created_by = request.user
            obj.save()
            return redirect('contracts:supplier_contract_detail', pk=obj.pk)
    else:
        form = SupplierContractForm()
    return render(request, 'contracts/supplier_contract_form.html', {
        'form': form, 'supplier': supplier, 'is_create': True,
    })


@perm_required('contracts.view_contract')
def supplier_contract_detail(request, pk):
    from .models import SupplierContract, SupplierContractLine
    from .forms import SupplierContractLineForm
    contract = get_object_or_404(
        SupplierContract.objects.select_related('supplier', 'created_by').prefetch_related('lines'),
        pk=pk,
    )
    line_form = SupplierContractLineForm()
    return render(request, 'contracts/supplier_contract_detail.html', {
        'contract': contract, 'line_form': line_form,
    })


@perm_required('contracts.change_contract')
def supplier_contract_edit(request, pk):
    from .models import SupplierContract
    from .forms import SupplierContractForm
    contract = get_object_or_404(SupplierContract, pk=pk)
    if request.method == 'POST':
        form = SupplierContractForm(request.POST, instance=contract)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            return redirect('contracts:supplier_contract_detail', pk=pk)
    else:
        form = SupplierContractForm(instance=contract)
    return render(request, 'contracts/supplier_contract_form.html', {
        'form': form, 'contract': contract, 'supplier': contract.supplier, 'is_create': False,
    })


@perm_required('contracts.delete_contract')
@require_POST
def supplier_contract_delete(request, pk):
    from .models import SupplierContract
    obj = get_object_or_404(SupplierContract, pk=pk)
    supplier_pk = obj.supplier_id
    obj.delete()
    return redirect('contracts:supplier_contracts', supplier_pk=supplier_pk)


@perm_required('contracts.change_contract')
@require_POST
def supplier_line_add(request, pk):
    from .models import SupplierContract, SupplierContractLine
    from .forms import SupplierContractLineForm
    contract = get_object_or_404(SupplierContract, pk=pk)
    form = SupplierContractLineForm(request.POST)
    if form.is_valid():
        line = form.save(commit=False)
        line.contract = contract
        last = contract.lines.order_by('-order').first()
        line.order = (last.order + 10) if last else 10
        line.save()
    return redirect('contracts:supplier_contract_detail', pk=pk)


@perm_required('contracts.change_contract')
@require_POST
def supplier_line_delete(request, pk, line_pk):
    from .models import SupplierContractLine
    get_object_or_404(SupplierContractLine, pk=line_pk, contract_id=pk).delete()
    return redirect('contracts:supplier_contract_detail', pk=pk)
