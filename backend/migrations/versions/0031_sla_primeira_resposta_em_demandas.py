"""sla primeira resposta em demandas

Fase 2G.6D2B — marcação da primeira resposta do SLA (ver app/models/demanda.py e
app/services/demanda_comentario_service.py). Adiciona SOMENTE `sla_primeira_resposta_em` em
`demandas` — não toca em `sla_regras`, `demanda_comentarios`, `workflow_modelos`,
`workflow_modelo_etapas`, `demanda_workflow_etapas` nem `regra_expediente`.

Sem CHECK constraint: ao contrário dos campos de snapshot (2G.6D1), este é um FATO ocorrido
(quando a equipe respondeu pela primeira vez), não um valor com formato restrito — qualquer
timestamp é válido.

Revision ID: 5bb704c7596d
Revises: 6cb667a43389
Create Date: 2026-09-03 21:12:50.299900

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bb704c7596d'
down_revision: Union[str, None] = '6cb667a43389'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('demandas', sa.Column('sla_primeira_resposta_em', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('demandas', 'sla_primeira_resposta_em')
