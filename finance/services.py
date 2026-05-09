"""
Camada de serviço financeira — Sprint 3 (incremental).

Hoje: thin wrappers em redor das `sync_status` do Payable/Receivable, para
que callers (views, jobs, testes) não precisem de saber detalhes de
transação/select_for_update.
"""
from django.db import transaction


def sync_payable_status(payable):
    """Recalcula status do Payable a partir dos pagamentos. Reentrante."""
    with transaction.atomic():
        payable.sync_status()
    return payable


def sync_receivable_status(receivable):
    """
    Recalcula status do Receivable, propagando ao Invoice ligado quando
    aplicável (via Receivable.sync_status).
    """
    with transaction.atomic():
        receivable.sync_status()
    return receivable
