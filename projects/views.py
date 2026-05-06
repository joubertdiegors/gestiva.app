import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Product
from clients.models import ClientContact
from fleet.models import VehicleFueling
from subcontractors.models import Subcontractor
from suppliers.models import Supplier
from workforce.models import Collaborator

from accounts.decorators import perm_required
from .forms import ProjectForm
from .models import (
    Project,
    ProjectCiawParticipant,
    ProjectInteraction,
    ProjectLabourEntry,
    ProjectMaterial,
    ProjectSupplierInvoice,
    WorkRegistrationType,
)


# ── LIST ──────────────────────────────────────────────────────────────────────
@perm_required('projects.view_project')
def project_list(request):
    qs = Project.objects.select_related('client').order_by('-created_at')
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(client__name__icontains=q)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'projects/project_list.html', {
        'projects': page,
        'page_obj': page,
        'q': q,
        'status': status,
    })


# ── CREATE ────────────────────────────────────────────────────────────────────
@perm_required('projects.add_project')
def project_create(request):
    form = ProjectForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        project = form.save(commit=False)
        project.created_by = request.user
        project.save()
        form.save_m2m()
        return redirect('project_detail', pk=project.pk)
    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Create Project'})


# ── UPDATE ────────────────────────────────────────────────────────────────────
@perm_required('projects.change_project')
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == 'POST' and form.is_valid():
        project = form.save(commit=False)
        project.updated_by = request.user
        project.save()
        form.save_m2m()
        return redirect('project_detail', pk=project.pk)
    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Edit Project'})


# ── DETAIL ────────────────────────────────────────────────────────────────────
@perm_required('projects.view_project')
def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.select_related('client', 'created_by'),
        pk=pk,
    )

    interactions = project.interactions.select_related('author').order_by('-date', '-created_at')
    invoices = project.supplier_invoices.select_related('supplier').order_by('-date')
    materials = project.materials.select_related('product').order_by('-date')
    labour = project.labour_entries.select_related('worker').order_by('-date')

    # Combustível: agrega VehicleFueling pelos veículos usados no planning deste projecto
    # dentro do intervalo de datas do projecto.
    fuel_qs = VehicleFueling.objects.filter(
        vehicle__planning_assignments__planning__project=project
    ).distinct()
    if project.start_date:
        fuel_qs = fuel_qs.filter(date__gte=project.start_date)
    if project.end_date:
        fuel_qs = fuel_qs.filter(date__lte=project.end_date)

    fuel_total = fuel_qs.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')
    fuel_liters = fuel_qs.aggregate(liters=Sum('liters'))['liters'] or Decimal('0')

    # Totais por categoria
    invoices_total = sum(inv.amount_ht for inv in invoices)
    materials_total = sum(m.total for m in materials)
    labour_total = sum(e.total_cost for e in labour)
    grand_total = invoices_total + materials_total + labour_total + fuel_total

    all_suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    all_workers = Collaborator.objects.filter(status='active').order_by('name')

    # CIAW — garante raízes e passa árvore
    _ensure_ciaw_roots(project)
    ciaw_nodes = list(
        project.ciaw_participants
        .select_related('subcontractor', 'worker', 'worker__company')
        .order_by('order', 'added_at')
    )
    ciaw_nodes_json = json.dumps([_ciaw_node_json(n) for n in ciaw_nodes])

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'interactions': interactions,
        'invoices': invoices,
        'materials': materials,
        'labour': labour,
        'fuel_records': fuel_qs.select_related('vehicle', 'driver').order_by('-date')[:50],
        'fuel_total': fuel_total,
        'fuel_liters': fuel_liters,
        'invoices_total': invoices_total,
        'materials_total': materials_total,
        'labour_total': labour_total,
        'grand_total': grand_total,
        'all_suppliers': all_suppliers,
        'all_workers': all_workers,
        'interaction_type_choices': ProjectInteraction.TYPE_CHOICES,
        'invoice_status_choices': ProjectSupplierInvoice.STATUS_CHOICES,
        'ciaw_nodes': ciaw_nodes,
        'ciaw_nodes_json': ciaw_nodes_json,
    })


