"""11B.2B-A — base de planejamento: janela planejada por etapa + percentual de capacidade alocável da empresa.

ADITIVA. Sem tabela nova e sem backfill:
- `demanda_workflow_etapas.planejado_inicio DATE NULL` e `planejado_fim DATE NULL` — todas as etapas existentes ficam NULL/NULL ("não planejado"). CHECK: `fim` exige
  `inicio` e não pode ser anterior a ele (NULL/NULL, DATE/NULL e DATE/DATE>= são válidos; NULL/DATE e fim < início nunca são persistidos).
- `regra_expediente.percentual_capacidade_alocavel SMALLINT NOT NULL DEFAULT 100` com CHECK 1..100 — toda regra existente nasce com 100 (capacidade nominal inteira).

NÃO altera `workflow_modelo_etapas` (o template não recebe janela), `demandas` (prazo, data_inicio, data_fim_prevista), `sessoes_trabalho`, `demanda_status_intervalos`,
`eventos` nem nenhum horário/dia/fuso/flag do expediente. Nenhum dado existente é reescrito.

Downgrade: remove só as colunas e os CHECKs novos (depois de uso real, descarta as janelas e o percentual configurados).
"""
import sqlalchemy as sa
from alembic import op

revision = "e8a4c2d71f96"
down_revision = "d7f3b91e4a58"
branch_labels = None
depends_on = None

CK_JANELA = "ck_demanda_workflow_etapas_janela_planejada"
CK_PERCENTUAL = "ck_regra_expediente_percentual_capacidade_alocavel"


def upgrade() -> None:
    op.add_column("demanda_workflow_etapas", sa.Column("planejado_inicio", sa.Date(), nullable=True))
    op.add_column("demanda_workflow_etapas", sa.Column("planejado_fim", sa.Date(), nullable=True))
    op.create_check_constraint(
        CK_JANELA,
        "demanda_workflow_etapas",
        "planejado_fim IS NULL OR (planejado_inicio IS NOT NULL AND planejado_fim >= planejado_inicio)",
    )
    op.add_column(
        "regra_expediente",
        sa.Column("percentual_capacidade_alocavel", sa.SmallInteger(), nullable=False, server_default="100"),
    )
    op.create_check_constraint(
        CK_PERCENTUAL,
        "regra_expediente",
        "percentual_capacidade_alocavel >= 1 AND percentual_capacidade_alocavel <= 100",
    )


def downgrade() -> None:
    op.drop_constraint(CK_PERCENTUAL, "regra_expediente", type_="check")
    op.drop_column("regra_expediente", "percentual_capacidade_alocavel")
    op.drop_constraint(CK_JANELA, "demanda_workflow_etapas", type_="check")
    op.drop_column("demanda_workflow_etapas", "planejado_fim")
    op.drop_column("demanda_workflow_etapas", "planejado_inicio")
