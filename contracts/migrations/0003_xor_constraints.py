"""
Adiciona CheckConstraint XOR a Contract e Statement.

- Contract: o tipo determina qual contraparte (client/subcontractor/supplier)
  está preenchida; 'other' não tem nenhuma das três.
- Statement: 'client' usa contract; 'subcontractor' usa addendum.

Estas restrições impedem que estados ilegais cheguem ao DB (ex.: contrato
de cliente com supplier preenchido por engano).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0002_suppliercontract_suppliercontractline'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='contract',
            constraint=models.CheckConstraint(
                name='contract_counterpart_xor',
                check=(
                    models.Q(
                        contract_type='client',
                        client__isnull=False,
                        subcontractor__isnull=True,
                        supplier__isnull=True,
                    )
                    | models.Q(
                        contract_type='subcontractor',
                        client__isnull=True,
                        subcontractor__isnull=False,
                        supplier__isnull=True,
                    )
                    | models.Q(
                        contract_type='supplier',
                        client__isnull=True,
                        subcontractor__isnull=True,
                        supplier__isnull=False,
                    )
                    | models.Q(
                        contract_type='other',
                        client__isnull=True,
                        subcontractor__isnull=True,
                        supplier__isnull=True,
                    )
                ),
            ),
        ),
        migrations.AddConstraint(
            model_name='statement',
            constraint=models.CheckConstraint(
                name='statement_origin_xor',
                check=(
                    models.Q(
                        statement_type='client',
                        contract__isnull=False,
                        addendum__isnull=True,
                    )
                    | models.Q(
                        statement_type='subcontractor',
                        contract__isnull=True,
                        addendum__isnull=False,
                    )
                ),
            ),
        ),
    ]
