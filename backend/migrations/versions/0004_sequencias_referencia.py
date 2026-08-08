"""sequencias_referencia

Contador de códigos de referência por empresa + tipo de entidade + ano.
Ver app/core/referencias.py.

Revision ID: fdd5609850d0
Revises: 422df1665a6c
Create Date: 2026-08-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdd5609850d0'
down_revision: Union[str, None] = '422df1665a6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sequencias_referencia',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('tipo_entidade', sa.String(length=32), nullable=False),
        sa.Column('ano', sa.SmallInteger(), nullable=False),
        sa.Column('ultimo_numero', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
        # Escopo do contador. É esta constraint que o ON CONFLICT usa para o UPSERT atômico.
        sa.UniqueConstraint('empresa_id', 'tipo_entidade', 'ano', name='uq_sequencias_referencia_escopo'),
    )
    op.create_index('ix_sequencias_referencia_empresa_id', 'sequencias_referencia', ['empresa_id'])


def downgrade() -> None:
    op.drop_index('ix_sequencias_referencia_empresa_id', table_name='sequencias_referencia')
    op.drop_table('sequencias_referencia')
