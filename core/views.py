from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.db import connection, DatabaseError
from django.db.models import Q
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core import __version__
from .i18n_redirect import redirect_with_cookie_language

User = get_user_model()


@csrf_exempt
@never_cache
@require_http_methods(["GET", "HEAD"])
def healthz(request):
    """
    Liveness/readiness probe usada por UptimeRobot/Better Stack.

    - 200 → app responde e DB aceita uma query trivial.
    - 503 → DB inacessível (pool esgotado, host fora, etc.).
    """
    db_ok = True
    db_error = ''
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
    except DatabaseError as exc:
        db_ok = False
        db_error = str(exc)

    payload = {
        'status': 'ok' if db_ok else 'degraded',
        'version': __version__,
        'database': 'ok' if db_ok else 'error',
    }
    if not db_ok:
        payload['database_error'] = db_error
    return JsonResponse(payload, status=200 if db_ok else 503)


def root_redirect(request):
    """Bare '/' → localized home (respects cookie / Accept-Language via LocaleMiddleware)."""
    return HttpResponseRedirect(reverse('home'))


def _default_redirect(user):
    """Retorna a URL padrão conforme o perfil do usuário."""
    if user.is_staff or user.is_superuser:
        return 'accounts:list'
    return 'planning:list'


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect_with_cookie_language(request, _default_redirect(request.user))

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect_with_cookie_language(request, _default_redirect(user))
        else:
            context = {'error': 'Usuário ou senha inválidos'}
            return render(request, 'login.html', context)

    return render(request, 'login.html')


@login_required(login_url='login')
def home_view(request):
    return redirect_with_cookie_language(request, 'dashboard')


@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'dashboard.html')


@require_http_methods(["GET", "POST"])
def setup_view(request):
    if User.objects.exists():
        return redirect('login')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if not username:
            error = 'Informe um nome de usuário.'
        elif len(password) < 8:
            error = 'A senha deve ter ao menos 8 caracteres.'
        elif password != password2:
            error = 'As senhas não coincidem.'
        else:
            user = User.objects.create_superuser(username=username, password=password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            return redirect('login')

    return render(request, 'setup.html', {'error': error})


@login_required(login_url='login')
def global_search(request):
    q = request.GET.get('q', '').strip()
    results = []

    if len(q) >= 2:
        from clients.models import Client
        from projects.models import Project
        from workforce.models import Collaborator
        from subcontractors.models import Subcontractor
        from suppliers.models import Supplier

        for obj in Client.objects.filter(
            Q(name__icontains=q) | Q(trade_name__icontains=q) | Q(vat_number__icontains=q)
        )[:5]:
            results.append({
                'label': obj.trade_name or obj.name,
                'sublabel': obj.vat_number or '',
                'url': reverse('clients:detail', args=[obj.pk]),
                'type': 'client',
            })

        for obj in Project.objects.filter(
            Q(name__icontains=q)
        ).select_related('client')[:5]:
            results.append({
                'label': obj.name,
                'sublabel': obj.client.trade_name if obj.client else '',
                'url': reverse('projects:project_detail', args=[obj.pk]),
                'type': 'project',
            })

        for obj in Collaborator.objects.filter(
            Q(name__icontains=q) | Q(id_number__icontains=q)
        )[:5]:
            results.append({
                'label': obj.name,
                'sublabel': obj.role or '',
                'url': reverse('workforce:detail', args=[obj.pk]),
                'type': 'collaborator',
            })

        for obj in Subcontractor.objects.filter(
            Q(name__icontains=q) | Q(trade_name__icontains=q) | Q(vat_number__icontains=q)
        )[:5]:
            results.append({
                'label': obj.trade_name or obj.name,
                'sublabel': obj.vat_number or '',
                'url': reverse('subcontractors:detail', args=[obj.pk]),
                'type': 'subcontractor',
            })

        for obj in Supplier.objects.filter(
            Q(name__icontains=q) | Q(trade_name__icontains=q) | Q(vat_number__icontains=q)
        )[:5]:
            results.append({
                'label': obj.trade_name or obj.name,
                'sublabel': obj.vat_number or '',
                'url': reverse('suppliers:detail', args=[obj.pk]),
                'type': 'supplier',
            })

    return JsonResponse({'results': results})