# ── AJAX CONTACTS ─────────────────────────────────────────────────────────────
@perm_required('projects.view_project')
def get_contacts_by_client(request):
    client_id = request.GET.get('client_id')
    contacts = ClientContact.objects.filter(client_id=client_id).values('id', 'name')
    return JsonResponse(list(contacts), safe=False)


# ── AJAX INTERACTIONS ─────────────────────────────────────────────────────────
@perm_required('projects.change_project')
@require_POST
def interaction_save(request, pk):
    project = get_object_or_404(Project, pk=pk)
    data = request.POST
    entry_pk = data.get('entry_pk') or None

    errors = {}
    subject = data.get('subject', '').strip()
    date = data.get('date', '').strip()
    if not subject:
        errors['subject'] = ['This field is required.']
    if not date:
        errors['date'] = ['This field is required.']
    if errors:
        return JsonResponse({'ok': False, 'errors': errors})

    if entry_pk:
        obj = get_object_or_404(ProjectInteraction, pk=entry_pk, project=project)
    else:
        obj = ProjectInteraction(project=project, author=request.user)

    obj.date = date
    obj.interaction_type = data.get('interaction_type', ProjectInteraction.TYPE_OTHER)
    obj.subject = subject
    obj.body = data.get('body', '').strip()
    obj.save()

    return JsonResponse({'ok': True, 'entry': {
        'id': obj.pk,
        'date': str(obj.date),
        'type': obj.get_interaction_type_display(),
        'subject': obj.subject,
        'body': obj.body,
        'author': obj.author.get_full_name() or obj.author.username,
    }})


@perm_required('projects.change_project')
@require_POST
def interaction_delete(request, pk, entry_pk):
    obj = get_object_or_404(ProjectInteraction, pk=entry_pk, project_id=pk)
    obj.delete()
    return JsonResponse({'ok': True})


# ── AJAX INVOICES ─────────────────────────────────────────────────────────────
@perm_required('projects.change_project')
@require_POST
def invoice_save(request, pk):
    project = get_object_or_404(Project, pk=pk)
    data = request.POST
    entry_pk = data.get('entry_pk') or None

    errors = {}
    supplier_id = data.get('supplier_id', '').strip()
    date = data.get('date', '').strip()
    amount_raw = data.get('amount_ht', '').strip()
    if not supplier_id:
        errors['supplier_id'] = ['This field is required.']
    if not date:
        errors['date'] = ['This field is required.']
    try:
        amount_ht = Decimal(amount_raw) if amount_raw else Decimal('0')
    except InvalidOperation:
        errors['amount_ht'] = ['Enter a valid number.']
        amount_ht = Decimal('0')
    if errors:
        return JsonResponse({'ok': False, 'errors': errors})

    if entry_pk:
        obj = get_object_or_404(ProjectSupplierInvoice, pk=entry_pk, project=project)
    else:
        obj = ProjectSupplierInvoice(project=project)

    obj.supplier = get_object_or_404(Supplier, pk=supplier_id)
    obj.invoice_ref = data.get('invoice_ref', '').strip()
    obj.description = data.get('description', '').strip()
    obj.date = date
    obj.amount_ht = amount_ht
    try:
        obj.vat_rate = Decimal(data.get('vat_rate', '21'))
    except InvalidOperation:
        obj.vat_rate = Decimal('21')
    obj.status = data.get('status', ProjectSupplierInvoice.STATUS_PENDING)
    obj.notes = data.get('notes', '').strip()
    obj.save()

    return JsonResponse({'ok': True, 'entry': {
        'id': obj.pk,
        'date': str(obj.date),
        'supplier': str(obj.supplier),
        'invoice_ref': obj.invoice_ref,
        'description': obj.description,
        'amount_ht': str(obj.amount_ht),
        'amount_ttc': str(obj.amount_ttc),
        'vat_rate': str(obj.vat_rate),
        'status': obj.status,
        'status_display': obj.get_status_display(),
    }})


@perm_required('projects.change_project')
@require_POST
def invoice_delete(request, pk, entry_pk):
    obj = get_object_or_404(ProjectSupplierInvoice, pk=entry_pk, project_id=pk)
    obj.delete()
    return JsonResponse({'ok': True})


