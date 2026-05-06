from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ContractsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contracts'
    verbose_name = _('Contracts')
