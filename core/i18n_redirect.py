"""
Redirects and reverse() that respect the language cookie on URLs outside
i18n_patterns (e.g. /login/). Kept for explicit reverse(); with
prefix_default_language=True, LocaleMiddleware no longer forces LANGUAGE_CODE
on unprefixed paths, but this helper still applies cookie-based override safely.
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import translation
from django.utils.translation import check_for_language, get_supported_language_variant


def language_from_cookie(request) -> str | None:
    raw = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
    if not raw:
        return None
    try:
        lang = get_supported_language_variant(raw)
    except LookupError:
        return None
    if not check_for_language(lang):
        return None
    return lang


def reverse_with_cookie_language(request, viewname, *args, **kwargs) -> str:
    lang = language_from_cookie(request)
    if lang:
        with translation.override(lang):
            return reverse(viewname, args=args, kwargs=kwargs)
    return reverse(viewname, args=args, **kwargs)


def redirect_with_cookie_language(request, viewname, *args, **kwargs):
    return HttpResponseRedirect(reverse_with_cookie_language(request, viewname, *args, **kwargs))
