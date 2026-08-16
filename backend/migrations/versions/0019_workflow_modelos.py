"""workflow_modelos, workflow_modelo_etapas e workflow_modelo_etapa_responsaveis

Ver app/models/workflow_modelo.py, workflow_modelo_etapa.py e
workflow_modelo_etapa_responsavel.py. Não toca em nenhuma tabela existente.

Revision ID: 370addf85190
Revises: d6b1a9f04c58
Create Date: 2026-08-15 21:08:16.077139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '370addf85190'
down_revision: Union[str, None] = 'd6b1a9f04c58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workflow_modelos',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('codigo_interno', sa.String(length=64), nullable=False),
        sa.Column('codigo_referencia', sa.String(length=16), nullable=False),
        sa.Column('ano_referencia', sa.SmallInteger(), nullable=False),
        sa.Column('sequencial_referencia', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arquivado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('motivo_arquivamento', sa.String(length=500), nullable=True),
        sa.Column('restaurado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restaurado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('status_anterior_arquivamento', sa.String(length=32), nullable=True),
        sa.CheckConstraint("status IN ('ativo', 'inativo', 'arquivado')", name='ck_workflow_modelos_status'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'codigo_interno', name='uq_workflow_modelos_empresa_codigo_interno'),
        sa.UniqueConstraint('empresa_id', 'codigo_referencia', name='uq_workflow_modelos_empresa_codigo_referencia'),
        sa.UniqueConstraint(
            'empresa_id', 'ano_referencia', 'sequencial_referencia',
            name='uq_workflow_modelos_empresa_ano_sequencial',
        ),
        sa.UniqueConstraint('empresa_id', 'nome_normalizado', name='uq_workflow_modelos_empresa_nome_normalizado'),
    )
    op.create_index('ix_workflow_modelos_empresa_id', 'workflow_modelos', ['empresa_id'])
    op.create_index('ix_workflow_modelos_status', 'workflow_modelos', ['status'])
    op.create_index('ix_workflow_modelos_codigo_referencia', 'workflow_modelos', ['codigo_referencia'])
    op.create_index('ix_workflow_modelos_codigo_interno', 'workflow_modelos', ['codigo_interno'])
    op.create_index('ix_workflow_modelos_nome_normalizado', 'workflow_modelos', ['nome_normalizado'])

    op.create_table(
        'workflow_modelo_etapas',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_modelo_id', sa.String(length=36), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('tipo', sa.String(length=32), nullable=False),
        sa.Column('quantidade_antes_deadline', sa.Integer(), nullable=False),
        sa.Column('unidade_prazo', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("tipo IN ('execucao', 'aprovacao')", name='ck_workflow_modelo_etapas_tipo'),
        sa.CheckConstraint(
            "unidade_prazo IN ('dias_corridos', 'dias_uteis', 'horas')",
            name='ck_workflow_modelo_etapas_unidade_prazo',
        ),
        sa.ForeignKeyConstraint(['workflow_modelo_id'], ['workflow_modelos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_workflow_modelo_etapas_modelo_ordem', 'workflow_modelo_etapas', ['workflow_modelo_id', 'ordem']
    )

    op.create_table(
        'workflow_modelo_etapa_responsaveis',
        sa.Column('workflow_modelo_etapa_id', sa.String(length=36), nullable=False),
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workflow_modelo_etapa_id'], ['workflow_modelo_etapas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workflow_modelo_etapa_id', 'usuario_id'),
    )
    op.create_index(
        'ix_workflow_modelo_etapa_responsaveis_usuario_id', 'workflow_modelo_etapa_responsaveis', ['usuario_id']
    )


def downgrade() -> None:
    op.drop_index(
        'ix_workflow_modelo_etapa_responsaveis_usuario_id', table_name='workflow_modelo_etapa_responsaveis'
    )
    op.drop_table('workflow_modelo_etapa_responsaveis')
    op.drop_index('ix_workflow_modelo_etapas_modelo_ordem', table_name='workflow_modelo_etapas')
    op.drop_table('workflow_modelo_etapas')
    op.drop_index('ix_workflow_modelos_nome_normalizado', table_name='workflow_modelos')
    op.drop_index('ix_workflow_modelos_codigo_interno', table_name='workflow_modelos')
    op.drop_index('ix_workflow_modelos_codigo_referencia', table_name='workflow_modelos')
    op.drop_index('ix_workflow_modelos_status', table_name='workflow_modelos')
    op.drop_index('ix_workflow_modelos_empresa_id', table_name='workflow_modelos')
    op.drop_table('workflow_modelos')
