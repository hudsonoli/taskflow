"""demanda_comentarios

Ver app/models/demanda_comentario.py (Fase 2E.4). Histórico não cria tabela — lê de `eventos`,
já existente. Não toca em nenhuma tabela existente.

Revision ID: 43247bb6e713
Revises: d2f456941501
Create Date: 2026-08-16 18:02:32.613264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43247bb6e713'
down_revision: Union[str, None] = 'd2f456941501'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'demanda_comentarios',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('demanda_id', sa.String(length=36), nullable=False),
        sa.Column('autor_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('texto', sa.String(length=4000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('editado_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['demanda_id'], ['demandas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['autor_usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_demanda_comentarios_demanda_id', 'demanda_comentarios', ['demanda_id'])


def downgrade() -> None:
    op.drop_index('ix_demanda_comentarios_demanda_id', table_name='demanda_comentarios')
    op.drop_table('demanda_comentarios')
