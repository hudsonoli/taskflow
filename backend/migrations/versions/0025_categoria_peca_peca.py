"""categoria_peca_peca

Ver app/models/categoria_peca.py e app/models/peca.py. Não toca em nenhuma tabela existente.
Sem catálogo tenant-specific aqui — dado real vem do import (app/cli/importar_pecas.py),
separado da migration estrutural.

Revision ID: 676e5b234084
Revises: a093e92015a6
Create Date: 2026-08-22 23:19:20.481985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '676e5b234084'
down_revision: Union[str, None] = 'a093e92015a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'categorias_peca',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=100), nullable=False),
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
        sa.CheckConstraint("status IN ('ativo', 'arquivado')", name='ck_categorias_peca_status'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'nome_normalizado', name='uq_categorias_peca_empresa_nome_normalizado'),
    )
    op.create_index('ix_categorias_peca_empresa_id', 'categorias_peca', ['empresa_id'])
    op.create_index('ix_categorias_peca_status', 'categorias_peca', ['status'])
    op.create_index('ix_categorias_peca_nome_normalizado', 'categorias_peca', ['nome_normalizado'])

    op.create_table(
        'pecas',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('categoria_id', sa.String(length=36), nullable=True),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('codigo_legado', sa.String(length=64), nullable=True),
        sa.Column('tempo_estimado_minutos', sa.Integer(), nullable=True),
        sa.Column('tempo_medio_minutos', sa.Integer(), nullable=True),
        sa.Column('tempo_calculado_execucao_minutos', sa.Integer(), nullable=True),
        sa.Column('valor_tabela_centavos', sa.BigInteger(), nullable=True),
        sa.Column('sindicato_ativo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('valor_sindicato_criacao_centavos', sa.BigInteger(), nullable=True),
        sa.Column('valor_sindicato_adaptacao_centavos', sa.BigInteger(), nullable=True),
        sa.Column('valor_sindicato_finalizacao_centavos', sa.BigInteger(), nullable=True),
        sa.Column('briefing_padrao', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arquivado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('motivo_arquivamento', sa.String(length=500), nullable=True),
        sa.Column('restaurado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restaurado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('status_anterior_arquivamento', sa.String(length=32), nullable=True),
        sa.CheckConstraint("status IN ('ativo', 'inativo', 'arquivado')", name='ck_pecas_status'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.ForeignKeyConstraint(['categoria_id'], ['categorias_peca.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'codigo_legado', name='uq_pecas_empresa_codigo_legado'),
    )
    op.create_index('ix_pecas_empresa_id', 'pecas', ['empresa_id'])
    op.create_index('ix_pecas_categoria_id', 'pecas', ['categoria_id'])
    op.create_index('ix_pecas_status', 'pecas', ['status'])


def downgrade() -> None:
    op.drop_index('ix_pecas_status', table_name='pecas')
    op.drop_index('ix_pecas_categoria_id', table_name='pecas')
    op.drop_index('ix_pecas_empresa_id', table_name='pecas')
    op.drop_table('pecas')

    op.drop_index('ix_categorias_peca_nome_normalizado', table_name='categorias_peca')
    op.drop_index('ix_categorias_peca_status', table_name='categorias_peca')
    op.drop_index('ix_categorias_peca_empresa_id', table_name='categorias_peca')
    op.drop_table('categorias_peca')
