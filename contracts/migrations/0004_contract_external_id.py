import uuid

from django.db import migrations, models


def populate_external_id(apps, schema_editor):
    Contract = apps.get_model('contracts', 'Contract')
    for obj in Contract.objects.filter(external_id__isnull=True):
        obj.external_id = uuid.uuid4()
        obj.save(update_fields=['external_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0003_xor_constraints'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='external_id',
            field=models.UUIDField(null=True, editable=False, unique=False, verbose_name='External ID'),
        ),
        migrations.RunPython(populate_external_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='contract',
            name='external_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='External ID'),
        ),
    ]
