from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0001_initial'),
        ('workforce', '0005_legalform_migrate_all'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE suppliers_supplier DROP COLUMN legal_form_old;",
                    reverse_sql="SELECT 1;",
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='supplier',
                    name='legal_form',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='suppliers',
                        to='workforce.legalform',
                        verbose_name='Forme juridique',
                    ),
                ),
            ],
        ),
    ]
