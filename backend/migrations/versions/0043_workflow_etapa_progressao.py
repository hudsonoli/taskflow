"""workflow_etapa_progressao

Progressão operacional do snapshot de Workflow da Demanda (Fase 8A). Migration ADITIVA e reversível; `status` e `ordem` das
etapas existentes NÃO são alterados e a "etapa atual" continua DERIVADA (menor `ordem` com `status != 'concluida'`):

  demanda_workflow_etapas.iniciada_em              quando a etapa passou a ser a atual (NULL = início histórico desconhecido)
  demanda_workflow_etapas.concluida_em             quando foi concluída/aprovada
  demanda_workflow_etapas.concluida_por_usuario_id quem concluiu/aprovou (FK usuarios, ON DELETE SET NULL)
  ck_demanda_workflow_etapas_concluida_em          status = 'concluida' => concluida_em preenchido
  uq_demanda_workflow_etapas_demanda_ordem         (demanda_id, ordem) único — torna a derivação da etapa atual inequívoca
                                                   (substitui o índice não-único ix_demanda_workflow_etapas_demanda_ordem)

Backfill: NADA é inventado. Etapas existentes ficam com os três campos NULL; só uma etapa que já estivesse `concluida` (não
deveria existir — nenhuma ação a concluía) recebe `concluida_em = updated_at`, sem ator. Se existir (demanda_id, ordem)
duplicado, a migration FALHA com mensagem clara e NÃO tenta corrigir/reordenar dados.

Revision ID: b7d3f19c2a58
Revises: e4a7c1d93b60
Create Date: 2026-10-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d3f19c2a58'
down_revision: Union[str, None] = 'e4a7c1d93b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABELA = 'demanda_workflow_etapas'


def upgrade() -> None:
    bind = op.get_bind()

    # 0) pré-checagem: ordem duplicada dentro da mesma demanda => falha explícita, sem corrigir nada
    duplicadas = bind.execute(
        sa.text(
            'SELECT demanda_id, ordem, count(*) FROM demanda_workflow_etapas '
            'GROUP BY demanda_id, ordem HAVING count(*) > 1 ORDER BY demanda_id, ordem LIMIT 5'
        )
    ).fetchall()
    if duplicadas:
        amostra = ', '.join(f'(demanda_id={d}, ordem={o}, linhas={n})' for d, o, n in duplicadas)
        raise RuntimeError(
            'demanda_workflow_etapas tem ordem duplicada dentro da mesma demanda; a migration 0043 NAO corrige dados. '
            f'Resolva manualmente e rode de novo. Exemplos: {amostra}'
        )

    # 1) colunas novas (todas nullable — ADD COLUMN sem reescrita de tabela)
    op.add_column(_TABELA, sa.Column('iniciada_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column(_TABELA, sa.Column('concluida_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column(_TABELA, sa.Column('concluida_por_usuario_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_demanda_workflow_etapas_concluida_por_usuario_id', _TABELA, 'usuarios',
        ['concluida_por_usuario_id'], ['id'], ondelete='SET NULL',
    )

    # 2) backfill mínimo: etapa histórica já concluída (excepcional) — data = updated_at, ator desconhecido (NULL)
    op.execute("UPDATE demanda_workflow_etapas SET concluida_em = updated_at WHERE status = 'concluida'")

    # 3) constraint de conclusão só depois do backfill
    op.create_check_constraint(
        'ck_demanda_workflow_etapas_concluida_em', _TABELA, "status <> 'concluida' OR concluida_em IS NOT NULL"
    )

    # 4) ordem única por demanda (o índice único substitui o não-único antigo)
    op.drop_index('ix_demanda_workflow_etapas_demanda_ordem', table_name=_TABELA)
    op.create_unique_constraint('uq_demanda_workflow_etapas_demanda_ordem', _TABELA, ['demanda_id', 'ordem'])


def downgrade() -> None:
    op.drop_constraint('uq_demanda_workflow_etapas_demanda_ordem', _TABELA, type_='unique')
    op.create_index('ix_demanda_workflow_etapas_demanda_ordem', _TABELA, ['demanda_id', 'ordem'])
    op.drop_constraint('ck_demanda_workflow_etapas_concluida_em', _TABELA, type_='check')
    op.drop_constraint('fk_demanda_workflow_etapas_concluida_por_usuario_id', _TABELA, type_='foreignkey')
    op.drop_column(_TABELA, 'concluida_por_usuario_id')
    op.drop_column(_TABELA, 'concluida_em')
    op.drop_column(_TABELA, 'iniciada_em')
