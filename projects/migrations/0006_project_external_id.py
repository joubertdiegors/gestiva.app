import uuid

from django.db import migrations, models


def populate_external_id(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    for obj in Project.objects.filter(external_id__isnull=True):
        obj.external_id = uuid.uuid4()
        obj.save(update_fields=['external_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0005_ciaw_node_entity_xor'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='external_id',
            field=models.UUIDField(null=True, editable=False, unique=False, verbose_name='External ID'),
        ),
        migrations.RunPython(populate_external_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='project',
            name='external_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='External ID'),
        ),
    ]
