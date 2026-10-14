"""Expediente — Fase 3: pausa automática no fim dos períodos (armadura da flag).

Adiciona SÓ `regra_expediente.pausa_automatica_ativada_em TIMESTAMPTZ NULL`: o instante em que a pausa automática foi "armada" (flag ligada, controle-mestre religado ou
calendário editado enquanto ela está ligada). Um corte (fim de período) só é elegível se for POSTERIOR a esse instante — ligar a configuração às 12:15 NUNCA pausa
retroativamente como se ela já valesse às 12:00. NULL = nunca armada (não pausa nada).

Nasce NULL para toda regra existente: o deploy não pausa nada e não altera nenhuma flag (`pausar_no_fim_periodo` continua como está — em produção, false). Sem backfill.

Downgrade: remove a coluna (o instante de armadura se perde; a flag em si permanece).
"""
import sqlalchemy as sa
from alembic import op

revision = "c6e1a38d5b92"
down_revision = "b4d7f2a96c31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("regra_expediente", sa.Column("pausa_automatica_ativada_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("regra_expediente", "pausa_automatica_ativada_em")
