"""sla resolvido em demandas

Fase 2G.6D3B — resolução do SLA pela primeira conclusão real da Demanda (ver
app/models/demanda.py e app/services/demanda_service.py). Adiciona SOMENTE
`sla_resolvido_em` em `demandas` — não toca em `sla_regras`, `demanda_comentarios`,
`workflow_modelos`, `workflow_modelo_etapas`, `demanda_workflow_etapas` nem `regra_expediente`.

Sem CHECK constraint: é um fato ocorrido (quando a Demanda foi dada como pronta pela
primeira vez), não um valor com formato restrito.

Revision ID: afdf2d44c7b2
Revises: 5bb704c7596d
Create Date: 2026-09-04 10:09:31.758679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afdf2d44c7b2'
down_revision: Union[str, None] = '5bb704c7596d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('demandas', sa.Column('sla_resolvido_em', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('demandas', 'sla_resolvido_em')
