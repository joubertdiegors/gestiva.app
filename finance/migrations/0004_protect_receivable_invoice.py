"""
Trocar Receivable.invoice de CASCADE para PROTECT.

Motivo: a Invoice é entidade fiscal. Apagar uma Invoice em produção (mesmo
acidentalmente, via admin ou shell) ia, em CASCADE, destruir também o
Receivable e os Payments associados — perdendo o registo contabilístico
de pagamentos já recebidos. Com PROTECT o utilizador é forçado a anular
o Receivable explicitamente antes, ou a marcar a Invoice como cancelada
em vez de a apagar.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_payable_subcontractor_and_more'),
        ('invoicing', '0002_add_invoice_type_and_line_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='receivable',
            name='invoice',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='receivable',
                to='invoicing.invoice',
                verbose_name='Invoice',
            ),
        ),
    ]
