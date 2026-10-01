"""usuario_google

Login Google Workspace para usuário pré-cadastrado. Adiciona SOMENTE colunas auxiliares de
identidade Google em `usuarios` — nenhuma delas participa de RBAC (perfil_base/departamento/
permissões continuam exclusivamente controlados pelo TaskFloww, ver app/services/auth_service.py).

`google_sub` é UNIQUE globalmente (não por empresa): o `sub` de uma conta Google é único no
mundo, então o índice único também impede que a mesma conta Google seja vinculada a dois
usuários TaskFloww (mesmo em empresas diferentes). Nullable porque a imensa maioria dos
usuários nunca vinculará Google — e múltiplos NULL são permitidos por uma UNIQUE constraint no
Postgres (NULL nunca é igual a NULL).

Revision ID: 57c9ac75e1bc
Revises: 31d8b31f86f0
Create Date: 2026-09-30 22:29:57.330747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57c9ac75e1bc'
down_revision: Union[str, None] = '31d8b31f86f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('google_sub', sa.String(length=255), nullable=True))
    op.add_column('usuarios', sa.Column('google_linked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('usuarios', sa.Column('last_google_login_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('usuarios', sa.Column('google_given_name', sa.String(length=255), nullable=True))
    op.add_column('usuarios', sa.Column('google_family_name', sa.String(length=255), nullable=True))
    op.add_column('usuarios', sa.Column('google_locale', sa.String(length=32), nullable=True))
    op.create_unique_constraint('uq_usuarios_google_sub', 'usuarios', ['google_sub'])


def downgrade() -> None:
    op.drop_constraint('uq_usuarios_google_sub', 'usuarios', type_='unique')
    op.drop_column('usuarios', 'google_locale')
    op.drop_column('usuarios', 'google_family_name')
    op.drop_column('usuarios', 'google_given_name')
    op.drop_column('usuarios', 'last_google_login_at')
    op.drop_column('usuarios', 'google_linked_at')
    op.drop_column('usuarios', 'google_sub')
