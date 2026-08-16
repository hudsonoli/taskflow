"""demanda_checklist_arquivos

Ver app/models/demanda_checklist_item.py e app/models/demanda_arquivo.py (Fase 2E.3). Não
toca em nenhuma tabela existente.

Revision ID: d2f456941501
Revises: 89ff6c49ff70
Create Date: 2026-08-16 14:46:03.705506

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2f456941501'
down_revision: Union[str, None] = '89ff6c49ff70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'demanda_checklist_itens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('demanda_id', sa.String(length=36), nullable=False),
        sa.Column('texto', sa.String(length=500), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('concluido', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('concluido_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('concluido_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('criado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['demanda_id'], ['demandas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['concluido_por_usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['criado_por_usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_demanda_checklist_itens_demanda_ordem', 'demanda_checklist_itens', ['demanda_id', 'ordem']
    )

    op.create_table(
        'demanda_arquivos',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('demanda_id', sa.String(length=36), nullable=False),
        sa.Column('nome_original', sa.String(length=255), nullable=False),
        sa.Column('nome_fisico', sa.String(length=64), nullable=False),
        sa.Column('content_type', sa.String(length=128), nullable=True),
        sa.Column('tamanho_bytes', sa.Integer(), nullable=False),
        sa.Column('enviado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['demanda_id'], ['demandas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['enviado_por_usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_demanda_arquivos_demanda_id', 'demanda_arquivos', ['demanda_id'])


def downgrade() -> None:
    op.drop_index('ix_demanda_arquivos_demanda_id', table_name='demanda_arquivos')
    op.drop_table('demanda_arquivos')

    op.drop_index('ix_demanda_checklist_itens_demanda_ordem', table_name='demanda_checklist_itens')
    op.drop_table('demanda_checklist_itens')
