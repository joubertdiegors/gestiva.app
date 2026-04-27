"""
Permission registry for the Construart permission matrix UI.

Each entry in MODULE_PERMISSIONS defines one row in the matrix:
  app     — Django app_label
  model   — main model name (lowercase) used for permission codenames
  label   — display name (translatable)
  icon    — emoji for the UI

Standard actions (view/add/change/delete) are auto-created by Django migrations.
The custom 'export_*' permissions are created by migration 0004.

To add a new module in the future, simply append an entry here — the matrix
and all permission checks will pick it up automatically.
"""

from django.utils.translation import gettext_lazy as _


MODULE_PERMISSIONS = [
    {
        'app':   'projects',
        'model': 'project',
        'label': _('Projetos'),
        'icon':  '🏗️',
    },
    {
        'app':   'clients',
        'model': 'client',
        'label': _('Clientes'),
        'icon':  '👤',
    },
    {
        'app':   'subcontractors',
        'model': 'subcontractor',
        'label': _('Subcontratados'),
        'icon':  '🏢',
    },
    {
        'app':   'workforce',
        'model': 'collaborator',
        'label': _('Colaboradores'),
        'icon':  '👷',
    },
    {
        'app':   'planning',
        'model': 'planning',
        'label': _('Planning'),
        'icon':  '📅',
    },
    {
        'app':   'timesheets',
        'model': 'timesheet',
        'label': _('Timesheets'),
        'icon':  '⏱️',
    },
    {
        'app':   'accounts',
        'model': 'user',
        'label': _('Utilizadores'),
        'icon':  '👥',
    },
]

PERMISSION_ACTIONS = [
    ('view',   _('Ver')),
    ('add',    _('Adicionar')),
    ('change', _('Editar')),
    ('delete', _('Eliminar')),
    ('export', _('Exportar')),
]


def build_matrix(group=None):
    """
    Return the full permission matrix as a list of module dicts.
    Each module dict has an 'actions' list with checked/perm_id info.
    If group is None (create), all boxes are unchecked.
    """
    from django.contrib.auth.models import Permission

    # IDs of permissions already assigned to this group
    assigned_ids = set()
    if group and group.pk:
        assigned_ids = set(group.permissions.values_list('id', flat=True))

    # Load all relevant permissions in one query
    app_labels = [m['app'] for m in MODULE_PERMISSIONS]
    all_perms  = Permission.objects.filter(
        content_type__app_label__in=app_labels
    ).select_related('content_type')
    perm_map = {
        (p.content_type.app_label, p.codename): p
        for p in all_perms
    }

    matrix = []
    for module in MODULE_PERMISSIONS:
        actions = []
        for action, action_label in PERMISSION_ACTIONS:
            codename = f'{action}_{module["model"]}'
            perm     = perm_map.get((module['app'], codename))
            actions.append({
                'action':       action,
                'action_label': action_label,
                'perm_id':      perm.id if perm else None,
                'checked':      (perm.id in assigned_ids) if perm else False,
            })
        matrix.append({**module, 'actions': actions})

    return matrix


# ---------------------------------------------------------------------------
# Data migration helper — called from migration 0004
# ---------------------------------------------------------------------------

def create_export_permissions(apps, schema_editor):
    """Create custom export_* permissions for each main module model."""
    Permission   = apps.get_model('auth', 'Permission')
    ContentType  = apps.get_model('contenttypes', 'ContentType')

    targets = [
        ('projects',       'project',       'Exportar projetos'),
        ('clients',        'client',        'Exportar clientes'),
        ('subcontractors', 'subcontractor', 'Exportar subcontratados'),
        ('workforce',      'collaborator',  'Exportar colaboradores'),
        ('planning',       'planning',      'Exportar planning'),
        ('timesheets',     'timesheet',     'Exportar timesheets'),
        ('accounts',       'user',          'Exportar utilizadores'),
    ]

    for app_label, model_name, name in targets:
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
            Permission.objects.get_or_create(
                codename=f'export_{model_name}',
                content_type=ct,
                defaults={'name': name},
            )
        except ContentType.DoesNotExist:
            pass  # App not yet migrated — safe to skip
