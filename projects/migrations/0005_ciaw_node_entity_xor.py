"""
Adiciona CheckConstraint XOR a ProjectCiawParticipant.

A árvore CIAW de cada projeto tem 4 tipos de nó:
  - client / construart : sintéticos (não apontam para nenhuma entidade)
  - subcontractor       : preenche FK Subcontractor
  - worker              : preenche FK Collaborator

A constraint garante que cada nó tem preenchidos apenas os campos
compatíveis com o seu node_type.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_projectciawparticipant'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='projectciawparticipant',
            constraint=models.CheckConstraint(
                name='ciaw_node_entity_xor',
                check=(
                    models.Q(
                        node_type='client',
                        subcontractor__isnull=True,
                        worker__isnull=True,
                    )
                    | models.Q(
                        node_type='construart',
                        subcontractor__isnull=True,
                        worker__isnull=True,
                    )
                    | models.Q(
                        node_type='subcontractor',
                        subcontractor__isnull=False,
                        worker__isnull=True,
                    )
                    | models.Q(
                        node_type='worker',
                        subcontractor__isnull=True,
                        worker__isnull=False,
                    )
                ),
            ),
        ),
    ]
