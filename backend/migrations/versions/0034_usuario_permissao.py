"""usuario_permissao

Fase 2G.10A — fundação de permissões configuráveis. Cria SOMENTE a tabela de exceções
individuais (`usuario_permissao`). Não altera `usuarios.perfil_base` nem
`ck_usuarios_perfil_base`, não altera nenhuma outra tabela, não popula dado nenhum — a tabela
nasce vazia e nenhuma rota a consulta ainda (ver app/core/permissoes.py e
app/services/usuario_permissao_service.py).

Revision ID: 31d8b31f86f0
Revises: ba64228ee8e1
Create Date: 2026-09-11 14:40:29.263875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31d8b31f86f0'
down_revision: Union[str, None] = 'ba64228ee8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'usuario_permissao',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        sa.Column('permissao', sa.String(length=80), nullable=False),
        sa.Column('efeito', sa.String(length=10), nullable=False),
        sa.Column('motivo', sa.String(length=500), nullable=True),
        sa.Column('concedido_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "efeito IN ('conceder', 'negar')",
            name='ck_usuario_permissao_efeito',
        ),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('usuario_id', 'permissao', name='uq_usuario_permissao_usuario_permissao'),
    )
    op.create_index('ix_usuario_permissao_empresa_id', 'usuario_permissao', ['empresa_id'])
    op.create_index('ix_usuario_permissao_usuario_id', 'usuario_permissao', ['usuario_id'])


def downgrade() -> None:
    op.drop_index('ix_usuario_permissao_usuario_id', table_name='usuario_permissao')
    op.drop_index('ix_usuario_permissao_empresa_id', table_name='usuario_permissao')
    op.drop_table('usuario_permissao')
