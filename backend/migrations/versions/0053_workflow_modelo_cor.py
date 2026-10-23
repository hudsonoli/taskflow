"""P1_WORKFLOW_COLOR — cor (identidade visual) do modelo de workflow.

ADITIVA: uma coluna nullable `workflow_modelos.cor` (VARCHAR(7)) + CHECK `cor IS NULL OR cor ~ '^#[0-9A-F]{6}$'` (HEX canônico em maiúsculas). Sem backfill: os modelos existentes ficam com `cor = NULL`
(sem cor personalizada — a interface usa o neutro; nenhuma cor é escolhida pelo banco). Não toca `demanda_workflow_etapas` (a cor não faz parte do snapshot da Demanda) nem nenhuma outra tabela.

Downgrade: remove a constraint e a coluna (descarta as cores cadastradas depois do upgrade).
"""
import sqlalchemy as sa
from alembic import op

revision = "a9d2c6e84b17"
down_revision = "f1b7c3a95d28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_modelos", sa.Column("cor", sa.String(7), nullable=True))
    op.create_check_constraint("ck_workflow_modelos_cor", "workflow_modelos", "cor IS NULL OR cor ~ '^#[0-9A-F]{6}$'")


def downgrade() -> None:
    op.drop_constraint("ck_workflow_modelos_cor", "workflow_modelos", type_="check")
    op.drop_column("workflow_modelos", "cor")
