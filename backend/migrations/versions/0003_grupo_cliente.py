"""grupo_cliente

Revision ID: 422df1665a6c
Revises: 76f7f6fb4a70
Create Date: 2026-08-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '422df1665a6c'
down_revision: Union[str, None] = '76f7f6fb4a70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'grupos_cliente',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('codigo_interno', sa.String(length=64), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=255), nullable=False),
        sa.Column('cor_identificacao', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arquivado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('motivo_arquivamento', sa.String(length=500), nullable=True),
        sa.Column('restaurado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restaurado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('status_anterior_arquivamento', sa.String(length=32), nullable=True),
        sa.CheckConstraint("status IN ('ativo', 'arquivado')", name='ck_grupos_cliente_status'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'codigo_interno', name='uq_grupos_cliente_empresa_codigo_interno'),
        sa.UniqueConstraint('empresa_id', 'nome_normalizado', name='uq_grupos_cliente_empresa_nome_normalizado'),
    )
    op.create_index('ix_grupos_cliente_empresa_id', 'grupos_cliente', ['empresa_id'])
    op.create_index('ix_grupos_cliente_status', 'grupos_cliente', ['status'])


def downgrade() -> None:
    op.drop_index('ix_grupos_cliente_status', table_name='grupos_cliente')
    op.drop_index('ix_grupos_cliente_empresa_id', table_name='grupos_cliente')
    op.drop_table('grupos_cliente')
