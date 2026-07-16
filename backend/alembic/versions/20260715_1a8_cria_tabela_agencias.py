"""cria tabela agencias

Revision ID: 20260715_1a8
Revises: 20260715_1a7
Create Date: 2026-07-15 16:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260715_1a8"
down_revision: Union[str, Sequence[str], None] = "20260715_1a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agencias",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("codigo_interno", sa.String(length=64), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("sigla", sa.String(length=32), nullable=False),
        sa.Column("descricao", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inativado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_inativacao", sa.String(length=500), nullable=True),
        sa.Column("inativado_por_usuario_id", sa.String(length=36), nullable=True),
        sa.CheckConstraint(
            "status IN ('ativa', 'inativa', 'arquivada')",
            name="ck_agencias_status",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["inativado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "codigo_interno", name="uq_agencias_empresa_codigo_interno"),
        sa.UniqueConstraint("empresa_id", "nome", name="uq_agencias_empresa_nome"),
    )
    op.create_index("ix_agencias_empresa_id", "agencias", ["empresa_id"])
    op.create_index("ix_agencias_status", "agencias", ["status"])
    op.create_index("ix_agencias_created_at", "agencias", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agencias_created_at", table_name="agencias")
    op.drop_index("ix_agencias_status", table_name="agencias")
    op.drop_index("ix_agencias_empresa_id", table_name="agencias")
    op.drop_table("agencias")