# ── AJAX MATERIALS ────────────────────────────────────────────────────────────
@perm_required('projects.change_project')
@require_POST
def material_save(request, pk):
    project = get_object_or_404(Project, pk=pk)
    data = request.POST
    entry_pk = data.get('entry_pk') or None

    errors = {}
    description = data.get('description', '').strip()
    qty_raw = data.get('quantity', '').strip()
    price_raw = data.get('unit_price', '').strip()
    if not description:
        errors['description'] = ['This field is required.']
    try:
        quantity = Decimal(qty_raw) if qty_raw else Decimal('1')
    except InvalidOperation:
        errors['quantity'] = ['Enter a valid number.']
        quantity = Decimal('1')
    try:
        unit_price = Decimal(price_raw) if price_raw else Decimal('0')
    except InvalidOperation:
        errors['unit_price'] = ['Enter a valid number.']
        unit_price = Decimal('0')
    if errors:
        return JsonResponse({'ok': False, 'errors': errors})

    if entry_pk:
        obj = get_object_or_404(ProjectMaterial, pk=entry_pk, project=project)
    else:
        obj = ProjectMaterial(project=project)

    product_id = data.get('product_id', '').strip()
    if product_id:
        obj.product = get_object_or_404(Product, pk=product_id)
    else:
        obj.product = None

    obj.description = description
    obj.quantity = quantity
    obj.unit = data.get('unit', '').strip()
    obj.unit_price = unit_price
    date_val = data.get('date', '').strip()
    obj.date = date_val or None
    obj.notes = data.get('notes', '').strip()
    obj.save()

    return JsonResponse({'ok': True, 'entry': {
        'id': obj.pk,
        'date': str(obj.date) if obj.date else '',
        'description': obj.description,
        'quantity': str(obj.quantity),
        'unit': obj.unit,
        'unit_price': str(obj.unit_price),
        'total': str(obj.total),
    }})


@perm_required('projects.change_project')
@require_POST
def material_delete(request, pk, entry_pk):
    obj = get_object_or_404(ProjectMaterial, pk=entry_pk, project_id=pk)
    obj.delete()
    return JsonResponse({'ok': True})


# ── AJAX LABOUR ───────────────────────────────────────────────────────────────
@perm_required('projects.change_project')
@require_POST
def labour_save(request, pk):
    project = get_object_or_404(Project, pk=pk)
    data = request.POST
    entry_pk = data.get('entry_pk') or None

    errors = {}
    worker_id = data.get('worker_id', '').strip()
    date = data.get('date', '').strip()
    hours_raw = data.get('hours', '').strip()
    rate_raw = data.get('hourly_rate', '').strip()

    if not worker_id:
        errors['worker_id'] = ['This field is required.']
    if not date:
        errors['date'] = ['This field is required.']
    try:
        hours = Decimal(hours_raw) if hours_raw else Decimal('0')
    except InvalidOperation:
        errors['hours'] = ['Enter a valid number.']
        hours = Decimal('0')
    try:
        hourly_rate = Decimal(rate_raw) if rate_raw else Decimal('0')
    except InvalidOperation:
        errors['hourly_rate'] = ['Enter a valid number.']
        hourly_rate = Decimal('0')
    if errors:
        return JsonResponse({'ok': False, 'errors': errors})

    if entry_pk:
        obj = get_object_or_404(ProjectLabourEntry, pk=entry_pk, project=project)
    else:
        obj = ProjectLabourEntry(project=project)

    obj.worker = get_object_or_404(Collaborator, pk=worker_id)
    obj.date = date
    obj.hours = hours
    obj.hourly_rate = hourly_rate
    obj.is_overtime = data.get('is_overtime') == 'on'
    try:
        obj.overtime_multiplier = Decimal(data.get('overtime_multiplier', '1.5'))
    except InvalidOperation:
        obj.overtime_multiplier = Decimal('1.5')
    obj.notes = data.get('notes', '').strip()
    obj.save()

    return JsonResponse({'ok': True, 'entry': {
        'id': obj.pk,
        'date': str(obj.date),
        'worker': obj.worker.name,
        'hours': str(obj.hours),
        'hourly_rate': str(obj.hourly_rate),
        'is_overtime': obj.is_overtime,
        'total_cost': str(obj.total_cost),
    }})


