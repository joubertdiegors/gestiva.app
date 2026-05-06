from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST
import json

from accounts.decorators import perm_required
from .models import Planning, PlanningBlankLine, PlanningDayOff, PlanningSubcontractor, PlanningVehicle, PlanningWorker
from projects.models import Project
from workforce.models import Collaborator
from subcontractors.models import Subcontractor
from fleet.models import Vehicle


def _parse_board_date(request):
    raw = (request.GET.get('date') or '').strip()[:10]
    if raw:
        try:
            return datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            pass
    return timezone.localdate()


@perm_required('planning.view_planning')
def planning_list(request):
    """Quadro diário: cards de obras (arrastadas manualmente) + pool de funcionários e obras."""
    selected_date = _parse_board_date(request)

    slots_per_sheet = 12

    # Plannings criados para este dia (obras arrastadas para o board)
    pw_qs = PlanningWorker.objects.select_related('worker')
    ps_qs = PlanningSubcontractor.objects.select_related('subcontractor')
    pv_qs = PlanningVehicle.objects.select_related('vehicle', 'driver')
    plannings_today = list(
        Planning.objects.filter(date=selected_date)
        .select_related('project__client', 'project__work_registration_type', 'parent')
        .prefetch_related(
            Prefetch('planning_workers', queryset=pw_qs),
            Prefetch('planning_subcontractors', queryset=ps_qs),
            Prefetch('planning_vehicles', queryset=pv_qs),
        )
        .order_by('pk')
    )

    assigned_worker_ids = set()
    for pl in plannings_today:
        for pw in pl.planning_workers.all():
            assigned_worker_ids.add(pw.worker_id)

    pool_workers = (
        Collaborator.objects.filter(company__status='active', status='active')
        .exclude(pk__in=assigned_worker_ids)
        .select_related('company')
        .order_by('name')
    )

    # IDs de projetos já no board hoje
    board_project_ids = {pl.project_id for pl in plannings_today}

    # Ordena: plannings normais na ordem de criação, extensões inseridas logo após o seu pai
    def _ordered_plannings(plannings):
        by_pk   = {pl.pk: pl for pl in plannings}
        normal  = [pl for pl in plannings if not pl.is_extension]
        ext_map = {}  # parent_pk → [extensão, ...]
        for pl in plannings:
            if pl.is_extension and pl.parent_id:
                ext_map.setdefault(pl.parent_id, []).append(pl)
        result = []
        for pl in normal:
            result.append(pl)
            for ext in ext_map.get(pl.pk, []):
                result.append(ext)
                # extensões de extensões (improvável mas seguro)
                for ext2 in ext_map.get(ext.pk, []):
                    result.append(ext2)
        return result

    plannings_ordered = _ordered_plannings(plannings_today)

    # Monta os cards do board (slots ocupados por obras)
    project_cards = []
    for pl in plannings_ordered:
        driver_ids = {pv.driver_id for pv in pl.planning_vehicles.all() if pv.driver_id}
        project_cards.append({
            'kind': 'project',
            'planning': pl,
            'project': pl.project,
            'workers': list(pl.planning_workers.all()),
            'driver_ids': driver_ids,
        })

    n_proj = len(project_cards)
    total_slots = max(slots_per_sheet, ((n_proj + slots_per_sheet - 1) // slots_per_sheet) * slots_per_sheet)

    blank_map = {}
    for row in PlanningBlankLine.objects.filter(date=selected_date):
        blank_map[(row.slot_index, row.line_index)] = row.text

    all_items = []
    for idx, card in enumerate(project_cards):
        all_items.append({
            'kind': 'project',
            'slot': idx,
            'project': card['project'],
            'planning': card['planning'],
            'workers': card['workers'],
        })
    for slot in range(n_proj, total_slots):
        lines = [blank_map.get((slot, li), '') for li in range(6)]
        all_items.append({'kind': 'blank', 'slot': slot, 'lines': lines})

    pages = [all_items[i:i + slots_per_sheet] for i in range(0, len(all_items), slots_per_sheet)]

    # Projetos para o painel lateral (ativos e em planning, excluindo os já no board)
    sidebar_projects = (
        Project.objects.filter(status__in=['active', 'planning'])
        .exclude(pk__in=board_project_ids)
        .select_related('client')
        .order_by('name')
    )

    return render(
        request,
        'planning/planning_list.html',
        {
            'board_date': selected_date,
            'board_date_str': selected_date.isoformat(),
            'pages': pages,
            'pool_workers': pool_workers,
            'sidebar_projects': sidebar_projects,
            'project_status_choices': Project.Status.choices,
        },
    )


@perm_required('planning.change_planning')
@require_POST
def board_clear_day(request):
    """Apaga todos os Plannings (e respetivos PlanningWorkers) de um dia."""
    try:
        data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    date_str = (data.get('date') or '')[:10]
    try:
        day = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Data inválida.'}, status=400)

    from timesheets.models import Timesheet
    has_hours = Timesheet.objects.filter(date=day, hours__isnull=False).exists()
    if has_hours:
        return JsonResponse({'error': 'Existem horas registadas no timesheet para este dia. Apague os registos de horas primeiro.'}, status=400)

    with transaction.atomic():
        plannings = Planning.objects.filter(date=day)
        planning_count = plannings.count()
        worker_count = PlanningWorker.objects.filter(planning__date=day).count()
        plannings.delete()  # cascade apaga PlanningWorkers via on_delete

    return JsonResponse({'ok': True, 'deleted_plannings': planning_count, 'deleted_workers': worker_count})


@perm_required('planning.change_planning')
@require_POST
def board_duplicate_planning(request):
    """Duplica todos os Plannings de um dia para o dia seguinte numa única transação."""
    try:
        data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    date_str = (data.get('date') or '')[:10]
    try:
        day = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Data inválida.'}, status=400)

    next_day = day + timedelta(days=1)

    sources = list(
        Planning.objects.filter(date=day)
        .prefetch_related('planning_workers__worker')
    )

    if not sources:
        return JsonResponse({'ok': True, 'created': 0, 'already_existed': 0,
                             'next_date': next_day.isoformat(),
                             'next_date_display': next_day.strftime('%d/%m/%Y')})

    created_count = 0
    existed_count = 0

    with transaction.atomic():
        for source in sources:
            new_planning, created = Planning.objects.get_or_create(
                project=source.project,
                date=next_day,
                defaults={'notes': source.notes},
            )
            if created:
                created_count += 1
                for pw in source.planning_workers.all():
                    PlanningWorker.objects.get_or_create(
                        planning=new_planning,
                        worker=pw.worker,
                        defaults={
                            'period': pw.period,
                            'start_time': pw.start_time,
                            'end_time': pw.end_time,
                            'role': pw.role,
                            'notes': pw.notes,
                            'is_present': True,
                        },
                    )
            else:
                existed_count += 1

    return JsonResponse({
        'ok': True,
        'created': created_count,
        'already_existed': existed_count,
        'next_date': next_day.isoformat(),
        'next_date_display': next_day.strftime('%d/%m/%Y'),
    })


@perm_required('planning.view_planning')
def board_subcontractors_search(request):
    """JSON — lista de subcontratados ativos para o painel lateral."""
    q = (request.GET.get('q') or '').strip()

    qs = Subcontractor.objects.filter(status='active').prefetch_related('contacts').order_by('name')

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(contacts__name__icontains=q)
        ).distinct()

    def get_contact_name(s):
        contacts = list(s.contacts.all())
        default = next((c for c in contacts if c.is_default), None)
        c = default or (contacts[0] if contacts else None)
        return c.name if c else ''

    subs = [
        {
            'id': s.pk,
            'name': s.name,
            'contact': get_contact_name(s),
        }
        for s in qs[:80]
    ]
    return JsonResponse({'subcontractors': subs})


@perm_required('planning.change_planning')
@require_POST
def board_assign_subcontractor(request):
    """Atribui ou remove um subcontratado de uma obra no board."""
    try:
        data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    action = data.get('action', 'add')
    date_str = (data.get('date') or '')[:10]
    try:
        day = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Data inválida.'}, status=400)

    if action == 'remove':
        ps_id = data.get('ps_id')
        if ps_id:
            PlanningSubcontractor.objects.filter(pk=ps_id).delete()
        return JsonResponse({'ok': True, 'action': 'remove'})

    sub_id = data.get('subcontractor_id')
    project_id = data.get('project_id')
    if not sub_id or not project_id:
        return JsonResponse({'error': 'Dados em falta.'}, status=400)

    sub = get_object_or_404(Subcontractor, pk=sub_id, status='active')
    project = get_object_or_404(Project, pk=project_id)

    with transaction.atomic():
        planning, _ = Planning.objects.get_or_create(
            project=project, date=day, defaults={'notes': ''}
        )
        ps, created = PlanningSubcontractor.objects.get_or_create(
            planning=planning, subcontractor=sub, defaults={'notes': ''}
        )

    return JsonResponse({
        'ok': True,
        'action': 'add',
        'ps_id': ps.pk,
        'subcontractor_id': sub.pk,
        'subcontractor_name': sub.name,
        'planning_id': planning.pk,
        'project_id': project.pk,
    })


@perm_required('planning.view_planning')
def board_workers_search(request):
    """JSON — lista de funcionários filtrados para o painel lateral."""
    q = (request.GET.get('q') or '').strip()
    date_str = (request.GET.get('date') or '')[:10]
    statuses = request.GET.getlist('status') or ['active']
    show_assigned = request.GET.get('show_assigned') == '1'

    day = None
    if date_str:
        try:
            day = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Mapa worker_id → lista de nomes de projeto (atribuições do dia)
    assigned_map = {}
    if day:
        rows = (
            PlanningWorker.objects
            .filter(planning__date=day)
            .select_related('planning__project')
            .values('worker_id', 'planning__project__name')
        )
        for row in rows:
            assigned_map.setdefault(row['worker_id'], []).append(row['planning__project__name'])

    valid_statuses = {'active', 'inactive'}
    statuses = [s for s in statuses if s in valid_statuses]
    if not statuses:
        statuses = ['active']

    qs = (
        Collaborator.objects.filter(company__status='active', status__in=statuses)
        .select_related('company')
        .order_by('name')
    )

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(company__name__icontains=q) |
            Q(role__icontains=q)
        )

    if not show_assigned:
        qs = qs.exclude(pk__in=assigned_map.keys())

    workers = []
    for w in qs[:120]:
        projects = assigned_map.get(w.pk, [])
        workers.append({
            'id': w.pk,
            'name': w.name,
            'company': w.company.name,
            'role': w.role or '',
            'status': w.status,
            'assigned_projects': projects,
        })
    return JsonResponse({'workers': workers})


