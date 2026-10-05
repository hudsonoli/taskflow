"""password_reset

Recuperação de senha self-service. Adiciona SOMENTE três colunas nullable em
`usuario_credenciais` (onde já vivem o hash da senha local, as tentativas e o bloqueio) — nada
em `usuarios`, nenhuma tabela nova, nenhum dado existente alterado:

  reset_senha_token_hash     SHA-256 (hex, 64) do token enviado por e-mail — NUNCA o token
  reset_senha_expira_em      fim da validade do token (30 minutos após a solicitação)
  reset_senha_solicitado_em  instante do último pedido (cooldown entre pedidos)

`reset_senha_token_hash` é UNIQUE: além de impedir colisão, é o índice do lookup do confirm
(`SHA-256(token recebido) -> credencial`). NULL repetido é permitido pela UNIQUE do Postgres,
e a imensa maioria das credenciais nunca terá reset pendente. Credencial sem as colunas
preenchidas (todas as existentes hoje) segue exatamente como antes.

Revision ID: 3b7f1a9c52d4
Revises: e4464f8f7bb9
Create Date: 2026-10-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b7f1a9c52d4'
down_revision: Union[str, None] = 'e4464f8f7bb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuario_credenciais', sa.Column('reset_senha_token_hash', sa.String(length=64), nullable=True))
    op.add_column('usuario_credenciais', sa.Column('reset_senha_expira_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column('usuario_credenciais', sa.Column('reset_senha_solicitado_em', sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint(
        'uq_usuario_credenciais_reset_senha_token_hash', 'usuario_credenciais', ['reset_senha_token_hash']
    )


def downgrade() -> None:
    op.drop_constraint('uq_usuario_credenciais_reset_senha_token_hash', 'usuario_credenciais', type_='unique')
    op.drop_column('usuario_credenciais', 'reset_senha_solicitado_em')
    op.drop_column('usuario_credenciais', 'reset_senha_expira_em')
    op.drop_column('usuario_credenciais', 'reset_senha_token_hash')
