"""usuario.departamento_id: contract final (D3-B)

Terceiro e último passo do expand/contract. Depois desta migration a tabela `usuarios`
tem UMA única representação de Departamento:

    departamento_id  varchar(36)  NULL  FK -> departamentos.id  ON DELETE SET NULL
    ix_usuarios_departamento_id
    fk_usuarios_departamento_id

A coluna textual legada (`departamento_id varchar(64)`, que guardava o NOME em texto
livre) deixa de existir.

## Por que a ordem é esta

`ALTER TABLE ... RENAME COLUMN` no PostgreSQL **não** renomeia a constraint de chave
estrangeira nem o índice que dependem da coluna — os dois continuariam com o nome antigo
(`fk_usuarios_departamento_uuid`, `ix_usuarios_departamento_uuid`), apontando para uma
coluna que agora se chama outra coisa. Funciona, mas mente. Por isso os três objetos são
tratados explicitamente:

1. guardas (abaixo);
2. DROP da coluna textual legada — precisa vir ANTES do rename, senão o nome colide;
3. RENAME da coluna `departamento_uuid` -> `departamento_id`;
4. RENAME da constraint -> `fk_usuarios_departamento_id`;
5. RENAME do índice -> `ix_usuarios_departamento_id`.

O `ON DELETE SET NULL` e o `nullable` sobrevivem ao rename (renomear não recria a
constraint), e isso é conferido depois da migration.

## Guardas — estruturais, não de dataset

As guardas abaixo abortam a migration ANTES de qualquer DROP. São todas **estruturais**:
valem em qualquer banco, inclusive vazio (a suíte roda `alembic upgrade head` contra um
banco sem usuários, e ali toda contagem de violação dá 0 — no-op válido).

    G1/G5  UUID órfão: departamento_uuid não nulo sem Departamento correspondente;
    G2     cross-tenant: usuario.empresa_id <> departamento.empresa_id;
    G3/G10 divergência: texto legado e UUID apontando para Departamentos diferentes;
    G4     texto legado não vazio sem departamento_uuid (backfill incompleto).

As conferências de **dataset** deste ambiente (40 usuários originais presentes, 38 vínculos
resolvidos, 2 NULL originais, usuário de QA arquivado adicional) NÃO entram aqui de
propósito: números fixos de um banco de desenvolvimento fariam a migration falhar em
qualquer outro ambiente, inclusive no de teste. Elas são executadas como reconciliação
antes e depois do upgrade, fora da migration.

Revision ID: 3c1a7be59d24
Revises: f48a7cc97e56
Create Date: 2026-08-07 21:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c1a7be59d24'
down_revision: Union[str, None] = 'f48a7cc97e56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mesmo mapa de acentos da migration D2 (0008) — mantido aqui para a migration ser
# autocontida e auditável sem depender de código da aplicação.
ACENTUADOS = 'áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ'
SEM_ACENTO = 'aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN'


def _norm(coluna: str) -> str:
    return f"lower(translate(btrim({coluna}), '{ACENTUADOS}', '{SEM_ACENTO}'))"


def _contar(conexao, sql: str) -> int:
    return conexao.execute(sa.text(sql)).scalar_one()


def upgrade() -> None:
    conexao = op.get_bind()

    # ---------------------------------------------------------------- guardas
    orfaos = _contar(
        conexao,
        """
        SELECT count(*) FROM usuarios u
        WHERE u.departamento_uuid IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM departamentos d WHERE d.id = u.departamento_uuid)
        """,
    )

    cross_tenant = _contar(
        conexao,
        """
        SELECT count(*) FROM usuarios u
        JOIN departamentos d ON d.id = u.departamento_uuid
        WHERE d.empresa_id <> u.empresa_id
        """,
    )

    divergentes = _contar(
        conexao,
        f"""
        SELECT count(*) FROM usuarios u
        JOIN departamentos d ON d.id = u.departamento_uuid
        WHERE u.departamento_id IS NOT NULL
          AND btrim(u.departamento_id) <> ''
          AND {_norm('u.departamento_id')} <> {_norm('d.nome')}
        """,
    )

    texto_sem_uuid = _contar(
        conexao,
        """
        SELECT count(*) FROM usuarios
        WHERE departamento_id IS NOT NULL
          AND btrim(departamento_id) <> ''
          AND departamento_uuid IS NULL
        """,
    )

    violacoes = {
        "UUID órfão (aponta para Departamento inexistente)": orfaos,
        "vínculo cross-tenant (empresa do usuário <> empresa do departamento)": cross_tenant,
        "texto legado e UUID apontando para Departamentos diferentes": divergentes,
        "texto legado não vazio sem departamento_uuid": texto_sem_uuid,
    }
    problemas = {motivo: qtd for motivo, qtd in violacoes.items() if qtd}

    if problemas:
        detalhe = "; ".join(f"{motivo}: {qtd}" for motivo, qtd in problemas.items())
        raise RuntimeError(
            "Contract de usuarios.departamento_id ABORTADO — nenhuma coluna foi removida. "
            f"Invariantes violadas: {detalhe}. Corrija os dados e rode novamente; esta "
            "migration nunca repara nada silenciosamente."
        )

    # ---------------------------------------------------------------- contract
    # 1) A coluna textual legada some. É o passo destrutivo: o dado equivalente já vive
    #    em departamento_uuid (garantido pelas guardas acima).
    op.drop_column('usuarios', 'departamento_id')

    # 2) A coluna nova assume o nome definitivo.
    op.alter_column('usuarios', 'departamento_uuid', new_column_name='departamento_id')

    # 3) e 4) RENAME não propaga para constraint/índice — feitos à mão.
    op.execute(
        'ALTER TABLE usuarios RENAME CONSTRAINT fk_usuarios_departamento_uuid '
        'TO fk_usuarios_departamento_id'
    )
    op.execute('ALTER INDEX ix_usuarios_departamento_uuid RENAME TO ix_usuarios_departamento_id')


def downgrade() -> None:
    """Reconstrói o estado da D2: `departamento_uuid` + `departamento_id` textual.

    Passos, na ordem inversa do upgrade:

    1. `departamento_id` (agora UUID) volta a se chamar `departamento_uuid`;
    2. constraint e índice voltam aos nomes antigos;
    3. `departamento_id varchar(64)` é recriada, nullable;
    4. o texto é repopulado a partir do NOME ATUAL do Departamento apontado pelo UUID;
       quem está sem UUID permanece com texto NULL.

    LIMITAÇÃO CONHECIDA E ACEITA: o passo 4 reconstrói o nome **atual**. Se um Departamento
    tiver sido renomeado depois do contract, o texto restaurado será o nome novo, não o
    histórico. O dado autoritativo passou a ser o UUID, então nada de valor se perde — mas
    a restauração fiel byte a byte é o `pg_dump` tirado imediatamente antes da D3-B, não
    este downgrade.
    """
    op.execute('ALTER INDEX ix_usuarios_departamento_id RENAME TO ix_usuarios_departamento_uuid')
    op.execute(
        'ALTER TABLE usuarios RENAME CONSTRAINT fk_usuarios_departamento_id '
        'TO fk_usuarios_departamento_uuid'
    )
    op.alter_column('usuarios', 'departamento_id', new_column_name='departamento_uuid')

    op.add_column('usuarios', sa.Column('departamento_id', sa.String(length=64), nullable=True))
    op.execute(
        """
        UPDATE usuarios u
        SET    departamento_id = d.nome
        FROM   departamentos d
        WHERE  d.id = u.departamento_uuid
        """
    )
