"""Uma sessão de trabalho ATIVA por pessoa: índice único parcial (empresa_id, usuario_id).

Só protege contra a corrida de duas aberturas simultâneas do MESMO usuário; a regra de produto (409 `SESSAO_ATIVA_EXISTENTE`) é aplicada antes, no service.
Sessões puramente departamentais (`usuario_id IS NULL`) ficam fora do índice. Sem FK nova, sem backfill, sem alteração de dados.
"""
from alembic import op
import sqlalchemy as sa

revision = "f2c6a9d41b87"
down_revision = "d9f3b58e2a71"
branch_labels = None
depends_on = None

INDICE = "uq_sessoes_trabalho_ativa_empresa_usuario"
PREDICADO = "usuario_id IS NOT NULL AND status = 'ativa'"


def upgrade() -> None:
    # Guarda: o legado precisa ser compatível. Nada é corrigido automaticamente — se houver conflito, a migration para ANTES de criar o índice,
    # informando só a contagem (sem ids nem nomes).
    conflitos = op.get_bind().execute(
        sa.text(
            "SELECT count(*) FROM (SELECT 1 FROM sessoes_trabalho WHERE " + PREDICADO
            + " GROUP BY empresa_id, usuario_id HAVING count(*) > 1) x"
        )
    ).scalar_one()
    if conflitos:
        raise RuntimeError(
            f"{conflitos} usuário(s) com mais de uma sessão de trabalho ativa: encerre as sessões duplicadas antes de aplicar esta migration"
        )
    op.create_index(
        INDICE, "sessoes_trabalho", ["empresa_id", "usuario_id"], unique=True, postgresql_where=sa.text(PREDICADO)
    )


def downgrade() -> None:
    op.drop_index(INDICE, table_name="sessoes_trabalho")