@perm_required('planning.view_planning')
def board_projects_search(request):
    """JSON — lista de projetos filtrados para o painel lateral."""
    q = (request.GET.get('q') or '').strip()
    statuses = request.GET.getlist('status') or ['active', 'planning']
    date_str = (request.GET.get('date') or '')[:10]

    # Projetos já no board hoje (para excluir)
    board_ids = set()
    if date_str:
        try:
            day = datetime.strptime(date_str, '%Y-%m-%d').date()
            board_ids = set(Planning.objects.filter(date=day).values_list('project_id', flat=True))
        except ValueError:
            pass

    qs = Project.objects.select_related('client').order_by('name')

    valid_statuses = {s for s, _ in Project.Status.choices}
    statuses = [s for s in statuses if s in valid_statuses]
    if statuses:
        qs = qs.filter(status__in=statuses)

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(address__icontains=q) |
            Q(client__name__icontains=q)
        )

    qs = qs.exclude(pk__in=board_ids)

    projects = [
        {
            'id': p.pk,
            'name': p.name,
            'client': p.client.name,
            'address': p.address or '',
            'status': p.status,
            'status_label': p.get_status_display(),
        }
        for p in qs[:80]
    ]
    return JsonResponse({'projects': projects})


@perm_required('planning.change_planning')
@require_POST
def board_assign_project(request):
    """Arrasta uma obra para um slot do board — cria o Planning se não existir."""
    try:
        data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    project_id = data.get('project_id')
    date_str = (data.get('date') or '')[:10]
    action = data.get('action', 'add')  # 'add' ou 'remove'

    try:
        day = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Data inválida.'}, status=400)

    if action == 'remove':
        planning_id = data.get('planning_id')
        if planning_id:
            Planning.objects.filter(pk=planning_id, date=day).delete()
        return JsonResponse({'ok': True, 'action': 'remove'})

    project = get_object_or_404(Project, pk=project_id)
    parent_id = data.get('parent_planning_id')  # presente quando é extensão

    with transaction.atomic():
        if parent_id:
            # Extensão: cria sempre um novo Planning ligado ao pai
            parent_pl = get_object_or_404(Planning, pk=parent_id, date=day)
            planning = Planning.objects.create(
                project=project,
                date=day,
                parent=parent_pl,
                is_extension=True,
                notes='',
            )
        else:
            planning, _ = Planning.objects.get_or_create(
                project=project,
                date=day,
                is_extension=False,
                defaults={'notes': ''},
            )

    return JsonResponse({
        'ok': True,
        'action': 'add',
        'planning_id': planning.pk,
        'is_extension': planning.is_extension,
        'parent_planning_id': planning.parent_id,
        'project_id': project.pk,
        'project_name': project.name,
        'client_name': project.client.name,
        'address': project.address or '',
        'status': project.status,
        'has_work_registration': project.has_work_registration,
        'registration_type': project.work_registration_type.name if project.work_registration_type else '',
        'registration_number': project.work_registration_number or '',
    })


