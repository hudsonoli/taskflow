"""tipo_tarefa

Ver app/models/tipo_tarefa.py. Não toca em nenhuma tabela existente.

Revision ID: 39b960876eb7
Revises: 43247bb6e713
Create Date: 2026-08-20 14:59:45.093740

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39b960876eb7'
down_revision: Union[str, None] = '43247bb6e713'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tipos_tarefa',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arquivado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('motivo_arquivamento', sa.String(length=500), nullable=True),
        sa.Column('restaurado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restaurado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('status_anterior_arquivamento', sa.String(length=32), nullable=True),
        sa.CheckConstraint("status IN ('ativo', 'inativo', 'arquivado')", name='ck_tipos_tarefa_status'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'nome_normalizado', name='uq_tipos_tarefa_empresa_nome_normalizado'),
    )
    op.create_index('ix_tipos_tarefa_empresa_id', 'tipos_tarefa', ['empresa_id'])
    op.create_index('ix_tipos_tarefa_status', 'tipos_tarefa', ['status'])
    op.create_index('ix_tipos_tarefa_nome_normalizado', 'tipos_tarefa', ['nome_normalizado'])


def downgrade() -> None:
    op.drop_index('ix_tipos_tarefa_nome_normalizado', table_name='tipos_tarefa')
    op.drop_index('ix_tipos_tarefa_status', table_name='tipos_tarefa')
    op.drop_index('ix_tipos_tarefa_empresa_id', table_name='tipos_tarefa')
    op.drop_table('tipos_tarefa')
