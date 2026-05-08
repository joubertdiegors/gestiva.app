import uuid

from django.db import migrations, models


def populate_external_id(apps, schema_editor):
    Supplier = apps.get_model('suppliers', 'Supplier')
    for obj in Supplier.objects.filter(external_id__isnull=True):
        obj.external_id = uuid.uuid4()
        obj.save(update_fields=['external_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0003_alter_supplier_options_alter_supplieraddress_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='external_id',
            field=models.UUIDField(null=True, editable=False, unique=False, verbose_name='External ID'),
        ),
        migrations.RunPython(populate_external_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='supplier',
            name='external_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='External ID'),
        ),
    ]
