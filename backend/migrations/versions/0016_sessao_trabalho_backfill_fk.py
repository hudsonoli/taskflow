"""sessoes_trabalho.usuario_uuid / departamento_uuid: backfill comprovável + FK (D2)

Segundo passo do expand/contract. Resolve `usuario_id`/`departamento_id` (texto legado) para
`usuarios.id`/`departamentos.id` **só onde comprovável**, e cria a FK.

## Por que este backfill é mais permissivo que o de `0008`

`0008` (Departamento em Usuário) abortava se um valor legado não tivesse correspondência
única — porque ali o texto era o NOME do departamento, e nome sem correspondência normalmente
sinaliza erro de digitação ou departamento renomeado, algo a corrigir, não a aceitar.

Aqui o texto é um id de mock (`"user-1"`) que **nunca existiu** como referência real — não há
erro de digitação a corrigir, só dado histórico do qual não sobrou correspondência. Backfill
sem correspondência permanece `NULL`, deliberadamente, sem segundo critério nem heurística de
fallback. Não é abortante: linha órfã aqui é esperada, não uma anomalia.

## Não retrabalha o que a escrita dupla já fez

Toda sessão criada depois de `0015` (ver `SessaoTrabalhoService.open_session`) já grava o
mesmo UUID real nas duas colunas — a cláusula `WHERE usuario_uuid IS NULL` restringe o
UPDATE às linhas herdadas de antes de `0015`, que são as únicas que precisam de resolução.

## Escopo por empresa

A correspondência exige `u.empresa_id = s.empresa_id` (idem para departamento) — um usuário
de OUTRA empresa com o mesmo `codigo_interno` nunca é usado. É isto que torna o vazamento
cross-tenant impossível no backfill, não uma regra de aplicação.

NÃO faz nesta etapa (é D3 — `0018`): DROP das colunas legadas, rename, mudança de schema
público, alteração de frontend.

Revision ID: b8e4d06c1f73
Revises: a3f7c1e92b4d
Create Date: 2026-08-10 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e4d06c1f73'
down_revision: Union[str, None] = 'a3f7c1e92b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conexao = op.get_bind()

    # --- Backfill de usuario_uuid: só linhas pré-0015 (usuario_uuid ainda NULL) ---
    conexao.execute(
        sa.text(
            """
            UPDATE sessoes_trabalho s
            SET    usuario_uuid = u.id
            FROM   usuarios u
            WHERE  s.usuario_uuid IS NULL
              AND  s.usuario_id = u.codigo_interno
              AND  u.empresa_id = s.empresa_id
            """
        )
    )

    # --- Backfill de departamento_uuid: mesma lógica ---
    conexao.execute(
        sa.text(
            """
            UPDATE sessoes_trabalho s
            SET    departamento_uuid = d.id
            FROM   departamentos d
            WHERE  s.departamento_uuid IS NULL
              AND  s.departamento_id = d.codigo_interno
              AND  d.empresa_id = s.empresa_id
            """
        )
    )

    # --- FK: nullable de propósito. Linha sem correspondência comprovável fica NULL — não é
    # erro, é o resultado correto de "não fabricar vínculo" (ver docstring acima).
    op.create_foreign_key(
        'fk_sessoes_trabalho_usuario_uuid',
        'sessoes_trabalho',
        'usuarios',
        ['usuario_uuid'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_sessoes_trabalho_departamento_uuid',
        'sessoes_trabalho',
        'departamentos',
        ['departamento_uuid'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # Remove SOMENTE as FKs. Os valores de usuario_uuid/departamento_uuid são PRESERVADOS de
    # propósito — o dado é reconstituível (o texto legado segue intacto como fonte), e
    # apagá-lo obrigaria a refazer o backfill sem necessidade.
    op.drop_constraint('fk_sessoes_trabalho_departamento_uuid', 'sessoes_trabalho', type_='foreignkey')
    op.drop_constraint('fk_sessoes_trabalho_usuario_uuid', 'sessoes_trabalho', type_='foreignkey')
