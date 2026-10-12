"""Esforço opcional por etapa; legado permanece NULL, sem conversão de prazo."""
from alembic import op
import sqlalchemy as sa

revision = "d9f3b58e2a71"
down_revision = "c8e2a47d1f93"
branch_labels = None
depends_on = None

TABELAS = ("workflow_modelo_etapas", "demanda_workflow_etapas")


def upgrade() -> None:
    for tabela in TABELAS:
        op.add_column(tabela, sa.Column("esforco_estimado_minutos", sa.Integer(), nullable=True))
        op.create_check_constraint(
            f"ck_{tabela}_esforco_nao_negativo", tabela,
            "esforco_estimado_minutos IS NULL OR esforco_estimado_minutos >= 0",
        )


def downgrade() -> None:
    for tabela in reversed(TABELAS):
        op.drop_constraint(f"ck_{tabela}_esforco_nao_negativo", tabela, type_="check")
        op.drop_column(tabela, "esforco_estimado_minutos")
