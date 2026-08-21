"""regra_expediente

Ver app/models/regra_expediente.py. Não toca em nenhuma tabela existente.

Revision ID: a093e92015a6
Revises: 39b960876eb7
Create Date: 2026-08-20 21:27:44.917444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a093e92015a6'
down_revision: Union[str, None] = '39b960876eb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'regra_expediente',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('tolerancia_retomada_minutos', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', name='uq_regra_expediente_empresa_id'),
    )
    op.create_index('ix_regra_expediente_empresa_id', 'regra_expediente', ['empresa_id'])

    op.create_table(
        'regra_expediente_dias',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('regra_expediente_id', sa.String(length=36), nullable=False),
        sa.Column('dia_semana', sa.SmallInteger(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('manha_inicio', sa.Time(), nullable=True),
        sa.Column('manha_fim', sa.Time(), nullable=True),
        sa.Column('tarde_inicio', sa.Time(), nullable=True),
        sa.Column('tarde_fim', sa.Time(), nullable=True),
        sa.CheckConstraint('dia_semana >= 0 AND dia_semana <= 6', name='ck_regra_expediente_dias_dia_semana'),
        sa.CheckConstraint(
            "NOT ativo OR ("
            "manha_inicio IS NOT NULL AND manha_fim IS NOT NULL AND "
            "tarde_inicio IS NOT NULL AND tarde_fim IS NOT NULL AND "
            "manha_inicio < manha_fim AND tarde_inicio < tarde_fim AND manha_fim <= tarde_inicio"
            ")",
            name='ck_regra_expediente_dias_janelas_validas',
        ),
        sa.ForeignKeyConstraint(['regra_expediente_id'], ['regra_expediente.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('regra_expediente_id', 'dia_semana', name='uq_regra_expediente_dias_regra_dia'),
    )
    op.create_index('ix_regra_expediente_dias_regra_id', 'regra_expediente_dias', ['regra_expediente_id'])


def downgrade() -> None:
    op.drop_index('ix_regra_expediente_dias_regra_id', table_name='regra_expediente_dias')
    op.drop_table('regra_expediente_dias')
    op.drop_index('ix_regra_expediente_empresa_id', table_name='regra_expediente')
    op.drop_table('regra_expediente')
