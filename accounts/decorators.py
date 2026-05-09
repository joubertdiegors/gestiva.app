from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required as _perm_required
from django.shortcuts import redirect
from django.urls import reverse


def perm_required(perm):
    """Combina login_required + permission_required com raise_exception=True."""
    def decorator(view_func):
        view_func = _perm_required(perm, raise_exception=True)(view_func)
        view_func = login_required(view_func)
        return view_func
    return decorator


def otp_required(view_func=None, *, force=False):
    """
    Garante que o utilizador autenticou OTP nesta sessão.

    - Se `OTP_REQUIRED_FOR_STAFF=True` (default em produção), staff/superusers
      sem TOTP confirmado são redirigidos para a página de inscrição.
    - `force=True` aplica a TODOS os utilizadores autenticados — usar em
      rotas hiper-sensíveis (export financeiro completo, p.ex.).
    - Se `OTP_REQUIRED_FOR_STAFF=False` em DEV, decorador é no-op para staff
      sem TOTP — não estorva desenvolvimento local.
    """
    def decorator(func):
        @wraps(func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(settings.LOGIN_URL or 'login')

            requires = force or (
                getattr(settings, 'OTP_REQUIRED_FOR_STAFF', True)
                and (user.is_staff or user.is_superuser)
            )

            if requires and not user.is_verified():
                from django_otp import devices_for_user
                has_device = any(devices_for_user(user, confirmed=True))
                if has_device:
                    return redirect(reverse('accounts:otp_verify') + f'?next={request.path}')
                return redirect(reverse('accounts:otp_setup'))

            return func(request, *args, **kwargs)

        return login_required(_wrapped)

    if view_func is not None:
        return decorator(view_func)
    return decorator
