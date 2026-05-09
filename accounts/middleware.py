"""
Middleware de gating 2FA para staff/superusers (Sprint 5).

Quando `OTP_REQUIRED_FOR_STAFF=True` (default em produção), qualquer
utilizador `is_staff`/`is_superuser` que ainda não tenha sessão verificada
por TOTP é redirecionado para:

  - /accounts/2fa/setup/    se ainda não tem device confirmado
  - /accounts/2fa/verify/   se já tem mas a sessão é nova

Em DEV (`DEBUG=True`) o setting cai para False por default, portanto este
middleware é no-op localmente. Para forçar 2FA em DEV, define
`OTP_REQUIRED_FOR_STAFF=True` no .env.

Não bloqueia:
  - URLs do próprio fluxo 2FA (loop infinito).
  - login/logout/setup/healthz/static/media/admin-jsi18n (servidos antes
    do user resolver permissão).
  - Endpoint AJAX i18n.
"""
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse, NoReverseMatch


# Path prefixes (sem locale) que NÃO disparam o gating.
# `request.path` chega já com prefixo de língua aplicado em rotas dentro
# de i18n_patterns, por isso fazemos o teste contra `path_info` sem o prefixo.
_EXEMPT_PATH_SUFFIXES = (
    '/login/',
    '/logout/',
    '/i18n/',
    '/healthz/',
    '/setup-inicial-4x9z/',
    '/accounts/2fa/setup/',
    '/accounts/2fa/verify/',
    '/accounts/2fa/disable/',
)

# Prefixos de path absoluto que isentam (servem-se a qualquer um).
_EXEMPT_PATH_PREFIXES = (
    '/static/',
    '/media/',
)


def _is_exempt(path: str) -> bool:
    if any(path.startswith(prefix) for prefix in _EXEMPT_PATH_PREFIXES):
        return True
    return any(path.endswith(suffix) for suffix in _EXEMPT_PATH_SUFFIXES)


class OTPGateMiddleware:
    """
    Força staff/superuser sem TOTP confirmado nesta sessão a passar pelas
    páginas de setup/verify antes de acederem a qualquer outra rota.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'OTP_REQUIRED_FOR_STAFF', False):
            return self.get_response(request)

        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return self.get_response(request)

        if not (user.is_staff or user.is_superuser):
            return self.get_response(request)

        # OTPMiddleware põe `is_verified()` em request.user.
        if user.is_verified():
            return self.get_response(request)

        if _is_exempt(request.path):
            return self.get_response(request)

        # Decide setup ou verify conforme tem device confirmado ou não.
        from django_otp import devices_for_user
        has_device = any(devices_for_user(user, confirmed=True))
        try:
            target = reverse(
                'accounts:otp_verify' if has_device else 'accounts:otp_setup'
            )
        except NoReverseMatch:
            return self.get_response(request)

        return HttpResponseRedirect(f'{target}?next={request.path}')
