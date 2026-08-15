"""sessoes_trabalho.usuario_uuid / departamento_uuid (expansão — D1)

Primeiro passo do expand/contract de `sessoes_trabalho.usuario_id`/`departamento_id`, que
hoje são `varchar(128)` guardando ids do mock antigo (`"user-1"`) sem FK — mesmo problema já
resolvido para `usuarios.departamento_id` em `0007`/`0008`/`0009`, aqui reaplicado.

Esta migration **só adiciona** as colunas novas, vazias:
- não cria FK (D2 — `0016`);
- não faz backfill (D2 — `0016`);
- não altera, renomeia nem remove `usuario_id`/`departamento_id` legados (D3 — `0018`);
- nenhuma camada da aplicação lê `usuario_uuid`/`departamento_uuid` ainda.

Depois dela toda sessão continua com as colunas novas em `NULL` e o comportamento do sistema
é idêntico ao anterior. A escrita dupla (gravar o mesmo UUID nas duas famílias de coluna)
começa no código da aplicação, não nesta migration — ver `SessaoTrabalhoService.open_session`.

Revision ID: a3f7c1e92b4d
Revises: 5f1c9e73b204
Create Date: 2026-08-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f7c1e92b4d'
down_revision: Union[str, None] = '5f1c9e73b204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sessoes_trabalho', sa.Column('usuario_uuid', sa.String(length=36), nullable=True))
    op.add_column('sessoes_trabalho', sa.Column('departamento_uuid', sa.String(length=36), nullable=True))
    op.create_index('ix_sessoes_trabalho_usuario_uuid', 'sessoes_trabalho', ['usuario_uuid'])
    op.create_index('ix_sessoes_trabalho_departamento_uuid', 'sessoes_trabalho', ['departamento_uuid'])


def downgrade() -> None:
    # Reversível sem perda: as colunas estão vazias em D1 (o backfill só acontece em D2/0016).
    op.drop_index('ix_sessoes_trabalho_departamento_uuid', table_name='sessoes_trabalho')
    op.drop_index('ix_sessoes_trabalho_usuario_uuid', table_name='sessoes_trabalho')
    op.drop_column('sessoes_trabalho', 'departamento_uuid')
    op.drop_column('sessoes_trabalho', 'usuario_uuid')
