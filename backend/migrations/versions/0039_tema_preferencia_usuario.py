"""tema_preferencia_usuario

Preferência PESSOAL de tema (claro | escuro | sistema) em `usuarios`. Migration ADITIVA: uma coluna
nullable, sem default e sem reescrever nenhuma linha — todo usuário existente fica NULL, que significa
"usar o tema padrão da empresa" (comportamento atual). Sem downtime.

Reversível: `downgrade` remove o CHECK e a coluna.

Revision ID: 7c1e9b4d2a50
Revises: 48bd07aba026
Create Date: 2026-10-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1e9b4d2a50'
down_revision: Union[str, None] = '48bd07aba026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('tema_preferencia', sa.String(length=16), nullable=True))
    op.create_check_constraint(
        'ck_usuarios_tema_preferencia',
        'usuarios',
        "tema_preferencia IS NULL OR tema_preferencia IN ('claro', 'escuro', 'sistema')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_usuarios_tema_preferencia', 'usuarios', type_='check')
    op.drop_column('usuarios', 'tema_preferencia')
