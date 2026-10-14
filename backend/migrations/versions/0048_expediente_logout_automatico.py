"""Expediente — Fase 2: logout automático (horário próprio e independente).

Adiciona SÓ a configuração do logout automático à regra de expediente:
- `logout_automatico_ativo BOOLEAN NOT NULL DEFAULT FALSE`
- `logout_horario TIME NULL` (horário local da empresa, no fuso `regra_expediente.timezone`)
- CHECK: logout ativo exige horário.

Tudo nasce DESLIGADO: este deploy NÃO desloga ninguém. As flags `bloquear_fora_expediente` e `pausar_no_fim_periodo` NÃO são alteradas (seguem como estão). Nenhum dado
existente é reescrito; o logout automático é independente do fim do último período e da pausa de Demandas (Fase 3).

Downgrade: remove o CHECK e as duas colunas (a configuração do logout se perde; nada mais é tocado).
"""
import sqlalchemy as sa
from alembic import op

revision = "b4d7f2a96c31"
down_revision = "a3c8e5f17d24"
branch_labels = None
depends_on = None

CHECK = "ck_regra_expediente_logout_exige_horario"


def upgrade() -> None:
    op.add_column("regra_expediente", sa.Column("logout_automatico_ativo", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("regra_expediente", sa.Column("logout_horario", sa.Time(), nullable=True))
    op.create_check_constraint(CHECK, "regra_expediente", "NOT logout_automatico_ativo OR logout_horario IS NOT NULL")


def downgrade() -> None:
    op.drop_constraint(CHECK, "regra_expediente", type_="check")
    op.drop_column("regra_expediente", "logout_horario")
    op.drop_column("regra_expediente", "logout_automatico_ativo")
