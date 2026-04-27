# Custom permission: view timesheet cost values (lista com valores)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='timesheet',
            options={
                'verbose_name': 'Timesheet',
                'verbose_name_plural': 'Timesheets',
                'ordering': ['-date', 'worker__name'],
                'indexes': [
                    models.Index(fields=['date', 'project'], name='timesheets__date_56299d_idx'),
                    models.Index(fields=['worker', 'date'], name='timesheets__worker__bf2145_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=['worker', 'project', 'date'],
                        name='unique_timesheet_per_worker_project_day',
                    )
                ],
                'permissions': [
                    ('view_timesheet_values', 'View timesheet cost values'),
                ],
            },
        ),
    ]
