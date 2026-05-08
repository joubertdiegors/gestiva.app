import uuid

from django.db import migrations, models


def populate_external_id(apps, schema_editor):
    Invoice = apps.get_model('invoicing', 'Invoice')
    for obj in Invoice.objects.filter(external_id__isnull=True):
        obj.external_id = uuid.uuid4()
        obj.save(update_fields=['external_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing', '0002_add_invoice_type_and_line_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='external_id',
            field=models.UUIDField(null=True, editable=False, unique=False, verbose_name='External ID'),
        ),
        migrations.RunPython(populate_external_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='invoice',
            name='external_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='External ID'),
        ),
    ]
