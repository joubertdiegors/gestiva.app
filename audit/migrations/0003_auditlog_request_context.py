from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0002_auditlog_audit_audit_model_n_20c0d3_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='user_agent',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='request_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=36),
        ),
    ]
