"""sessoes_trabalho.empresa_id ganha FK real

`Cliente.empresa_id` e `Demanda.empresa_id` já são `ForeignKey("empresas.id")`.
`SessaoTrabalho.empresa_id` era `varchar(128)` sem FK — mesmo defeito estrutural, tratado à
parte porque não precisa do ciclo completo de expand/contract: a correção de segurança que
passou a exigir `empresaId` vindo do token (`_empresa_do_token`, em
`app/api/routes/sessoes_trabalho.py`) já faz **toda sessão nova nascer com o UUID real**. Não
há um "novo nome" de coluna para migrar — só falta a constraint.

## Fail-fast, não reparadora

Esta migration **nunca apaga nem repara**. Se existir qualquer `sessoes_trabalho.empresa_id`
sem `empresas.id` correspondente, ela **aborta** e informa quantidade e ids — saneamento é
decisão de quem opera o banco, tomada fora deste arquivo, antes de rodar de novo.

Independente de `0015`/`0016`/`0018` — pode rodar antes, depois ou em paralelo com elas.

Revision ID: c2a5f8d34e91
Revises: b8e4d06c1f73
Create Date: 2026-08-10 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2a5f8d34e91'
down_revision: Union[str, None] = 'b8e4d06c1f73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conexao = op.get_bind()

    violacoes = conexao.execute(
        sa.text(
            """
            SELECT s.id FROM sessoes_trabalho s
            WHERE NOT EXISTS (SELECT 1 FROM empresas e WHERE e.id = s.empresa_id)
            """
        )
    ).fetchall()

    if violacoes:
        ids = ", ".join(str(linha.id) for linha in violacoes)
        raise RuntimeError(
            f"FK de sessoes_trabalho.empresa_id ABORTADA — {len(violacoes)} sessão(ões) com "
            f"empresa_id sem correspondência em empresas.id: {ids}. Saneie manualmente "
            "(remover ou corrigir cada linha) e rode a migration novamente; ela nunca "
            "apaga nem repara dado sozinha."
        )

    op.alter_column(
        'sessoes_trabalho',
        'empresa_id',
        type_=sa.String(length=36),
        existing_type=sa.String(length=128),
        existing_nullable=False,
    )
    op.create_foreign_key(
        'fk_sessoes_trabalho_empresa_id',
        'sessoes_trabalho',
        'empresas',
        ['empresa_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_sessoes_trabalho_empresa_id', 'sessoes_trabalho', type_='foreignkey')
    op.alter_column(
        'sessoes_trabalho',
        'empresa_id',
        type_=sa.String(length=128),
        existing_type=sa.String(length=36),
        existing_nullable=False,
    )
