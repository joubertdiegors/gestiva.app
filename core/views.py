from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

User = get_user_model()


def _default_redirect(user):
    """Retorna a URL padrão conforme o perfil do usuário."""
    if user.is_staff or user.is_superuser:
        return 'accounts:list'
    return 'planning:list'


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(_default_redirect(request.user))

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect(_default_redirect(user))
        else:
            context = {'error': 'Usuário ou senha inválidos'}
            return render(request, 'login.html', context)

    return render(request, 'login.html')


@login_required(login_url='login')
def home_view(request):
    return redirect('dashboard')


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
