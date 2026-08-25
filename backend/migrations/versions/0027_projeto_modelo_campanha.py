"""projeto_modelo_campanha

Ver app/models/projeto_modelo_campanha.py. Cria só o schema do snapshot (Fase 2G.5C1) — não
toca em `projetos` (nem `modelo_campanha`, nem `modelo_campanha_id`) nem em nenhuma outra
tabela existente. Sem service/rota/frontend ainda (Fase 2G.5C2 em diante).

Revision ID: 2cb9f5dcaba9
Revises: b2c7674f4f94
Create Date: 2026-08-25 12:20:10.610770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cb9f5dcaba9'
down_revision: Union[str, None] = 'b2c7674f4f94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'projeto_modelo_campanha',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('projeto_id', sa.String(length=36), nullable=False),
        sa.Column('modelo_campanha_origem_id', sa.String(length=36), nullable=True),
        sa.Column('modelo_campanha_nome_snapshot', sa.String(length=255), nullable=True),
        sa.Column('aplicado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('aplicado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['projeto_id'], ['projetos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['modelo_campanha_origem_id'], ['modelos_campanha.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('projeto_id', name='uq_projeto_modelo_campanha_projeto_id'),
    )
    op.create_index(
        'ix_projeto_modelo_campanha_origem_id', 'projeto_modelo_campanha', ['modelo_campanha_origem_id']
    )

    op.create_table(
        'projeto_modelo_campanha_itens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('projeto_modelo_campanha_id', sa.String(length=36), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('briefing_padrao', sa.Text(), nullable=True),
        sa.Column('prioridade_padrao', sa.String(length=16), nullable=False, server_default='media'),
        sa.Column('peca_id', sa.String(length=36), nullable=True),
        sa.Column('peca_nome_snapshot', sa.String(length=255), nullable=True),
        sa.Column('tipo_tarefa_id', sa.String(length=36), nullable=True),
        sa.Column('tipo_tarefa_nome_snapshot', sa.String(length=255), nullable=True),
        sa.Column('workflow_modelo_id', sa.String(length=36), nullable=True),
        sa.Column('workflow_modelo_nome_snapshot', sa.String(length=255), nullable=True),
        sa.Column('responsavel_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('responsavel_usuario_nome_snapshot', sa.String(length=255), nullable=True),
        sa.Column('responsavel_departamento_id', sa.String(length=36), nullable=True),
        sa.Column('responsavel_departamento_nome_snapshot', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "prioridade_padrao IN ('baixa', 'media', 'alta')", name='ck_projeto_modelo_campanha_itens_prioridade'
        ),
        sa.CheckConstraint("ordem >= 1", name='ck_projeto_modelo_campanha_itens_ordem'),
        sa.CheckConstraint(
            "NOT (responsavel_usuario_id IS NOT NULL AND responsavel_departamento_id IS NOT NULL)",
            name='ck_projeto_modelo_campanha_itens_responsavel_unico',
        ),
        sa.ForeignKeyConstraint(
            ['projeto_modelo_campanha_id'], ['projeto_modelo_campanha.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['peca_id'], ['pecas.id']),
        sa.ForeignKeyConstraint(['tipo_tarefa_id'], ['tipos_tarefa.id']),
        sa.ForeignKeyConstraint(['workflow_modelo_id'], ['workflow_modelos.id']),
        sa.ForeignKeyConstraint(['responsavel_usuario_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['responsavel_departamento_id'], ['departamentos.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('projeto_modelo_campanha_id', 'ordem', name='uq_projeto_modelo_campanha_itens_ordem'),
    )
    op.create_index(
        'ix_projeto_modelo_campanha_itens_cabecalho_id',
        'projeto_modelo_campanha_itens',
        ['projeto_modelo_campanha_id'],
    )
    op.create_index(
        'ix_projeto_modelo_campanha_itens_peca_id', 'projeto_modelo_campanha_itens', ['peca_id']
    )
    op.create_index(
        'ix_projeto_modelo_campanha_itens_tipo_tarefa_id', 'projeto_modelo_campanha_itens', ['tipo_tarefa_id']
    )
    op.create_index(
        'ix_projeto_modelo_campanha_itens_workflow_modelo_id',
        'projeto_modelo_campanha_itens',
        ['workflow_modelo_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_projeto_modelo_campanha_itens_workflow_modelo_id', table_name='projeto_modelo_campanha_itens')
    op.drop_index('ix_projeto_modelo_campanha_itens_tipo_tarefa_id', table_name='projeto_modelo_campanha_itens')
    op.drop_index('ix_projeto_modelo_campanha_itens_peca_id', table_name='projeto_modelo_campanha_itens')
    op.drop_index('ix_projeto_modelo_campanha_itens_cabecalho_id', table_name='projeto_modelo_campanha_itens')
    op.drop_table('projeto_modelo_campanha_itens')

    op.drop_index('ix_projeto_modelo_campanha_origem_id', table_name='projeto_modelo_campanha')
    op.drop_table('projeto_modelo_campanha')
