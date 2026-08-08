"""usuario.departamento_uuid: backfill validado + FK (D2)

Segundo passo do expand/contract. Resolve cada valor legado de `usuarios.departamento_id`
(texto com o NOME do departamento) para `departamentos.id` e cria a FK.

NÃO faz nesta etapa (é D3): DROP da coluna legada, rename, mudança de schema público,
alteração de frontend.

## Normalização

Sem extensão do Postgres. `lower(translate(btrim(x), <acentuados>, <sem acento>))` — mapa
explícito, previsível e autocontido. Foi conferido contra a mesma regra usada para gerar a
matriz de resolução em Python (NFKD + ascii + strip + lower): zero divergências nos 8
valores existentes.

## Escopo por empresa

A correspondência exige `d.empresa_id = u.empresa_id`. Um departamento com o mesmo nome em
OUTRA empresa nunca é usado — é isto que torna o vazamento cross-tenant impossível, não uma
regra de aplicação.

## Guardas (antes do UPDATE, na mesma transação)

1. valor legado não nulo com ZERO correspondências  -> aborta;
2. valor legado não nulo com MAIS DE UMA            -> aborta;
3. NULL/vazio permanece NULL (não é erro);
4. base vazia é no-op válido (é o caso do banco de teste).

Revision ID: f48a7cc97e56
Revises: 090ecbc4f863
Create Date: 2026-08-06 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f48a7cc97e56'
down_revision: Union[str, None] = '090ecbc4f863'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mapa de acentos usado na normalização — mantido aqui, junto de quem o usa, para a
# migration ser autocontida e auditável sem depender de código da aplicação.
ACENTUADOS = 'áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ'
SEM_ACENTO = 'aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN'


def _norm(coluna: str) -> str:
    return f"lower(translate(btrim({coluna}), '{ACENTUADOS}', '{SEM_ACENTO}'))"


def upgrade() -> None:
    conexao = op.get_bind()

    # --- Guarda 1 e 2: quantas correspondências cada valor legado tem, por empresa ---
    problemas = conexao.execute(
        sa.text(
            f"""
            SELECT u.empresa_id,
                   u.departamento_id                       AS valor_legado,
                   count(DISTINCT d.id)                    AS correspondencias,
                   count(*) OVER ()                        AS total_problemas
            FROM   usuarios u
            LEFT   JOIN departamentos d
                   ON  d.empresa_id = u.empresa_id
                   AND {_norm('d.nome')} = {_norm('u.departamento_id')}
            WHERE  u.departamento_id IS NOT NULL
              AND  btrim(u.departamento_id) <> ''
            GROUP  BY u.empresa_id, u.departamento_id
            HAVING count(DISTINCT d.id) <> 1
            """
        )
    ).fetchall()

    if problemas:
        detalhe = "; ".join(
            f"empresa={linha.empresa_id} valor={linha.valor_legado!r} correspondencias={linha.correspondencias}"
            for linha in problemas
        )
        raise RuntimeError(
            "Backfill de usuarios.departamento_uuid abortado — valores legados sem "
            f"correspondência única em departamentos (0 = não encontrado, >1 = ambíguo): {detalhe}"
        )

    # --- Backfill: escopado por empresa, só para valor legado não vazio ---
    conexao.execute(
        sa.text(
            f"""
            UPDATE usuarios u
            SET    departamento_uuid = d.id
            FROM   departamentos d
            WHERE  d.empresa_id = u.empresa_id
              AND  u.departamento_id IS NOT NULL
              AND  btrim(u.departamento_id) <> ''
              AND  {_norm('d.nome')} = {_norm('u.departamento_id')}
            """
        )
    )

    # --- Guarda 3 (pós-UPDATE): ninguém com valor legado pode ter ficado sem UUID ---
    nao_resolvidos = conexao.execute(
        sa.text(
            """
            SELECT count(*) FROM usuarios
            WHERE  departamento_id IS NOT NULL
              AND  btrim(departamento_id) <> ''
              AND  departamento_uuid IS NULL
            """
        )
    ).scalar_one()

    if nao_resolvidos:
        raise RuntimeError(
            f"Backfill abortado — {nao_resolvidos} usuário(s) com departamento textual "
            "permaneceram sem departamento_uuid."
        )

    # --- FK: nullable de propósito (usuário sem departamento é legítimo).
    # Sem cascade delete: apagar um departamento nunca pode apagar usuário. SET NULL
    # apenas desfaz o vínculo — e, na prática, Departamento é arquivado, nunca apagado.
    op.create_foreign_key(
        'fk_usuarios_departamento_uuid',
        'usuarios',
        'departamentos',
        ['departamento_uuid'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # Remove SOMENTE a FK. Os valores de departamento_uuid são PRESERVADOS de propósito:
    # o dado é reconstituível, mas apagá-lo obrigaria a refazer o backfill sem necessidade
    # — e `departamento_id` textual segue intacto como fonte original. Nada é perdido.
    op.drop_constraint('fk_usuarios_departamento_uuid', 'usuarios', type_='foreignkey')
