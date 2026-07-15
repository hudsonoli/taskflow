"""cria sessoes trabalho

Revision ID: 20260712_1a5
Revises: 20260711_1a2
Create Date: 2026-07-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260712_1a5"
down_revision: Union[str, Sequence[str], None] = "20260711_1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessoes_trabalho",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=128), nullable=False),
        sa.Column("agencia_id", sa.String(length=128), nullable=True),
        sa.Column("demanda_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_etapa_id", sa.String(length=128), nullable=True),
        sa.Column("usuario_id", sa.String(length=128), nullable=True),
        sa.Column("departamento_id", sa.String(length=128), nullable=True),
        sa.Column("evento_inicio_id", sa.String(length=36), nullable=False),
        sa.Column("evento_fim_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duracao_segundos", sa.Integer(), nullable=True),
        sa.Column("motivo_encerramento", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('ativa', 'encerrada', 'cancelada')",
            name="ck_sessoes_trabalho_status",
        ),
        sa.CheckConstraint(
            "duracao_segundos IS NULL OR duracao_segundos >= 0",
            name="ck_sessoes_trabalho_duracao_nao_negativa",
        ),
        sa.CheckConstraint(
            "status != 'ativa' OR (fim_em IS NULL AND evento_fim_id IS NULL AND duracao_segundos IS NULL)",
            name="ck_sessoes_trabalho_ativa_sem_fim",
        ),
        sa.CheckConstraint(
            "status != 'encerrada' OR (fim_em IS NOT NULL AND evento_fim_id IS NOT NULL AND duracao_segundos IS NOT NULL)",
            name="ck_sessoes_trabalho_encerrada_com_fim",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessoes_trabalho_empresa_id", "sessoes_trabalho", ["empresa_id"])
    op.create_index("ix_sessoes_trabalho_demanda_id", "sessoes_trabalho", ["demanda_id"])
    op.create_index("ix_sessoes_trabalho_usuario_id", "sessoes_trabalho", ["usuario_id"])
    op.create_index("ix_sessoes_trabalho_departamento_id", "sessoes_trabalho", ["departamento_id"])
    op.create_index("ix_sessoes_trabalho_workflow_etapa_id", "sessoes_trabalho", ["workflow_etapa_id"])
    op.create_index("ix_sessoes_trabalho_status", "sessoes_trabalho", ["status"])
    op.create_index("ix_sessoes_trabalho_inicio_em", "sessoes_trabalho", ["inicio_em"])
    op.create_index("ix_sessoes_trabalho_evento_inicio_id", "sessoes_trabalho", ["evento_inicio_id"], unique=True)
    op.create_index("ix_sessoes_trabalho_evento_fim_id", "sessoes_trabalho", ["evento_fim_id"])
    op.create_index(
        "uq_sessoes_trabalho_ativa_demanda_usuario",
        "sessoes_trabalho",
        ["demanda_id", "usuario_id"],
        unique=True,
        postgresql_where=sa.text("usuario_id IS NOT NULL AND status = 'ativa'"),
    )
    op.create_index(
        "uq_sessoes_trabalho_ativa_demanda_departamento",
        "sessoes_trabalho",
        ["demanda_id", "departamento_id"],
        unique=True,
        postgresql_where=sa.text("usuario_id IS NULL AND departamento_id IS NOT NULL AND status = 'ativa'"),
    )


def downgrade() -> None:
    op.drop_index("uq_sessoes_trabalho_ativa_demanda_departamento", table_name="sessoes_trabalho")
    op.drop_index("uq_sessoes_trabalho_ativa_demanda_usuario", table_name="sessoes_trabalho")
    op.drop_index("ix_sessoes_trabalho_evento_fim_id", table_name="sessoes_trabalho")
    op.drop_index("ix_sessoes_trabalho_evento_inicio_id", table_name="sessoes_trabalho")
    op.drop_index("ix_sessoes_trabalho_inicio_em", table_name="sessoes_trabalho")
    op.drop_index("ix_sessoes_trabalho_status", table_name="sessoes_trabalho")
    op.drop_index("ix_sessoes_trabalho_workflow_etapa_id", table_name="sessoes_trabalho")
    op.drop_index("ix_sessoes_trabalho_departamento_id", table_name="sessoes_trabalho")
    op.drop_index("ix_sessoes_trabalho_usuario_id", table_name="sessoes_trabalho")
    op.drop_index("ix_sessoes_trabalho_demanda_id", table_name="sessoes_trabalho")
    op.drop_index("ix_sessoes_trabalho_empresa_id", table_name="sessoes_trabalho")
    op.drop_table("sessoes_trabalho")
