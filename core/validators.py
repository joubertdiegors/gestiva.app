"""
Validadores partilhados.

`validate_be_vat` apoia-se no `python-stdnum` (formato + checksum modulo 97
para BE0XXXXXXXXX). Aceita também valores vazios para permitir que o campo
seja opcional ao nível do modelo (cabe a cada caller decidir se exige).
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_be_vat(value: str) -> None:
    """
    Valida um número de IVA belga. Vazio é aceite (campo opcional).

    Aceita variações comuns ('BE 0123.456.789', 'BE0123456789', '0123456789')
    — o `python-stdnum` normaliza antes de validar.
    """
    if not value:
        return
    raw = value.strip()
    if not raw:
        return
    try:
        from stdnum.be import vat as be_vat
    except ImportError as exc:
        raise ValidationError(
            _('VAT validation library (python-stdnum) is not installed.'),
        ) from exc
    try:
        be_vat.validate(raw)
    except Exception as exc:
        raise ValidationError(
            _('Invalid Belgian VAT number: %(value)s'),
            code='invalid_vat',
            params={'value': raw},
        ) from exc


def normalize_be_vat(value: str) -> str:
    """Normaliza para formato canónico BE0XXXXXXXXX (sem espaços/pontos).

    `python-stdnum.be.vat.compact()` devolve apenas os dígitos — preferimos
    re-prefixar `BE` por consistência com o que aparece em PDFs e emails.

    Devolve o input se a validação falhar — caller deve chamar
    `validate_be_vat` antes de persistir.
    """
    if not value:
        return value
    try:
        from stdnum.be import vat as be_vat
        digits = be_vat.compact(value)
        return f'BE{digits}'
    except Exception:
        return value
