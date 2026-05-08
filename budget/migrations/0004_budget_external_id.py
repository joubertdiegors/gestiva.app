import uuid

from django.db import migrations, models


def populate_external_id(apps, schema_editor):
    Budget = apps.get_model('budget', 'Budget')
    for obj in Budget.objects.filter(external_id__isnull=True):
        obj.external_id = uuid.uuid4()
        obj.save(update_fields=['external_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0003_alter_budget_options_alter_budgetchapter_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='budget',
            name='external_id',
            field=models.UUIDField(null=True, editable=False, unique=False, verbose_name='External ID'),
        ),
        migrations.RunPython(populate_external_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='budget',
            name='external_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='External ID'),
        ),
    ]
