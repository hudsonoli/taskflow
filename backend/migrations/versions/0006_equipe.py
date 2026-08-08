"""equipes e equipe_membros

Ver app/models/equipe.py e app/models/equipe_membro.py. Não toca em nenhuma tabela
existente.

Revision ID: 06092bd6fdb9
Revises: 66d999083d82
Create Date: 2026-08-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06092bd6fdb9'
down_revision: Union[str, None] = '66d999083d82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'equipes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('codigo_interno', sa.String(length=64), nullable=False),
        sa.Column('codigo_referencia', sa.String(length=16), nullable=False),
        sa.Column('ano_referencia', sa.SmallInteger(), nullable=False),
        sa.Column('sequencial_referencia', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        # NULL = equipe transversal.
        sa.Column('departamento_id', sa.String(length=36), nullable=True),
        sa.Column('lider_usuario_id', sa.String(length=36), nullable=True),
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
        sa.CheckConstraint("status IN ('ativo', 'inativo', 'arquivado')", name='ck_equipes_status'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.ForeignKeyConstraint(['departamento_id'], ['departamentos.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lider_usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'codigo_interno', name='uq_equipes_empresa_codigo_interno'),
        sa.UniqueConstraint('empresa_id', 'codigo_referencia', name='uq_equipes_empresa_codigo_referencia'),
        sa.UniqueConstraint(
            'empresa_id', 'ano_referencia', 'sequencial_referencia', name='uq_equipes_empresa_ano_sequencial'
        ),
        sa.UniqueConstraint('empresa_id', 'nome_normalizado', name='uq_equipes_empresa_nome_normalizado'),
    )
    op.create_index('ix_equipes_empresa_id', 'equipes', ['empresa_id'])
    op.create_index('ix_equipes_status', 'equipes', ['status'])
    op.create_index('ix_equipes_codigo_referencia', 'equipes', ['codigo_referencia'])
    op.create_index('ix_equipes_codigo_interno', 'equipes', ['codigo_interno'])
    op.create_index('ix_equipes_nome_normalizado', 'equipes', ['nome_normalizado'])
    op.create_index('ix_equipes_departamento_id', 'equipes', ['departamento_id'])

    op.create_table(
        'equipe_membros',
        sa.Column('equipe_id', sa.String(length=36), nullable=False),
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['equipe_id'], ['equipes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('equipe_id', 'usuario_id'),
    )
    op.create_index('ix_equipe_membros_usuario_id', 'equipe_membros', ['usuario_id'])


def downgrade() -> None:
    op.drop_index('ix_equipe_membros_usuario_id', table_name='equipe_membros')
    op.drop_table('equipe_membros')
    op.drop_index('ix_equipes_departamento_id', table_name='equipes')
    op.drop_index('ix_equipes_nome_normalizado', table_name='equipes')
    op.drop_index('ix_equipes_codigo_interno', table_name='equipes')
    op.drop_index('ix_equipes_codigo_referencia', table_name='equipes')
    op.drop_index('ix_equipes_status', table_name='equipes')
    op.drop_index('ix_equipes_empresa_id', table_name='equipes')
    op.drop_table('equipes')
