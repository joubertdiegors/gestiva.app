import uuid

from django.db import migrations, models


def populate_external_id(apps, schema_editor):
    Payment = apps.get_model('finance', 'Payment')
    for obj in Payment.objects.filter(external_id__isnull=True):
        obj.external_id = uuid.uuid4()
        obj.save(update_fields=['external_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0004_protect_receivable_invoice'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='external_id',
            field=models.UUIDField(null=True, editable=False, unique=False, verbose_name='External ID'),
        ),
        migrations.RunPython(populate_external_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='payment',
            name='external_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='External ID'),
        ),
    ]
