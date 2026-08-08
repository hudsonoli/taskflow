"""usuario.departamento_uuid (expansão — D1)

Primeiro passo do expand/contract de `usuarios.departamento_id`, que hoje é
`varchar(64)` guardando o NOME do departamento em texto livre ("Criação").

Esta migration **só adiciona** a coluna nova, vazia:
- não cria FK (D2);
- não faz backfill (D2);
- não altera, renomeia nem remove `departamento_id` legado (D3);
- nenhuma camada da aplicação lê `departamento_uuid` ainda.

Depois dela os 40 usuários continuam com `departamento_uuid` NULL e o comportamento do
sistema é idêntico ao anterior.

Revision ID: 090ecbc4f863
Revises: 06092bd6fdb9
Create Date: 2026-08-06 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '090ecbc4f863'
down_revision: Union[str, None] = '06092bd6fdb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('departamento_uuid', sa.String(length=36), nullable=True))
    # Índice justificado pelo uso já previsto: filtro "usuários do departamento X" na
    # listagem administrativa e no escopo de Meu Departamento, que passam a usar esta
    # coluna a partir de D3.
    op.create_index('ix_usuarios_departamento_uuid', 'usuarios', ['departamento_uuid'])


def downgrade() -> None:
    # Reversível sem perda: a coluna está vazia em D1 (o backfill só acontece em D2).
    op.drop_index('ix_usuarios_departamento_uuid', table_name='usuarios')
    op.drop_column('usuarios', 'departamento_uuid')