@perm_required('projects.change_project')
@require_POST
def labour_delete(request, pk, entry_pk):
    obj = get_object_or_404(ProjectLabourEntry, pk=entry_pk, project_id=pk)
    obj.delete()
    return JsonResponse({'ok': True})


# ── CIAW ──────────────────────────────────────────────────────────────────────

def _ciaw_node_json(node):
    return {
        'id':        node.pk,
        'node_type': node.node_type,
        'label':     node.label,
        'url':       node.entity_url,
        'parent_id': node.parent_id,
        'order':     node.order,
        'sub_id':    node.subcontractor_id,
        'worker_id': node.worker_id,
    }


def _ensure_ciaw_roots(project):
    """Garante que o nó raiz (cliente) e o nó Construart existem."""
    root = ProjectCiawParticipant.objects.filter(
        project=project, node_type=ProjectCiawParticipant.TYPE_CLIENT
    ).first()
    if not root:
        root = ProjectCiawParticipant.objects.create(
            project=project,
            node_type=ProjectCiawParticipant.TYPE_CLIENT,
            parent=None,
            order=0,
        )
    construart = ProjectCiawParticipant.objects.filter(
        project=project, node_type=ProjectCiawParticipant.TYPE_CONSTRUART
    ).first()
    if not construart:
        construart = ProjectCiawParticipant.objects.create(
            project=project,
            node_type=ProjectCiawParticipant.TYPE_CONSTRUART,
            parent=root,
            order=0,
        )
    return root, construart


@perm_required('projects.view_project')
def ciaw_tree(request, pk):
    """Retorna a árvore CIAW completa do projeto em JSON."""
    project = get_object_or_404(Project, pk=pk)
    _ensure_ciaw_roots(project)
    nodes = list(
        project.ciaw_participants
        .select_related('subcontractor', 'worker', 'worker__company')
        .order_by('order', 'added_at')
    )
    return JsonResponse({'ok': True, 'nodes': [_ciaw_node_json(n) for n in nodes]})


@perm_required('projects.change_project')
def ciaw_search(request, pk):
    """Pesquisa subempreiteiros ou trabalhadores ainda não adicionados ao projeto."""
    project = get_object_or_404(Project, pk=pk)
    kind = request.GET.get('kind', 'subcontractor')  # 'subcontractor' | 'worker'
    q = request.GET.get('q', '').strip()

    if kind == 'subcontractor':
        already = project.ciaw_participants.filter(
            node_type=ProjectCiawParticipant.TYPE_SUBCONTRACTOR
        ).values_list('subcontractor_id', flat=True)
        qs = Subcontractor.objects.filter(status='active').exclude(pk__in=already).order_by('name')
        if q:
            qs = qs.filter(name__icontains=q)
        results = [{'id': s.pk, 'label': s.name, 'sub': s.trade_name or ''} for s in qs[:30]]

    else:  # worker
        already = project.ciaw_participants.filter(
            node_type=ProjectCiawParticipant.TYPE_WORKER
        ).values_list('worker_id', flat=True)
        qs = (Collaborator.objects
              .select_related('company')
              .filter(status='active')
              .exclude(pk__in=already)
              .order_by('name'))
        if q:
            qs = qs.filter(name__icontains=q)
        results = [
            {'id': w.pk, 'label': w.name, 'sub': w.company.name if w.company else '', 'role': w.role or ''}
            for w in qs[:30]
        ]

    return JsonResponse({'ok': True, 'results': results})


