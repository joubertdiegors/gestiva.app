from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
        ('workforce', '0005_legalform_migrate_all'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # Remove a coluna antiga (já temos legal_form_id do RunSQL)
                migrations.RunSQL(
                    # SQLite 3.35+ suporta DROP COLUMN — se falhar, ignora (coluna obsoleta)
                    "ALTER TABLE clients_client DROP COLUMN legal_form;",
                    reverse_sql="SELECT 1;",
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='client',
                    name='legal_form',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='clients',
                        to='workforce.legalform',
                        verbose_name='Forme juridique',
                    ),
                ),
            ],
        ),
    ]
