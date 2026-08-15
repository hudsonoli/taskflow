"""sessoes_trabalho.usuario_id / departamento_id: contract final (D3)

Quarto e último passo do expand/contract. Depois desta migration `sessoes_trabalho` tem UMA
única representação de usuário e de departamento:

    usuario_id       varchar(36)  NULL  FK -> usuarios.id       ON DELETE SET NULL
    departamento_id  varchar(36)  NULL  FK -> departamentos.id  ON DELETE SET NULL

As colunas textuais legadas (`usuario_id`/`departamento_id` originais, que guardavam ids do
mock — `"user-1"`) deixam de existir. `usuario_uuid`/`departamento_uuid` assumem os nomes
finais.

## Por que a ordem é esta

`ALTER TABLE ... RENAME COLUMN` no PostgreSQL **não** renomeia a constraint de FK nem o
índice que dependem da coluna — os dois continuariam com o nome antigo
(`fk_sessoes_trabalho_usuario_uuid`, `ix_sessoes_trabalho_usuario_uuid`), apontando para uma
coluna que agora se chama outra coisa. Funciona, mas mente. Por isso os três objetos são
tratados explicitamente, na mesma ordem usada em `0009` (equivalente para Usuário/Departamento):

1. guardas (abaixo) — abortam ANTES de qualquer DROP;
2. DROP das colunas textuais legadas — precisa vir ANTES do rename, senão o nome colide;
3. RENAME `usuario_uuid` -> `usuario_id` / `departamento_uuid` -> `departamento_id`;
4. RENAME das constraints de FK -> nomes finais;
5. RENAME dos índices -> nomes finais.

## Guardas — estruturais, não de dataset

Todas abaixo valem em qualquer banco, inclusive vazio (a suíte roda `alembic upgrade head`
contra um banco sem sessões, e ali toda contagem de violação dá 0 — no-op válido).

    G1  UUID órfão: usuario_uuid/departamento_uuid não nulo sem linha correspondente
        (defesa em profundidade — a FK criada em 0016 já torna isto estruturalmente
        impossível; a guarda aqui é redundante de propósito, não confiança cega na FK);
    G2  cross-tenant: usuario.empresa_id/departamento.empresa_id <> sessoes_trabalho.empresa_id
        (a FK garante EXISTÊNCIA, não que o registro pertence à mesma empresa);
    G3  divergência texto×UUID — aceita DOIS formatos coerentes, produzidos pelos dois
        caminhos legítimos que uma linha pode ter percorrido até aqui:
          (A) usuario_id (texto) == usuario_uuid (como string)
              -> sessão nascida na janela de expansão (0015->0018), escrita dupla
                 (ver SessaoTrabalhoService.open_session);
          (B) usuario_id (texto) == codigo_interno do usuário apontado por usuario_uuid
              -> sessão anterior a 0015, resolvida pelo backfill de 0016.
        Qualquer terceiro valor é divergência real e aborta;
    G4  texto legado não vazio sem UUID resolvido — linha herdada de antes de 0015 que o
        backfill de 0016 não conseguiu resolver (sem correspondência comprovável). Abortante:
        perder esse texto no DROP sem que alguém tenha decidido o que fazer com ele seria
        informação jogada fora em silêncio.

Nenhuma guarda repara ou apaga dado. Uma violação aborta a migration inteira, sem alterar
nada — saneamento é decisão de quem opera o banco, tomada fora deste arquivo.

Revision ID: d6b1a9f04c58
Revises: c2a5f8d34e91
Create Date: 2026-08-14 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6b1a9f04c58'
down_revision: Union[str, None] = 'c2a5f8d34e91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _contar(conexao, sql: str) -> int:
    return conexao.execute(sa.text(sql)).scalar_one()


def upgrade() -> None:
    conexao = op.get_bind()

    # ---------------------------------------------------------------- guardas: usuario
    orfaos_usuario = _contar(
        conexao,
        """
        SELECT count(*) FROM sessoes_trabalho s
        WHERE s.usuario_uuid IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM usuarios u WHERE u.id = s.usuario_uuid)
        """,
    )
    cross_tenant_usuario = _contar(
        conexao,
        """
        SELECT count(*) FROM sessoes_trabalho s
        JOIN usuarios u ON u.id = s.usuario_uuid
        WHERE u.empresa_id <> s.empresa_id
        """,
    )
    divergentes_usuario = _contar(
        conexao,
        """
        SELECT count(*) FROM sessoes_trabalho s
        JOIN usuarios u ON u.id = s.usuario_uuid
        WHERE s.usuario_id IS NOT NULL AND btrim(s.usuario_id) <> ''
          AND s.usuario_id <> s.usuario_uuid
          AND s.usuario_id <> u.codigo_interno
        """,
    )
    texto_sem_uuid_usuario = _contar(
        conexao,
        """
        SELECT count(*) FROM sessoes_trabalho
        WHERE usuario_id IS NOT NULL AND btrim(usuario_id) <> ''
          AND usuario_uuid IS NULL
        """,
    )

    # ---------------------------------------------------------------- guardas: departamento
    orfaos_departamento = _contar(
        conexao,
        """
        SELECT count(*) FROM sessoes_trabalho s
        WHERE s.departamento_uuid IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM departamentos d WHERE d.id = s.departamento_uuid)
        """,
    )
    cross_tenant_departamento = _contar(
        conexao,
        """
        SELECT count(*) FROM sessoes_trabalho s
        JOIN departamentos d ON d.id = s.departamento_uuid
        WHERE d.empresa_id <> s.empresa_id
        """,
    )
    divergentes_departamento = _contar(
        conexao,
        """
        SELECT count(*) FROM sessoes_trabalho s
        JOIN departamentos d ON d.id = s.departamento_uuid
        WHERE s.departamento_id IS NOT NULL AND btrim(s.departamento_id) <> ''
          AND s.departamento_id <> s.departamento_uuid
          AND s.departamento_id <> d.codigo_interno
        """,
    )
    texto_sem_uuid_departamento = _contar(
        conexao,
        """
        SELECT count(*) FROM sessoes_trabalho
        WHERE departamento_id IS NOT NULL AND btrim(departamento_id) <> ''
          AND departamento_uuid IS NULL
        """,
    )

    violacoes = {
        "usuario_uuid órfão (aponta para Usuário inexistente)": orfaos_usuario,
        "vínculo de usuário cross-tenant": cross_tenant_usuario,
        "usuario_id (texto) diverge de usuario_uuid e do codigo_interno apontado": divergentes_usuario,
        "usuario_id (texto) não vazio sem usuario_uuid resolvido": texto_sem_uuid_usuario,
        "departamento_uuid órfão (aponta para Departamento inexistente)": orfaos_departamento,
        "vínculo de departamento cross-tenant": cross_tenant_departamento,
        "departamento_id (texto) diverge de departamento_uuid e do codigo_interno apontado": divergentes_departamento,
        "departamento_id (texto) não vazio sem departamento_uuid resolvido": texto_sem_uuid_departamento,
    }
    problemas = {motivo: qtd for motivo, qtd in violacoes.items() if qtd}

    if problemas:
        detalhe = "; ".join(f"{motivo}: {qtd}" for motivo, qtd in problemas.items())
        raise RuntimeError(
            "Contract de sessoes_trabalho ABORTADO — nenhuma coluna foi removida. "
            f"Invariantes violadas: {detalhe}. Corrija os dados e rode novamente; esta "
            "migration nunca repara nem apaga nada silenciosamente."
        )

    # ---------------------------------------------------------------- contract: usuario
    op.drop_column('sessoes_trabalho', 'usuario_id')
    op.alter_column('sessoes_trabalho', 'usuario_uuid', new_column_name='usuario_id')
    op.execute(
        'ALTER TABLE sessoes_trabalho RENAME CONSTRAINT fk_sessoes_trabalho_usuario_uuid '
        'TO fk_sessoes_trabalho_usuario_id'
    )
    op.execute('ALTER INDEX ix_sessoes_trabalho_usuario_uuid RENAME TO ix_sessoes_trabalho_usuario_id')

    # ---------------------------------------------------------------- contract: departamento
    op.drop_column('sessoes_trabalho', 'departamento_id')
    op.alter_column('sessoes_trabalho', 'departamento_uuid', new_column_name='departamento_id')
    op.execute(
        'ALTER TABLE sessoes_trabalho RENAME CONSTRAINT fk_sessoes_trabalho_departamento_uuid '
        'TO fk_sessoes_trabalho_departamento_id'
    )
    op.execute(
        'ALTER INDEX ix_sessoes_trabalho_departamento_uuid RENAME TO ix_sessoes_trabalho_departamento_id'
    )

    # ---------------------------------------------------------------- índices únicos
    # `uq_sessoes_trabalho_ativa_demanda_usuario`/`..._departamento` (criados na migration
    # 0001) NÃO sobrevivem: eles indexavam a coluna textual ORIGINAL `usuario_id`/
    # `departamento_id`, que o DROP COLUMN acima removeu — Postgres derruba em cascata
    # qualquer índice que dependa da coluna apagada. (A suposição inicial desta migration —
    # de que o RENAME preservaria os índices — estava errada: quem foi renomeado é a coluna
    # NOVA, `usuario_uuid`; os índices antigos apontavam para a coluna VELHA, que foi dropada,
    # não renomeada. `alembic check` pegou a divergência.) Recriados aqui, sobre as colunas
    # finais, com a definição idêntica à do modelo.
    op.create_index(
        'uq_sessoes_trabalho_ativa_demanda_usuario',
        'sessoes_trabalho',
        ['demanda_id', 'usuario_id'],
        unique=True,
        postgresql_where=sa.text("usuario_id IS NOT NULL AND status = 'ativa'"),
    )
    op.create_index(
        'uq_sessoes_trabalho_ativa_demanda_departamento',
        'sessoes_trabalho',
        ['demanda_id', 'departamento_id'],
        unique=True,
        postgresql_where=sa.text("usuario_id IS NULL AND departamento_id IS NOT NULL AND status = 'ativa'"),
    )


def downgrade() -> None:
    """Reconstrói o estado da D2 (0017): usuario_uuid/departamento_uuid + colunas textuais.

    LIMITAÇÃO CONHECIDA E ACEITA: o texto reconstruído é o `codigo_interno` ATUAL de quem o
    UUID aponta — não byte a byte o texto legado original (que pode ter sido, por exemplo, o
    próprio UUID de uma sessão nascida durante a janela de expansão). O dado autoritativo
    passou a ser o UUID; a restauração fiel é o backup tirado antes do contract, não este
    downgrade.
    """
    # Os dois índices únicos parciais criados no upgrade() apontam para os nomes finais de
    # coluna — precisam sumir ANTES do rename reverso, senão ficariam presos a um nome que
    # está prestes a deixar de existir.
    op.drop_index('uq_sessoes_trabalho_ativa_demanda_departamento', table_name='sessoes_trabalho')
    op.drop_index('uq_sessoes_trabalho_ativa_demanda_usuario', table_name='sessoes_trabalho')

    op.execute(
        'ALTER INDEX ix_sessoes_trabalho_departamento_id RENAME TO ix_sessoes_trabalho_departamento_uuid'
    )
    op.execute(
        'ALTER TABLE sessoes_trabalho RENAME CONSTRAINT fk_sessoes_trabalho_departamento_id '
        'TO fk_sessoes_trabalho_departamento_uuid'
    )
    op.alter_column('sessoes_trabalho', 'departamento_id', new_column_name='departamento_uuid')
    op.add_column('sessoes_trabalho', sa.Column('departamento_id', sa.String(length=128), nullable=True))
    op.execute(
        """
        UPDATE sessoes_trabalho s
        SET    departamento_id = d.codigo_interno
        FROM   departamentos d
        WHERE  d.id = s.departamento_uuid
        """
    )

    op.execute('ALTER INDEX ix_sessoes_trabalho_usuario_id RENAME TO ix_sessoes_trabalho_usuario_uuid')
    op.execute(
        'ALTER TABLE sessoes_trabalho RENAME CONSTRAINT fk_sessoes_trabalho_usuario_id '
        'TO fk_sessoes_trabalho_usuario_uuid'
    )
    op.alter_column('sessoes_trabalho', 'usuario_id', new_column_name='usuario_uuid')
    op.add_column('sessoes_trabalho', sa.Column('usuario_id', sa.String(length=128), nullable=True))
    op.execute(
        """
        UPDATE sessoes_trabalho s
        SET    usuario_id = u.codigo_interno
        FROM   usuarios u
        WHERE  u.id = s.usuario_uuid
        """
    )

    # Restaura os dois índices na forma original de 0001–0017: sobre as colunas TEXTUAIS
    # recém-recriadas acima, não sobre as `_uuid`.
    op.create_index(
        'uq_sessoes_trabalho_ativa_demanda_usuario',
        'sessoes_trabalho',
        ['demanda_id', 'usuario_id'],
        unique=True,
        postgresql_where=sa.text("usuario_id IS NOT NULL AND status = 'ativa'"),
    )
    op.create_index(
        'uq_sessoes_trabalho_ativa_demanda_departamento',
        'sessoes_trabalho',
        ['demanda_id', 'departamento_id'],
        unique=True,
        postgresql_where=sa.text("usuario_id IS NULL AND departamento_id IS NOT NULL AND status = 'ativa'"),
    )
