"""sla snapshot em demandas

Fase 2G.6D1 — resolução de SLA na criação da Demanda (ver app/models/demanda.py e
app/services/demanda_service.py). Adiciona SOMENTE as colunas de snapshot/deadline em
`demandas` — não toca em `sla_regras`, `workflow_modelos`, `workflow_modelo_etapas`,
`demanda_workflow_etapas` nem `regra_expediente`.

`sla_regra_id` é FK `ON DELETE SET NULL` (proveniência histórica — se a regra for removida
fisicamente algum dia, o snapshot textual/numérico sobrevive; ver docstring do model). Os
demais campos são cópia imutável da regra resolvida no instante da criação, nunca lidos via
JOIN vivo.

Revision ID: 6cb667a43389
Revises: a17fbbef4ad8
Create Date: 2026-09-02 18:22:57.489462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cb667a43389'
down_revision: Union[str, None] = 'a17fbbef4ad8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('demandas', sa.Column('sla_regra_id', sa.String(length=36), nullable=True))
    op.add_column('demandas', sa.Column('sla_regra_nome_snapshot', sa.String(length=255), nullable=True))
    op.add_column(
        'demandas', sa.Column('sla_prazo_primeira_resposta_quantidade_snapshot', sa.Integer(), nullable=True)
    )
    op.add_column(
        'demandas', sa.Column('sla_prazo_primeira_resposta_unidade_snapshot', sa.String(length=16), nullable=True)
    )
    op.add_column('demandas', sa.Column('sla_prazo_resolucao_quantidade_snapshot', sa.Integer(), nullable=True))
    op.add_column(
        'demandas', sa.Column('sla_prazo_resolucao_unidade_snapshot', sa.String(length=16), nullable=True)
    )
    op.add_column('demandas', sa.Column('sla_considerar_expediente_snapshot', sa.Boolean(), nullable=True))
    op.add_column('demandas', sa.Column('sla_resolvido_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('demandas', sa.Column('sla_primeira_resposta_limite_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column('demandas', sa.Column('sla_resolucao_limite_em', sa.DateTime(timezone=True), nullable=True))

    op.create_check_constraint(
        'ck_demandas_sla_prazo_primeira_resposta_quantidade_snapshot',
        'demandas',
        'sla_prazo_primeira_resposta_quantidade_snapshot IS NULL OR '
        'sla_prazo_primeira_resposta_quantidade_snapshot > 0',
    )
    op.create_check_constraint(
        'ck_demandas_sla_prazo_primeira_resposta_unidade_snapshot',
        'demandas',
        "sla_prazo_primeira_resposta_unidade_snapshot IS NULL OR "
        "sla_prazo_primeira_resposta_unidade_snapshot IN ('minutos', 'horas', 'dias_corridos', 'dias_uteis')",
    )
    op.create_check_constraint(
        'ck_demandas_sla_prazo_resolucao_quantidade_snapshot',
        'demandas',
        'sla_prazo_resolucao_quantidade_snapshot IS NULL OR sla_prazo_resolucao_quantidade_snapshot > 0',
    )
    op.create_check_constraint(
        'ck_demandas_sla_prazo_resolucao_unidade_snapshot',
        'demandas',
        "sla_prazo_resolucao_unidade_snapshot IS NULL OR "
        "sla_prazo_resolucao_unidade_snapshot IN ('minutos', 'horas', 'dias_corridos', 'dias_uteis')",
    )

    op.create_foreign_key(
        'fk_demandas_sla_regra_id_sla_regras',
        'demandas',
        'sla_regras',
        ['sla_regra_id'],
        ['id'],
        ondelete='SET NULL',
    )
    # Mesmo padrão de índice das outras FKs desta tabela (cliente_id, projeto_id,
    # criado_por_usuario_id, workflow_modelo_id) — não indexamos ainda
    # sla_primeira_resposta_limite_em/sla_resolucao_limite_em: nenhum filtro/ordenação real por
    # elas existe nesta fase (ver relatório 2G.6D1, item de índices).
    op.create_index('ix_demandas_sla_regra_id', 'demandas', ['sla_regra_id'])


def downgrade() -> None:
    op.drop_index('ix_demandas_sla_regra_id', table_name='demandas')
    op.drop_constraint('fk_demandas_sla_regra_id_sla_regras', 'demandas', type_='foreignkey')
    op.drop_constraint('ck_demandas_sla_prazo_resolucao_unidade_snapshot', 'demandas', type_='check')
    op.drop_constraint('ck_demandas_sla_prazo_resolucao_quantidade_snapshot', 'demandas', type_='check')
    op.drop_constraint('ck_demandas_sla_prazo_primeira_resposta_unidade_snapshot', 'demandas', type_='check')
    op.drop_constraint('ck_demandas_sla_prazo_primeira_resposta_quantidade_snapshot', 'demandas', type_='check')
    op.drop_column('demandas', 'sla_resolucao_limite_em')
    op.drop_column('demandas', 'sla_primeira_resposta_limite_em')
    op.drop_column('demandas', 'sla_resolvido_at')
    op.drop_column('demandas', 'sla_considerar_expediente_snapshot')
    op.drop_column('demandas', 'sla_prazo_resolucao_unidade_snapshot')
    op.drop_column('demandas', 'sla_prazo_resolucao_quantidade_snapshot')
    op.drop_column('demandas', 'sla_prazo_primeira_resposta_unidade_snapshot')
    op.drop_column('demandas', 'sla_prazo_primeira_resposta_quantidade_snapshot')
    op.drop_column('demandas', 'sla_regra_nome_snapshot')
    op.drop_column('demandas', 'sla_regra_id')
