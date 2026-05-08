import uuid

from django.db import migrations, models


def populate_external_id(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    for obj in Client.objects.filter(external_id__isnull=True):
        obj.external_id = uuid.uuid4()
        obj.save(update_fields=['external_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0003_alter_clientaddress_options_alter_client_category_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='external_id',
            field=models.UUIDField(null=True, editable=False, unique=False, verbose_name='External ID'),
        ),
        migrations.RunPython(populate_external_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='client',
            name='external_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='External ID'),
        ),
    ]
