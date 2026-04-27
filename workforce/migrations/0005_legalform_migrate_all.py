"""
Migração unificada:
1. Popula workforce_legalform com as opções que existiam como choices
2. Migra clients, suppliers e subcontractors de CharField → ForeignKey
   usando RunSQL puro para contornar limitações do SQLite e do ORM
   (o estado do model já não tem a coluna legal_form_old).
"""
from django.db import migrations, models
import django.db.models.deletion


INITIAL_FORMS = [
    ('SRL',         'SRL'),
    ('SA',          'SA'),
    ('SCS',         'SCS'),
    ('SNC',         'SNC'),
    ('ASBL',        'ASBL'),
    ('Indépendant', 'Indépendant'),
    ('Autre',       'Autre'),
]

# SQL para popular a tabela de formas jurídicas
POPULATE_SQL = "\n".join(
    f"INSERT OR IGNORE INTO workforce_legalform (abbreviation, name, notes) VALUES ('{abbr}', '{name}', '');"
    for abbr, name in INITIAL_FORMS
)

# SQL para migrar dados: para cada tabela, lê o código antigo e encontra o ID
MIGRATE_CLIENTS_SQL = """
UPDATE clients_client
SET legal_form_id = (
    SELECT id FROM workforce_legalform
    WHERE abbreviation = CASE legal_form_old
        WHEN 'srl'         THEN 'SRL'
        WHEN 'sa'          THEN 'SA'
        WHEN 'scs'         THEN 'SCS'
        WHEN 'snc'         THEN 'SNC'
        WHEN 'asbl'        THEN 'ASBL'
        WHEN 'independant' THEN 'Indépendant'
        WHEN 'other'       THEN 'Autre'
        ELSE NULL
    END
)
WHERE legal_form_old IS NOT NULL AND legal_form_old != '';
"""

MIGRATE_SUPPLIERS_SQL = """
UPDATE suppliers_supplier
SET legal_form_id = (
    SELECT id FROM workforce_legalform
    WHERE abbreviation = CASE legal_form_old
        WHEN 'srl'         THEN 'SRL'
        WHEN 'sa'          THEN 'SA'
        WHEN 'scs'         THEN 'SCS'
        WHEN 'snc'         THEN 'SNC'
        WHEN 'asbl'        THEN 'ASBL'
        WHEN 'independant' THEN 'Indépendant'
        WHEN 'other'       THEN 'Autre'
        ELSE NULL
    END
)
WHERE legal_form_old IS NOT NULL AND legal_form_old != '';
"""

MIGRATE_SUBCONTRACTORS_SQL = """
UPDATE subcontractors_subcontractor
SET legal_form_id = (
    SELECT id FROM workforce_legalform
    WHERE abbreviation = CASE legal_form_old
        WHEN 'srl'         THEN 'SRL'
        WHEN 'sa'          THEN 'SA'
        WHEN 'scs'         THEN 'SCS'
        WHEN 'snc'         THEN 'SNC'
        WHEN 'asbl'        THEN 'ASBL'
        WHEN 'independant' THEN 'Indépendant'
        WHEN 'other'       THEN 'Autre'
        ELSE NULL
    END
)
WHERE legal_form_old IS NOT NULL AND legal_form_old != '';
"""


class Migration(migrations.Migration):

    dependencies = [
        ('workforce', '0004_add_legalform_model'),
        # Tabelas alvo do RunSQL precisam existir antes (ordem de apps não garante isso)
        ('clients', '0001_initial'),
        ('suppliers', '0001_initial'),
        ('subcontractors', '0001_initial'),
    ]

    operations = [
        # 1. Popula a tabela de formas jurídicas
        migrations.RunSQL(POPULATE_SQL, reverse_sql=migrations.RunSQL.noop),

        # ── CLIENTS ──────────────────────────────────────────────────────────
        # Renomeia coluna antiga, adiciona FK, migra dados
        migrations.RunSQL(
            "ALTER TABLE clients_client RENAME COLUMN legal_form TO legal_form_old;",
            reverse_sql="ALTER TABLE clients_client RENAME COLUMN legal_form_old TO legal_form;",
        ),
        migrations.RunSQL(
            "ALTER TABLE clients_client ADD COLUMN legal_form_id INTEGER REFERENCES workforce_legalform(id) ON DELETE SET NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(MIGRATE_CLIENTS_SQL, reverse_sql=migrations.RunSQL.noop),

        # ── SUPPLIERS ─────────────────────────────────────────────────────────
        migrations.RunSQL(
            "ALTER TABLE suppliers_supplier RENAME COLUMN legal_form TO legal_form_old;",
            reverse_sql="ALTER TABLE suppliers_supplier RENAME COLUMN legal_form_old TO legal_form;",
        ),
        migrations.RunSQL(
            "ALTER TABLE suppliers_supplier ADD COLUMN legal_form_id INTEGER REFERENCES workforce_legalform(id) ON DELETE SET NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(MIGRATE_SUPPLIERS_SQL, reverse_sql=migrations.RunSQL.noop),

        # ── SUBCONTRACTORS ────────────────────────────────────────────────────
        migrations.RunSQL(
            "ALTER TABLE subcontractors_subcontractor RENAME COLUMN legal_form TO legal_form_old;",
            reverse_sql="ALTER TABLE subcontractors_subcontractor RENAME COLUMN legal_form_old TO legal_form;",
        ),
        migrations.RunSQL(
            "ALTER TABLE subcontractors_subcontractor ADD COLUMN legal_form_id INTEGER REFERENCES workforce_legalform(id) ON DELETE SET NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(MIGRATE_SUBCONTRACTORS_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
