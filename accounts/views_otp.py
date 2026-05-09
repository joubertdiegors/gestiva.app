"""
Views de gestão de 2FA TOTP (Sprint 5).

Fluxo do utilizador:

1. Login normal (username + password) ✅
2. Se já tem TOTP confirmado e a sessão ainda não verificou → /accounts/2fa/verify/
3. Se não tem TOTP e o sistema exige (staff/superuser em produção) → /accounts/2fa/setup/

Não usamos `django-two-factor-auth` para manter o login custom existente
(`core.views.login_view`) — só `django-otp` puro.
"""
import base64
from io import BytesIO
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from django_otp import devices_for_user, login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice


def _safe_next(request) -> str:
    """Devolve `next` apenas se for caminho relativo na própria app."""
    nxt = request.GET.get('next') or request.POST.get('next') or ''
    if not nxt:
        return ''
    parsed = urlparse(nxt)
    if parsed.scheme or parsed.netloc:
        return ''
    return nxt


def _qrcode_data_uri(uri: str) -> str:
    """Renderiza o URI otpauth:// como PNG inline (data URI)."""
    import qrcode
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


@login_required
@require_http_methods(['GET', 'POST'])
def otp_setup(request):
    """
    Inscreve o utilizador num dispositivo TOTP.

    GET  → mostra QR code do device pendente (cria-se um se não existir).
    POST → confirma o token introduzido. Sucesso = device.confirmed=True
           e sessão verificada.
    """
    user = request.user

    # Reutiliza um device unconfirmed se existir (recarregar página não cria
    # device novo). Caso contrário cria um.
    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if device is None:
        device = TOTPDevice.objects.create(
            user=user,
            name='default',
            confirmed=False,
        )

    issuer = getattr(settings, 'OTP_TOTP_ISSUER', 'Construart')
    config_url = device.config_url
    # Reescreve issuer para refletir COMPANY_NAME, já que `config_url` usa
    # o nome do device por defeito.
    if 'issuer=' not in config_url:
        sep = '&' if '?' in config_url else '?'
        config_url = f"{config_url}{sep}issuer={issuer}"

    error = None
    if request.method == 'POST':
        token = (request.POST.get('token') or '').strip()
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            otp_login(request, device)
            messages.success(request, _("2FA ativado com sucesso."))
            nxt = _safe_next(request) or reverse('dashboard')
            return HttpResponseRedirect(nxt)
        error = _("Código inválido. Verifica o relógio do telefone e tenta de novo.")

    return render(request, 'accounts/otp_setup.html', {
        'qr_data_uri': _qrcode_data_uri(config_url),
        'secret_b32': device.bin_key.hex() if hasattr(device, 'bin_key') else '',
        'config_url': config_url,
        'error': error,
        'next': _safe_next(request),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def otp_verify(request):
    """Pede o código TOTP (sessão ainda não verificada)."""
    user = request.user

    confirmed_devices = list(devices_for_user(user, confirmed=True))
    if not confirmed_devices:
        return redirect('accounts:otp_setup')

    error = None
    if request.method == 'POST':
        token = (request.POST.get('token') or '').strip()
        for device in confirmed_devices:
            if device.verify_token(token):
                otp_login(request, device)
                nxt = _safe_next(request) or reverse('dashboard')
                return HttpResponseRedirect(nxt)
        error = _("Código inválido.")

    return render(request, 'accounts/otp_verify.html', {
        'error': error,
        'next': _safe_next(request),
    })


@login_required
@require_http_methods(['POST'])
def otp_disable(request):
    """
    Desativa todos os devices TOTP do próprio utilizador.

    Só é permitido se a sessão estiver verificada — evita alguém com cookie
    roubado mas sem TOTP desativar 2FA da vítima.
    """
    if not request.user.is_verified():
        messages.error(request, _("Confirma o teu código antes de desativar 2FA."))
        return redirect('accounts:otp_verify')

    TOTPDevice.objects.filter(user=request.user).delete()
    messages.success(request, _("2FA desativado."))
    return redirect('accounts:list')