@perm_required('planning.change_planning')
@require_POST
def blank_line_save(request):
    try:
        data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    date_str = (data.get('date') or '')[:10]
    try:
        day = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Data inválida.'}, status=400)

    try:
        slot = int(data.get('slot_index'))
        line = int(data.get('line_index'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Slot inválido.'}, status=400)

    if slot < 0 or slot > 999 or line < 0 or line > 5:
        return JsonResponse({'error': 'Fora do intervalo.'}, status=400)

    raw = data.get('text', '')
    if not isinstance(raw, str):
        raw = str(raw)
    text = strip_tags(raw).strip()[:240]

    PlanningBlankLine.objects.update_or_create(
        date=day,
        slot_index=slot,
        line_index=line,
        defaults={'text': text},
    )
    return JsonResponse({'ok': True})


@perm_required('planning.change_planning')
@require_POST
def board_assign_worker(request):
    try:
        data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    worker_id = data.get('worker_id')
    date_str = (data.get('date') or '')[:10]
    target = data.get('target')
    project_id = data.get('project_id')

    if not worker_id or not date_str or target not in ('project', 'off', 'pool'):
        return JsonResponse({'error': 'Dados em falta.'}, status=400)

    try:
        day = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Data inválida.'}, status=400)

    worker = get_object_or_404(
        Collaborator.objects.filter(status='active', company__status='active')
        .select_related('company'),
        pk=worker_id,
    )

    with transaction.atomic():
        if target == 'pool':
            PlanningWorker.objects.filter(worker=worker, planning__date=day).delete()
            PlanningDayOff.objects.filter(worker=worker, date=day).delete()
            return JsonResponse(
                {
                    'ok': True,
                    'target': 'pool',
                    'worker_id': worker.pk,
                    'worker_name': worker.name,
                    'company_name': worker.company.name,
                }
            )

        if target == 'off':
            PlanningWorker.objects.filter(worker=worker, planning__date=day).delete()
            PlanningDayOff.objects.update_or_create(worker=worker, date=day, defaults={})
            return JsonResponse({'ok': True, 'target': 'off', 'worker_id': worker.pk, 'worker_name': worker.name})

        planning_id = data.get('planning_id')
        if not planning_id and not project_id:
            return JsonResponse({'error': 'planning_id ou project_id em falta.'}, status=400)

        if planning_id:
            planning = get_object_or_404(Planning, pk=planning_id, date=day)
        else:
            project = get_object_or_404(
                Project.objects.filter(status__in=['planning', 'active']),
                pk=project_id,
            )
            planning, _ = Planning.objects.get_or_create(
                project=project,
                date=day,
                is_extension=False,
                defaults={'notes': ''},
            )

        PlanningDayOff.objects.filter(worker=worker, date=day).delete()
        pw, _ = PlanningWorker.objects.get_or_create(
            planning=planning,
            worker=worker,
            defaults={
                'period': 'full_day',
                'is_present': True,
            },
        )

    return JsonResponse(
        {
            'ok': True,
            'target': 'project',
            'worker_id': worker.pk,
            'worker_name': worker.name,
            'pw_id': pw.pk,
            'planning_id': planning.pk,
            'project_id': planning.project_id,
        }
    )


@perm_required('planning.view_planning')
def planning_detail(request, pk):
    planning = get_object_or_404(
        Planning.objects.prefetch_related(
            'planning_workers__worker',
            'planning_workers__subcontractor',
            'planning_subcontractors__subcontractor',
        ),
        pk=pk
    )
    present_workers_count = planning.planning_workers.filter(is_present=True).count()
    collaborators = Collaborator.objects.filter(
        company__status='active'
    ).select_related('company').order_by('name')
    subcontractors = Subcontractor.objects.filter(status='active').order_by('name')

    return render(request, 'planning/planning_detail.html', {
        'planning': planning,
        'present_workers_count': present_workers_count,
        'collaborators': collaborators,
        'subcontractors': subcontractors,
        'period_choices': PlanningWorker.PERIOD_CHOICES,
    })


@perm_required('planning.add_planning')
def planning_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if request.method == 'POST':
        date = request.POST.get('date')
        notes = request.POST.get('notes', '')
        planning, _ = Planning.objects.get_or_create(
            project=project, date=date, defaults={'notes': notes}
        )
        return redirect('planning:detail', pk=planning.pk)
    return render(request, 'planning/planning_form.html', {'project': project})


@perm_required('planning.delete_planning')
@require_POST
def planning_delete(request, pk):
    from timesheets.models import Timesheet
    planning = get_object_or_404(Planning, pk=pk)
    has_hours = Timesheet.objects.filter(
        project=planning.project,
        date=planning.date,
        hours__isnull=False,
    ).exists()
    if has_hours:
        from django.contrib import messages
        messages.error(request, 'Não é possível apagar: existem horas registadas no timesheet para este planning.')
        return redirect('planning:list')
    planning.delete()
    return redirect('planning:list')


@perm_required('planning.change_planning')
@require_POST
def planning_add_worker(request, planning_pk):
    planning = get_object_or_404(Planning, pk=planning_pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)
    worker = get_object_or_404(Collaborator, pk=data.get('worker_id'))
    pw, created = PlanningWorker.objects.get_or_create(
        planning=planning, worker=worker,
        defaults={
            'subcontractor_id': data.get('subcontractor_id') or None,
            'period': data.get('period', 'full_day'),
            'start_time': data.get('start_time') or None,
            'end_time': data.get('end_time') or None,
            'role': data.get('role', ''),
            'notes': data.get('notes', ''),
            'is_present': True,
        }
    )
    if not created:
        return JsonResponse({'error': 'Worker already added.'}, status=400)
    return JsonResponse({
        'id': pw.pk, 'worker_name': worker.name,
        'period': pw.get_period_display(), 'period_key': pw.period,
        'role': pw.role, 'is_present': pw.is_present,
        'subcontractor': pw.subcontractor.name if pw.subcontractor else None,
    })


@perm_required('planning.change_planning')
@require_POST
def planning_update_worker(request, pw_pk):
    pw = get_object_or_404(PlanningWorker, pk=pw_pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)
    for field in ['is_present', 'period', 'role', 'notes']:
        if field in data:
            setattr(pw, field, data[field])
    if 'start_time' in data:
        pw.start_time = data['start_time'] or None
    if 'end_time' in data:
        pw.end_time = data['end_time'] or None
    pw.save()
    return JsonResponse({'id': pw.pk, 'is_present': pw.is_present,
                         'period': pw.get_period_display(), 'period_key': pw.period})


@perm_required('planning.change_planning')
@require_POST
def planning_remove_worker(request, pw_pk):
    get_object_or_404(PlanningWorker, pk=pw_pk).delete()
    return JsonResponse({'ok': True})


@perm_required('planning.change_planning')
@require_POST
def planning_add_subcontractor(request, planning_pk):
    planning = get_object_or_404(Planning, pk=planning_pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)
    sub = get_object_or_404(Subcontractor, pk=data.get('subcontractor_id'))
    ps, created = PlanningSubcontractor.objects.get_or_create(
        planning=planning, subcontractor=sub,
        defaults={'notes': data.get('notes', '')}
    )
    if not created:
        return JsonResponse({'error': 'Already added.'}, status=400)
    return JsonResponse({'id': ps.pk, 'subcontractor_name': sub.name, 'notes': ps.notes})


@perm_required('planning.change_planning')
@require_POST
def planning_remove_subcontractor(request, ps_pk):
    get_object_or_404(PlanningSubcontractor, pk=ps_pk).delete()
    return JsonResponse({'ok': True})


@perm_required('planning.view_planning')
def board_vehicles_search(request):
    """JSON — lista de veículos activos para o painel lateral."""
    q = (request.GET.get('q') or '').strip()
    date_str = (request.GET.get('date') or '')[:10]

    assigned_ids = set()
    if date_str:
        try:
            day = datetime.strptime(date_str, '%Y-%m-%d').date()
            assigned_ids = set(
                PlanningVehicle.objects.filter(planning__date=day)
                .values_list('vehicle_id', flat=True)
            )
        except ValueError:
            pass

    qs = Vehicle.objects.filter(status=Vehicle.STATUS_ACTIVE).select_related('category').order_by('license_plate')
    if q:
        qs = qs.filter(
            Q(license_plate__icontains=q) |
            Q(brand__icontains=q) |
            Q(model__icontains=q)
        )

    vehicles = []
    for v in qs[:80]:
        vehicles.append({
            'id': v.pk,
            'license_plate': v.license_plate,
            'brand': v.brand,
            'model': v.model,
            'assigned': v.pk in assigned_ids,
        })
    return JsonResponse({'vehicles': vehicles})


@perm_required('planning.change_planning')
@require_POST
def board_assign_vehicle(request):
    """Atribui ou remove um veículo de uma obra no board (M2M via PlanningVehicle)."""
    try:
        data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    action = data.get('action', 'add')

    if action == 'remove':
        pv_id = data.get('pv_id')
        if not pv_id:
            return JsonResponse({'error': 'pv_id em falta.'}, status=400)
        pv = get_object_or_404(PlanningVehicle, pk=pv_id)
        planning_id = pv.planning_id
        vehicle_id = pv.vehicle_id
        pv.delete()
        return JsonResponse({'ok': True, 'action': 'remove', 'planning_id': planning_id, 'vehicle_id': vehicle_id})

    # action == 'add'
    planning_id = data.get('planning_id')
    vehicle_id = data.get('vehicle_id')
    if not planning_id or not vehicle_id:
        return JsonResponse({'error': 'Dados em falta.'}, status=400)

    planning = get_object_or_404(Planning, pk=planning_id)
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, status=Vehicle.STATUS_ACTIVE)

    with transaction.atomic():
        pv, created = PlanningVehicle.objects.get_or_create(planning=planning, vehicle=vehicle)

    return JsonResponse({
        'ok': True,
        'action': 'add',
        'pv_id': pv.pk,
        'planning_id': planning.pk,
        'project_id': planning.project_id,
        'vehicle_id': vehicle.pk,
        'license_plate': vehicle.license_plate,
        'brand': vehicle.brand,
        'model': vehicle.model,
    })


@perm_required('planning.change_planning')
@require_POST
def board_set_vehicle_driver(request):
    """Define (ou limpa) o condutor de um PlanningVehicle."""
    try:
        data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    pv_id = data.get('pv_id')
    if not pv_id:
        return JsonResponse({'error': 'pv_id em falta.'}, status=400)

    pv = get_object_or_404(PlanningVehicle, pk=pv_id)
    worker_id = data.get('worker_id')  # None = limpar condutor

    if worker_id:
        driver = get_object_or_404(Collaborator, pk=worker_id)
        pv.driver = driver
    else:
        pv.driver = None

    pv.save(update_fields=['driver'])

    return JsonResponse({
        'ok': True,
        'pv_id': pv.pk,
        'worker_id': pv.driver_id,
        'worker_name': pv.driver.name if pv.driver else None,
    })
