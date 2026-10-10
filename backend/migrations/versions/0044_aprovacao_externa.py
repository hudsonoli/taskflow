"""aprovacao_externa

Portal externo de aprovação (Fase 9B). Migration ADITIVA, sem backfill: duas tabelas novas, nenhuma coluna alterada em tabelas existentes.

  aprovacoes_externas          link-capability por etapa de aprovação (token só como SHA-256; decisão e revogação mutuamente exclusivas;
                               no máximo UMA não decidida/não revogada por etapa — índice único parcial)
  aprovacao_externa_arquivos   artefatos da solicitação como snapshot (nome, tamanho, MIME, SHA-256); PK (aprovacao, ordem);
                               arquivo_id FK ON DELETE SET NULL (a evidência sobrevive à exclusão permitida do arquivo)

Sem IP, user-agent ou geolocalização. Retenção operacional inicial: 5 anos (sem job de purge). Downgrade remove as duas tabelas e, depois de uso real, a
evidência das decisões: faça backup antes.

Revision ID: c8e2a47d1f93
Revises: b7d3f19c2a58
Create Date: 2026-10-10 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e2a47d1f93'
down_revision: Union[str, None] = 'b7d3f19c2a58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'aprovacoes_externas',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('demanda_id', sa.String(length=36), nullable=False),
        sa.Column('workflow_etapa_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('instrucao', sa.Text(), nullable=True),
        sa.Column('criada_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('criada_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revogada_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revogada_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('revogada_motivo', sa.String(length=40), nullable=True),
        sa.Column('decisao', sa.String(length=24), nullable=True),
        sa.Column('decidida_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('nome_aprovador', sa.String(length=120), nullable=True),
        sa.Column('email_aprovador', sa.String(length=255), nullable=True),
        sa.Column('motivo', sa.Text(), nullable=True),
        sa.Column('destinatario_nome', sa.String(length=120), nullable=True),
        sa.Column('destinatario_email', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.ForeignKeyConstraint(['demanda_id'], ['demandas.id']),
        sa.ForeignKeyConstraint(['workflow_etapa_id'], ['demanda_workflow_etapas.id']),
        sa.ForeignKeyConstraint(['criada_por_usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revogada_por_usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('token_hash', name='uq_aprovacoes_externas_token_hash'),
        sa.CheckConstraint("decisao IS NULL OR decisao IN ('aprovada', 'ajustes_solicitados')", name='ck_aprovacoes_externas_decisao'),
        sa.CheckConstraint('(decisao IS NULL) = (decidida_em IS NULL)', name='ck_aprovacoes_externas_decidida_em'),
        sa.CheckConstraint('decisao IS NULL OR nome_aprovador IS NOT NULL', name='ck_aprovacoes_externas_nome_aprovador'),
        sa.CheckConstraint("decisao IS DISTINCT FROM 'ajustes_solicitados' OR motivo IS NOT NULL", name='ck_aprovacoes_externas_motivo_ajustes'),
        sa.CheckConstraint('decisao IS NULL OR revogada_em IS NULL', name='ck_aprovacoes_externas_decisao_ou_revogada'),
        sa.CheckConstraint('(revogada_em IS NULL) = (revogada_motivo IS NULL)', name='ck_aprovacoes_externas_revogada_motivo'),
        sa.CheckConstraint(
            "revogada_motivo IS NULL OR revogada_motivo IN ('manual', 'substituida', 'etapa_decidida_internamente')",
            name='ck_aprovacoes_externas_revogada_motivo_valores',
        ),
        sa.CheckConstraint('expira_em > criada_em', name='ck_aprovacoes_externas_expira_em'),
    )
    op.create_index(
        'uq_aprovacoes_externas_aberta_por_etapa', 'aprovacoes_externas', ['workflow_etapa_id'],
        unique=True, postgresql_where=sa.text('decisao IS NULL AND revogada_em IS NULL'),
    )
    op.create_index('ix_aprovacoes_externas_empresa_id', 'aprovacoes_externas', ['empresa_id'])
    op.create_index('ix_aprovacoes_externas_demanda_id', 'aprovacoes_externas', ['demanda_id'])
    op.create_index('ix_aprovacoes_externas_workflow_etapa_id', 'aprovacoes_externas', ['workflow_etapa_id'])

    op.create_table(
        'aprovacao_externa_arquivos',
        sa.Column('aprovacao_externa_id', sa.String(length=36), nullable=False),
        sa.Column('ordem', sa.SmallInteger(), nullable=False),
        sa.Column('arquivo_id', sa.String(length=36), nullable=True),
        sa.Column('nome_original', sa.String(length=255), nullable=False),
        sa.Column('tamanho_bytes', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(length=128), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('aprovacao_externa_id', 'ordem'),
        sa.ForeignKeyConstraint(['aprovacao_externa_id'], ['aprovacoes_externas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['arquivo_id'], ['demanda_arquivos.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('aprovacao_externa_id', 'arquivo_id', name='uq_aprovacao_externa_arquivos_arquivo'),
        sa.CheckConstraint('ordem >= 1', name='ck_aprovacao_externa_arquivos_ordem'),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name='ck_aprovacao_externa_arquivos_sha256'),
    )
    op.create_index('ix_aprovacao_externa_arquivos_arquivo_id', 'aprovacao_externa_arquivos', ['arquivo_id'])


def downgrade() -> None:
    op.drop_index('ix_aprovacao_externa_arquivos_arquivo_id', table_name='aprovacao_externa_arquivos')
    op.drop_table('aprovacao_externa_arquivos')
    op.drop_index('ix_aprovacoes_externas_workflow_etapa_id', table_name='aprovacoes_externas')
    op.drop_index('ix_aprovacoes_externas_demanda_id', table_name='aprovacoes_externas')
    op.drop_index('ix_aprovacoes_externas_empresa_id', table_name='aprovacoes_externas')
    op.drop_index('uq_aprovacoes_externas_aberta_por_etapa', table_name='aprovacoes_externas')
    op.drop_table('aprovacoes_externas')
