"""modelo_campanha

Ver app/models/modelo_campanha.py. Cria só a biblioteca (Fase 2G.5A) — não toca em `projetos`
nem em nenhuma outra tabela existente. Nenhum vínculo com Projeto ainda (fica pra 2G.5C).

Revision ID: b2c7674f4f94
Revises: 676e5b234084
Create Date: 2026-08-24 11:24:43.476459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c7674f4f94'
down_revision: Union[str, None] = '676e5b234084'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'modelos_campanha',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arquivado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('motivo_arquivamento', sa.String(length=500), nullable=True),
        sa.Column('restaurado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restaurado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('status_anterior_arquivamento', sa.String(length=32), nullable=True),
        sa.CheckConstraint("status IN ('ativo', 'inativo', 'arquivado')", name='ck_modelos_campanha_status'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'nome_normalizado', name='uq_modelos_campanha_empresa_nome_normalizado'),
    )
    op.create_index('ix_modelos_campanha_empresa_id', 'modelos_campanha', ['empresa_id'])
    op.create_index('ix_modelos_campanha_status', 'modelos_campanha', ['status'])
    op.create_index('ix_modelos_campanha_nome_normalizado', 'modelos_campanha', ['nome_normalizado'])

    op.create_table(
        'modelos_campanha_itens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('modelo_campanha_id', sa.String(length=36), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('briefing_padrao', sa.Text(), nullable=True),
        sa.Column('prioridade_padrao', sa.String(length=16), nullable=False, server_default='media'),
        sa.Column('peca_id', sa.String(length=36), nullable=True),
        sa.Column('tipo_tarefa_id', sa.String(length=36), nullable=True),
        sa.Column('workflow_modelo_id', sa.String(length=36), nullable=True),
        sa.Column('responsavel_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('responsavel_departamento_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "prioridade_padrao IN ('baixa', 'media', 'alta')", name='ck_modelos_campanha_itens_prioridade'
        ),
        sa.CheckConstraint("ordem >= 1", name='ck_modelos_campanha_itens_ordem'),
        sa.CheckConstraint(
            "NOT (responsavel_usuario_id IS NOT NULL AND responsavel_departamento_id IS NOT NULL)",
            name='ck_modelos_campanha_itens_responsavel_unico',
        ),
        sa.ForeignKeyConstraint(['modelo_campanha_id'], ['modelos_campanha.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['peca_id'], ['pecas.id']),
        sa.ForeignKeyConstraint(['tipo_tarefa_id'], ['tipos_tarefa.id']),
        sa.ForeignKeyConstraint(['workflow_modelo_id'], ['workflow_modelos.id']),
        sa.ForeignKeyConstraint(['responsavel_usuario_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['responsavel_departamento_id'], ['departamentos.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('modelo_campanha_id', 'ordem', name='uq_modelos_campanha_itens_modelo_ordem'),
    )
    op.create_index('ix_modelos_campanha_itens_modelo_id', 'modelos_campanha_itens', ['modelo_campanha_id'])
    op.create_index('ix_modelos_campanha_itens_peca_id', 'modelos_campanha_itens', ['peca_id'])
    op.create_index('ix_modelos_campanha_itens_tipo_tarefa_id', 'modelos_campanha_itens', ['tipo_tarefa_id'])
    op.create_index('ix_modelos_campanha_itens_workflow_modelo_id', 'modelos_campanha_itens', ['workflow_modelo_id'])


def downgrade() -> None:
    op.drop_index('ix_modelos_campanha_itens_workflow_modelo_id', table_name='modelos_campanha_itens')
    op.drop_index('ix_modelos_campanha_itens_tipo_tarefa_id', table_name='modelos_campanha_itens')
    op.drop_index('ix_modelos_campanha_itens_peca_id', table_name='modelos_campanha_itens')
    op.drop_index('ix_modelos_campanha_itens_modelo_id', table_name='modelos_campanha_itens')
    op.drop_table('modelos_campanha_itens')

    op.drop_index('ix_modelos_campanha_nome_normalizado', table_name='modelos_campanha')
    op.drop_index('ix_modelos_campanha_status', table_name='modelos_campanha')
    op.drop_index('ix_modelos_campanha_empresa_id', table_name='modelos_campanha')
    op.drop_table('modelos_campanha')