@perm_required('projects.change_project')
@require_POST
def ciaw_add(request, pk):
    """Adiciona um nó à árvore CIAW."""
    project = get_object_or_404(Project, pk=pk)
    _ensure_ciaw_roots(project)

    kind      = request.POST.get('kind')       # 'subcontractor' | 'worker'
    entity_id = request.POST.get('entity_id')
    parent_id = request.POST.get('parent_id')

    if not kind or not entity_id:
        return JsonResponse({'ok': False, 'error': 'Missing kind or entity_id'}, status=400)

    if kind == 'subcontractor':
        parent = get_object_or_404(ProjectCiawParticipant, pk=parent_id, project=project) if parent_id else None
        if parent and parent.node_type == ProjectCiawParticipant.TYPE_WORKER:
            return JsonResponse({'ok': False, 'error': 'Trabalhadores não podem ter filhos.'}, status=400)

        sub = get_object_or_404(Subcontractor, pk=entity_id)
        max_order = (
            ProjectCiawParticipant.objects
            .filter(project=project, parent=parent)
            .order_by('-order').values_list('order', flat=True).first() or -1
        )
        node = ProjectCiawParticipant.objects.create(
            project=project, parent=parent,
            node_type=ProjectCiawParticipant.TYPE_SUBCONTRACTOR,
            subcontractor=sub, order=max_order + 1,
        )

    elif kind == 'worker':
        worker = get_object_or_404(Collaborator, pk=entity_id)

        # Pai obrigatório = nó do subcontratado da empresa do trabalhador
        company = worker.company
        parent = ProjectCiawParticipant.objects.filter(
            project=project,
            node_type=ProjectCiawParticipant.TYPE_SUBCONTRACTOR,
            subcontractor=company,
        ).first()
        if not parent:
            # Auto-adiciona o subcontratado à árvore sob o nó Construart
            _, construart_node = _ensure_ciaw_roots(project)
            max_sub_order = (
                ProjectCiawParticipant.objects
                .filter(project=project, parent=construart_node)
                .order_by('-order').values_list('order', flat=True).first() or -1
            )
            parent = ProjectCiawParticipant.objects.create(
                project=project, parent=construart_node,
                node_type=ProjectCiawParticipant.TYPE_SUBCONTRACTOR,
                subcontractor=company, order=max_sub_order + 1,
            )

        max_order = (
            ProjectCiawParticipant.objects
            .filter(project=project, parent=parent)
            .order_by('-order').values_list('order', flat=True).first() or -1
        )
        node = ProjectCiawParticipant.objects.create(
            project=project, parent=parent,
            node_type=ProjectCiawParticipant.TYPE_WORKER,
            worker=worker, order=max_order + 1,
        )

    else:
        return JsonResponse({'ok': False, 'error': 'Invalid kind'}, status=400)

    # Retorna o nó adicionado e, se o pai foi auto-criado, também ele
    response_data = {'ok': True, 'node': _ciaw_node_json(node)}
    # Se o pai acabou de ser criado (não estava nos NODES do cliente), devolvê-lo também
    if kind == 'worker':
        response_data['parent_node'] = _ciaw_node_json(parent)
    return JsonResponse(response_data)


@perm_required('projects.change_project')
@require_POST
def ciaw_remove(request, pk, node_pk):
    """Remove um nó e todos os seus descendentes."""
    project = get_object_or_404(Project, pk=pk)
    node = get_object_or_404(
        ProjectCiawParticipant, pk=node_pk, project=project
    )
    # Impede remover raiz e Construart
    if node.node_type in (
        ProjectCiawParticipant.TYPE_CLIENT,
        ProjectCiawParticipant.TYPE_CONSTRUART,
    ):
        return JsonResponse({'ok': False, 'error': 'Cannot remove root nodes'}, status=400)
    node.delete()
    return JsonResponse({'ok': True})


# ── WorkRegistrationType (tabela auxiliar) ────────────────────────────────────

@perm_required('projects.view_project')
def work_registration_type_list(request):
    types = WorkRegistrationType.objects.annotate(
        project_count=Count('project')
    ).order_by('name')
    return render(request, 'projects/work_registration_type_list.html', {'types': types})


@perm_required('projects.change_project')
@require_POST
def work_registration_type_save(request, pk=None):
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'ok': False, 'errors': {'name': ['O nome é obrigatório.']}})
    if pk:
        obj = get_object_or_404(WorkRegistrationType, pk=pk)
    else:
        obj = WorkRegistrationType()
    obj.name = name
    obj.save()
    return JsonResponse({'ok': True, 'item': {'id': obj.pk, 'name': obj.name}})


@perm_required('projects.delete_project')
@require_POST
def work_registration_type_delete(request, pk):
    obj = get_object_or_404(WorkRegistrationType, pk=pk)
    count = obj.project_set.count()
    if count:
        return JsonResponse({'ok': False, 'error': f'Em uso por {count} projeto(s).'})
    obj.delete()
    return JsonResponse({'ok': True})
