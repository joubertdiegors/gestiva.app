from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_split_address_fields'),
        ('subcontractors', '__first__'),
        ('workforce', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectCiawParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_type', models.CharField(choices=[('client', 'Client (project owner)'), ('construart', 'Construart'), ('subcontractor', 'Subcontractor'), ('worker', 'Worker')], max_length=20, verbose_name='Type')),
                ('order', models.PositiveSmallIntegerField(default=0, verbose_name='Order')),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='projects.projectciawparticipant', verbose_name='Parent node')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ciaw_participants', to='projects.project', verbose_name='Project')),
                ('subcontractor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ciaw_nodes', to='subcontractors.subcontractor', verbose_name='Subcontractor')),
                ('worker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ciaw_nodes', to='workforce.collaborator', verbose_name='Worker')),
            ],
            options={
                'verbose_name': 'CIAW Participant',
                'verbose_name_plural': 'CIAW Participants',
                'ordering': ['order', 'added_at'],
            },
        ),
    ]
