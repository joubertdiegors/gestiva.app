from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from decimal import Decimal
import json

from .models import Timesheet
from projects.models import Project
from workforce.models import Collaborator
from planning.models import Planning, PlanningWorker


def _can_edit_timesheets(user):
    return user.is_staff or user.is_superuser or user.has_perm('timesheets.change_timesheet')


def _safe_next_path(request, nxt) -> str | None:
    if not nxt or not isinstance(nxt, str) or not nxt.startswith('/'):
        return None
    if nxt.startswith('//'):
        return None
    if not url_has_allowed_host_and_scheme(
        url=nxt,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return None
    return nxt


def _timesheet_may_delete_ts(ts) -> bool:
    """Pode apagar se já não houver linha de planning (mesmo dia, obra, funcionário)."""
    return not PlanningWorker.objects.filter(
        planning__date=ts.date,
        planning__project_id=ts.project_id,
        worker_id=ts.worker_id,
    ).exists()


def _can_view_timesheet_values(user):
    return user.is_superuser or user.has_perm("timesheets.view_timesheet_values")


def _parse_date_range(request):
    """
    Lê date_from e date_to da query string.
    Padrão: mês corrente completo (1º dia até hoje).
    """
    today = timezone.localdate()
    default_from = today.replace(day=1)
    default_to   = today

    raw_from = (request.GET.get('date_from') or '').strip()[:10]
    raw_to   = (request.GET.get('date_to')   or '').strip()[:10]

    try:
        date_from = datetime.strptime(raw_from, '%Y-%m-%d').date() if raw_from else default_from
    except ValueError:
        date_from = default_from

    try:
        date_to = datetime.strptime(raw_to, '%Y-%m-%d').date() if raw_to else default_to
    except ValueError:
        date_to = default_to

    if date_from > date_to:
        date_from = date_to.replace(day=1)

    return date_from, date_to


# ─────────────────────────────────────────────────────────────
# 📋 LISTA / DASHBOARD  (filtros: projeto, trabalhador, período)
# ─────────────────────────────────────────────────────────────
@login_required
def timesheet_list(request):
    import calendar as _cal
    date_from, date_to = _parse_date_range(request)

    qs = (
        Timesheet.objects
        .filter(date__gte=date_from, date__lte=date_to)
        .select_related('worker', 'worker__company', 'project', 'project__client')
        .order_by('-date', 'worker__name')
    )

    timesheets  = list(qs)
    total_hours = sum(t.computed_hours for t in timesheets)

    # Opções de filtro client-side
    seen_obra = {}; seen_worker = {}; seen_client = {}; seen_sub = {}
    all_dates = set()
    for t in timesheets:
        all_dates.add(t.date.isoformat())

        pid = t.project_id
        if pid not in seen_obra:
            seen_obra[pid] = {'id': pid, 'name': t.project.name, 'count': 0}
        seen_obra[pid]['count'] += 1

        wid = t.worker_id
        if wid not in seen_worker:
            seen_worker[wid] = {'id': wid, 'name': t.worker.name, 'count': 0}
        seen_worker[wid]['count'] += 1

        if t.project.client_id:
            cid = t.project.client_id
            if cid not in seen_client:
                seen_client[cid] = {'id': cid, 'name': t.project.client.name, 'count': 0}
            seen_client[cid]['count'] += 1

        sid = t.worker.company_id
        if sid not in seen_sub:
            seen_sub[sid] = {'id': sid, 'name': t.worker.company.name, 'count': 0}
        seen_sub[sid]['count'] += 1

    today = timezone.localdate()
    response = render(request, 'timesheets/timesheet_list.html', {
        'timesheets':     timesheets,
        'total_hours':    total_hours,
        'filter_obras':   sorted(seen_obra.values(),   key=lambda x: x['name']),
        'filter_workers': sorted(seen_worker.values(),  key=lambda x: x['name']),
        'filter_clients': sorted(seen_client.values(),  key=lambda x: x['name']),
        'filter_subs':    sorted(seen_sub.values(),    key=lambda x: x['name']),
        'all_dates_json': list(sorted(all_dates)),
        'today_str':      today.isoformat(),
        'cal_year':       today.year,
        'cal_month':      today.month,
        'date_from':      date_from.isoformat(),
        'date_to':        date_to.isoformat(),
    })
    response['Cache-Control'] = 'no-store'
    return response


@login_required
def timesheet_list_values(request):
    if not _can_view_timesheet_values(request.user):
        raise PermissionDenied

    date_from, date_to = _parse_date_range(request)

    qs = (
        Timesheet.objects
        .filter(date__gte=date_from, date__lte=date_to)
        .select_related('worker', 'worker__company', 'project', 'project__client')
        .order_by('-date', 'worker__name')
    )

    timesheets  = list(qs)
    total_hours = sum(t.computed_hours for t in timesheets)
    total_euros = Decimal('0')

    # Para registros sem snapshot (criados antes do save() automático existir),
    # busca o valor histórico vigente na data e grava no banco para não repetir.
    needs_backfill = [ts for ts in timesheets if not ts.hourly_rate_snapshot]
    if needs_backfill:
        from workforce.models import CollaboratorHourlyRate
        # Carrega todas as taxas dos workers afetados de uma vez
        worker_ids = {ts.worker_id for ts in needs_backfill}
        rates_qs = (
            CollaboratorHourlyRate.objects
            .filter(collaborator_id__in=worker_ids)
            .order_by('collaborator_id', '-start_date')
        )
        from collections import defaultdict
        rates_by_worker = defaultdict(list)
        for r in rates_qs:
            rates_by_worker[r.collaborator_id].append(r)

        to_update = []
        for ts in needs_backfill:
            for r in rates_by_worker[ts.worker_id]:
                if r.start_date <= ts.date and (r.end_date is None or r.end_date >= ts.date):
                    ts.hourly_rate_snapshot = r.hourly_rate
                    to_update.append(ts)
                    break

        if to_update:
            Timesheet.objects.bulk_update(to_update, ['hourly_rate_snapshot'])

    for ts in timesheets:
        snap = ts.hourly_rate_snapshot
        ts.cadastro_rate_base      = snap
        ts.cadastro_rate_effective = ts.effective_rate  # aplica overtime se for caso
        ts.cadastro_line_total     = ts.total_cost
        total_euros += ts.cadastro_line_total

    seen_obra = {}
    seen_worker = {}
    seen_client = {}
    seen_sub = {}
    all_dates = set()
    for t in timesheets:
        all_dates.add(t.date.isoformat())

        pid = t.project_id
        if pid not in seen_obra:
            seen_obra[pid] = {'id': pid, 'name': t.project.name, 'count': 0}
        seen_obra[pid]['count'] += 1

        wid = t.worker_id
        if wid not in seen_worker:
            seen_worker[wid] = {'id': wid, 'name': t.worker.name, 'count': 0}
        seen_worker[wid]['count'] += 1

        if t.project.client_id:
            cid = t.project.client_id
            if cid not in seen_client:
                seen_client[cid] = {'id': cid, 'name': t.project.client.name, 'count': 0}
            seen_client[cid]['count'] += 1

        sid = t.worker.company_id
        if sid not in seen_sub:
            seen_sub[sid] = {'id': sid, 'name': t.worker.company.name, 'count': 0}
        seen_sub[sid]['count'] += 1

    today = timezone.localdate()
    response = render(
        request,
        'timesheets/timesheet_list_values.html',
        {
            'timesheets':     timesheets,
            'total_hours':    total_hours,
            'total_euros':    total_euros,
            'filter_obras':   sorted(seen_obra.values(),  key=lambda x: x['name']),
            'filter_workers': sorted(seen_worker.values(), key=lambda x: x['name']),
            'filter_clients': sorted(seen_client.values(),  key=lambda x: x['name']),
            'filter_subs':    sorted(seen_sub.values(),    key=lambda x: x['name']),
            'all_dates_json': list(sorted(all_dates)),
            'today_str':      today.isoformat(),
            'cal_year':       today.year,
            'cal_month':      today.month,
            'date_from':      date_from.isoformat(),
            'date_to':        date_to.isoformat(),
        },
    )
    response['Cache-Control'] = 'no-store'
    return response


# ─────────────────────────────────────────────────────────────
# ➕ CRIAR (manual ou pré-preenchido a partir do planning)
# ─────────────────────────────────────────────────────────────
@login_required
def timesheet_create(request):
    projects = Project.objects.filter(status__in=['planning', 'active']).order_by('name')
    workers  = Collaborator.objects.filter(status='active').select_related('company').order_by('name')

    # Pré-preencher a partir de um PlanningWorker
    pw_pk = request.GET.get('planning_worker')
    prefill = {}
    planning_worker = None
    if pw_pk:
        planning_worker = PlanningWorker.objects.select_related(
            'planning__project', 'worker'
        ).filter(pk=pw_pk).first()
        if planning_worker:
            prefill = {
                'worker_id':   planning_worker.worker_id,
                'project_id':  planning_worker.planning.project_id,
                'date':        planning_worker.planning.date.isoformat(),
                'start_time':  planning_worker.start_time.strftime('%H:%M') if planning_worker.start_time else '',
                'end_time':    planning_worker.end_time.strftime('%H:%M')   if planning_worker.end_time   else '',
            }

    if request.method == 'POST':
        worker_id         = request.POST.get('worker')
        project_id        = request.POST.get('project')
        date              = request.POST.get('date')
        start_time        = request.POST.get('start_time') or None
        end_time          = request.POST.get('end_time')   or None
        hours             = request.POST.get('hours')      or None
        is_overtime       = request.POST.get('is_overtime') == 'on'
        overtime_rate     = request.POST.get('overtime_rate') or '1.50'
        notes             = request.POST.get('notes', '')
        pw_id             = request.POST.get('planning_worker_id') or None

        errors = {}
        if not worker_id:  errors['worker']  = "Campo obrigatório."
        if not project_id: errors['project'] = "Campo obrigatório."
        if not date:       errors['date']    = "Campo obrigatório."
        if not start_time and not hours:
            errors['hours'] = "Indique horas de início/fim ou total de horas."

        if not errors:
            ts = Timesheet(
                worker_id=worker_id,
                project_id=project_id,
                date=date,
                start_time=start_time or None,
                end_time=end_time or None,
                hours=Decimal(hours) if hours else None,
                is_overtime=is_overtime,
                overtime_rate=Decimal(overtime_rate),
                notes=notes,
                planning_worker_id=pw_id or None,
            )
            try:
                ts.full_clean()
                ts.save()
                next_url = request.POST.get('next') or 'timesheets:list'
                return redirect(next_url)
            except Exception as e:
                errors['__all__'] = str(e)

        return render(request, 'timesheets/timesheet_form.html', {
            'projects': projects, 'workers': workers,
            'errors': errors, 'post': request.POST,
            'planning_worker': planning_worker,
        })

    return render(request, 'timesheets/timesheet_form.html', {
        'projects': projects, 'workers': workers,
        'prefill': prefill, 'planning_worker': planning_worker,
    })


# ─────────────────────────────────────────────────────────────
# ✏️ EDITAR
# ─────────────────────────────────────────────────────────────
@login_required
def timesheet_update(request, pk):
    ts       = get_object_or_404(Timesheet, pk=pk)
    projects = Project.objects.filter(status__in=['planning', 'active']).order_by('name')
    workers  = Collaborator.objects.filter(status='active').select_related('company').order_by('name')

    if request.method == 'POST':
        ts.worker_id      = request.POST.get('worker')
        ts.project_id     = request.POST.get('project')
        ts.date           = request.POST.get('date')
        ts.start_time     = request.POST.get('start_time') or None
        ts.end_time       = request.POST.get('end_time')   or None
        h = request.POST.get('hours')
        ts.hours          = Decimal(h) if h else None
        ts.is_overtime    = request.POST.get('is_overtime') == 'on'
        ts.overtime_rate  = Decimal(request.POST.get('overtime_rate') or '1.50')
        ts.notes          = request.POST.get('notes', '')

        errors = {}
        if not ts.start_time and not ts.hours:
            errors['hours'] = "Indique horas de início/fim ou total de horas."

        if not errors:
            try:
                ts.full_clean()
                ts.save()
                return redirect('timesheets:list')
            except Exception as e:
                errors['__all__'] = str(e)

        return render(request, 'timesheets/timesheet_form.html', {
            'projects': projects, 'workers': workers,
            'errors': errors, 'ts': ts, 'editing': True,
        })

    return render(request, 'timesheets/timesheet_form.html', {
        'projects': projects, 'workers': workers,
        'ts': ts, 'editing': True,
    })


# ─────────────────────────────────────────────────────────────
# 🗑️ APAGAR
# ─────────────────────────────────────────────────────────────
@login_required
@require_POST
def timesheet_delete(request, pk):
    if not _can_edit_timesheets(request.user):
        raise PermissionDenied
    ts = get_object_or_404(Timesheet, pk=pk)
    nxt = _safe_next_path(request, (request.POST.get('next') or '').strip())
    if not _timesheet_may_delete_ts(ts):
        messages.error(
            request,
            _(
                "Não é possível apagar: este registo ainda consta do planning. "
                "Remova a atribuição no planning e volte a tentar."
            ),
        )
        return redirect(nxt or 'timesheets:list')
    ts.delete()
    return redirect(nxt or 'timesheets:list')


# ─────────────────────────────────────────────────────────────
# 📊 RESUMO POR PROJETO  (dados para relatório / futura fatura)
# ─────────────────────────────────────────────────────────────
@login_required
def timesheet_project_summary(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    timesheets = Timesheet.objects.filter(project=project).select_related(
        'worker', 'worker__company'
    ).order_by('-date', 'worker__name')

    from collections import defaultdict
    by_worker = defaultdict(lambda: {'entries': [], 'total_hours': Decimal('0'), 'total_cost': Decimal('0')})
    for ts in timesheets:
        w = by_worker[ts.worker]
        w['worker'] = ts.worker
        w['entries'].append(ts)
        w['total_hours'] += ts.computed_hours
        w['total_cost']  += ts.total_cost

    summary = sorted(by_worker.values(), key=lambda x: x['worker'].name)
    grand_hours = sum(w['total_hours'] for w in summary)
    grand_cost  = sum(w['total_cost']  for w in summary)

    return render(request, 'timesheets/timesheet_summary.html', {
        'project':     project,
        'summary':     summary,
        'grand_hours': grand_hours,
        'grand_cost':  grand_cost,
        'timesheets':  timesheets,
    })


# ─────────────────────────────────────────────────────────────
# ⚡ API — preencher timesheets em bulk a partir do planning do dia
# ─────────────────────────────────────────────────────────────
@login_required
@require_POST
def timesheet_bulk_from_planning(request, planning_pk):
    """
    Cria automaticamente um Timesheet para cada PlanningWorker presente
    no dia, usando os horários do planning como base.
    Ignora os que já têm timesheet.
    """
    planning = get_object_or_404(Planning, pk=planning_pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    created  = []
    skipped  = []

    for pw in planning.planning_workers.filter(is_present=True).select_related('worker'):
        exists = Timesheet.objects.filter(
            worker=pw.worker, project=planning.project, date=planning.date
        ).exists()
        if exists:
            skipped.append(pw.worker.name)
            continue

        ts = Timesheet(
            worker=pw.worker,
            project=planning.project,
            date=planning.date,
            start_time=pw.start_time,
            end_time=pw.end_time,
            hours=data.get('default_hours') or (None if pw.start_time else Decimal('8')),
            planning_worker=pw,
            notes=f"Auto-criado a partir do planning de {planning.date}",
        )
        ts.save()
        created.append(pw.worker.name)

    return JsonResponse({
        'created': created,
        'skipped': skipped,
        'count':   len(created),
    })


# ─────────────────────────────────────────────────────────────
# 📅 BOARD DIÁRIO — lista editável gerada a partir do planning
# ─────────────────────────────────────────────────────────────
@login_required
def timesheet_daily_board(request):
    if not _can_edit_timesheets(request.user):
        raise PermissionDenied

    import calendar as _cal
    today = timezone.localdate()

    # Dia inicial exibido no calendário: padrão = hoje
    raw_date = (request.GET.get('date') or '').strip()[:10]
    try:
        selected_date = datetime.strptime(raw_date, '%Y-%m-%d').date() if raw_date else today
    except ValueError:
        selected_date = today

    # Carrega timesheets do mês inteiro do dia selecionado (o JS filtra por dia)
    month_start = selected_date.replace(day=1)
    last_day    = _cal.monthrange(selected_date.year, selected_date.month)[1]
    month_end   = selected_date.replace(day=last_day)

    timesheets_qs = list(
        Timesheet.objects
        .filter(date__gte=month_start, date__lte=month_end)
        .select_related('worker__company', 'project__client')
        .order_by('worker__name', 'project__name')
    )

    # Planning workers do mês inteiro
    pw_index = {}
    for pw in (
        PlanningWorker.objects
        .filter(planning__date__gte=month_start, planning__date__lte=month_end)
        .select_related('worker__company', 'planning__project__client')
    ):
        key = (pw.planning.date, pw.worker_id, pw.planning.project_id)
        pw_index[key] = pw

    # 1. Linhas com timesheet já gravado
    rows = []
    seen_keys = set()
    for ts in timesheets_qs:
        key = (ts.date, ts.worker_id, ts.project_id)
        seen_keys.add(key)
        rows.append({
            'pw':            pw_index.get(key),
            'worker':        ts.worker,
            'project':       ts.project,
            'date':          ts.date,
            'date_str':      ts.date.isoformat(),
            'hours':         ts.hours,
            'notes':         ts.notes,
            'ts_id':         ts.pk,
            'can_delete_ts': key not in pw_index,
        })

    # 2. Planning workers do dia sem timesheet ainda
    for (d, wid, pid), pw in sorted(pw_index.items()):
        if (d, wid, pid) in seen_keys:
            continue
        rows.append({
            'pw':            pw,
            'worker':        pw.worker,
            'project':       pw.planning.project,
            'date':          d,
            'date_str':      d.isoformat(),
            'hours':         None,
            'notes':         '',
            'ts_id':         None,
            'can_delete_ts': False,
        })

    rows.sort(key=lambda r: (r['worker'].name, r['project'].name))

    # Dias do mês com planning (para marcar o calendário)
    all_dates_json = sorted(set(
        d.isoformat()
        for d in Planning.objects
        .filter(date__gte=month_start, date__lte=month_end)
        .values_list('date', flat=True)
        .distinct()
    ))

    # Opções de filtro client-side
    seen_obra = {}; seen_worker = {}; seen_client = {}; seen_sub = {}
    for r in rows:
        pid = r['project'].pk
        if pid not in seen_obra:
            seen_obra[pid] = {'id': pid, 'name': r['project'].name, 'count': 0}
        seen_obra[pid]['count'] += 1

        wid = r['worker'].pk
        if wid not in seen_worker:
            seen_worker[wid] = {'id': wid, 'name': r['worker'].name, 'count': 0}
        seen_worker[wid]['count'] += 1

        if r['project'].client_id:
            cid = r['project'].client_id
            if cid not in seen_client:
                seen_client[cid] = {'id': cid, 'name': r['project'].client.name, 'count': 0}
            seen_client[cid]['count'] += 1

        sid = r['worker'].company_id
        if sid not in seen_sub:
            seen_sub[sid] = {'id': sid, 'name': r['worker'].company.name, 'count': 0}
        seen_sub[sid]['count'] += 1

    response = render(request, 'timesheets/timesheet_daily_board.html', {
        'today_str':       today.isoformat(),
        'selected_date':   selected_date.isoformat(),
        'date_from_str':   selected_date.isoformat(),
        'rows':            rows,
        'all_dates_json':  all_dates_json,
        'cal_year':        selected_date.year,
        'cal_month':       selected_date.month,
        'can_edit_ts':     _can_edit_timesheets(request.user),
        'filter_obras':    sorted(seen_obra.values(),   key=lambda x: x['name']),
        'filter_workers':  sorted(seen_worker.values(),  key=lambda x: x['name']),
        'filter_clients':  sorted(seen_client.values(),  key=lambda x: x['name']),
        'filter_subs':     sorted(seen_sub.values(),    key=lambda x: x['name']),
    })
    response['Cache-Control'] = 'no-store'
    return response


@login_required
def timesheet_calendar_days(request):
    """Retorna os dias do mês que têm planning, para o calendário JS."""
    import calendar as _cal
    try:
        year  = int(request.GET.get('year',  timezone.localdate().year))
        month = int(request.GET.get('month', timezone.localdate().month))
    except (ValueError, TypeError):
        return JsonResponse({'active_days': []})
    last_day    = _cal.monthrange(year, month)[1]
    month_start = datetime(year, month, 1).date()
    month_end   = datetime(year, month, last_day).date()
    days = list(
        Planning.objects.filter(date__gte=month_start, date__lte=month_end)
        .values_list('date__day', flat=True).distinct()
    )
    return JsonResponse({'active_days': days})


@login_required
@require_POST
def timesheet_daily_board_save(request):
    """Salva em bulk as linhas do board diário."""
    if not _can_edit_timesheets(request.user):
        raise PermissionDenied
    try:
        data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    date_str = (data.get('date') or '')[:10]
    try:
        day = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Data inválida.'}, status=400)

    lines = data.get('lines', [])
    if len(lines) != 1:
        return JsonResponse({'error': 'Envie uma linha de cada vez.'}, status=400)

    line = lines[0]
    hours_raw = (line.get('hours') or '').strip()
    if not hours_raw:
        return JsonResponse({'ok': True, 'saved': 0, 'skipped': 1})

    try:
        hours_val = Decimal(hours_raw.replace(',', '.'))
    except Exception:
        return JsonResponse({'error': 'Valor de horas inválido.'}, status=400)

    try:
        worker_id  = int(line['worker_id'])
        project_id = int(line['project_id'])
    except (KeyError, TypeError, ValueError):
        return JsonResponse({'error': 'worker_id / project_id inválidos.'}, status=400)

    pw_id = line.get('pw_id')
    notes = (line.get('notes') or '').strip()

    try:
        Timesheet.objects.update_or_create(
            worker_id=worker_id,
            project_id=project_id,
            date=day,
            defaults={
                'hours':              hours_val,
                'notes':              notes,
                'planning_worker_id': int(pw_id) if pw_id else None,
            },
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'ok': True, 'saved': 1, 'skipped': 0})
