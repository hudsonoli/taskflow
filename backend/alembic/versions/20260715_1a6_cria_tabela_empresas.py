"""cria tabela empresas

Revision ID: 20260715_1a6
Revises: 20260712_1a5
Create Date: 2026-07-15 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260715_1a6"
down_revision: Union[str, Sequence[str], None] = "20260712_1a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "empresas",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("documento", sa.String(length=32), nullable=True),
        sa.Column("codigo_interno", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inativado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inativado_por_usuario_id", sa.String(length=128), nullable=True),
        sa.Column("motivo_inativacao", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "status IN ('ativa', 'inativa', 'arquivada')",
            name="ck_empresas_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo_interno", name="uq_empresas_codigo_interno"),
        sa.UniqueConstraint("documento", name="uq_empresas_documento"),
    )
    op.create_index("ix_empresas_status", "empresas", ["status"])
    op.create_index("ix_empresas_created_at", "empresas", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_empresas_created_at", table_name="empresas")
    op.drop_index("ix_empresas_status", table_name="empresas")
    op.drop_table("empresas")
