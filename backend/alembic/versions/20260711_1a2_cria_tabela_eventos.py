"""cria tabela eventos

Revision ID: 20260711_1a2
Revises:
Create Date: 2026-07-11 18:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260711_1a2"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eventos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=128), nullable=False),
        sa.Column("agencia_id", sa.String(length=128), nullable=True),
        sa.Column("tipo", sa.String(length=128), nullable=False),
        sa.Column("entidade_tipo", sa.String(length=128), nullable=False),
        sa.Column("entidade_id", sa.String(length=128), nullable=False),
        sa.Column("usuario_id", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=36), nullable=True),
        sa.Column("causation_id", sa.String(length=36), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eventos_empresa_id", "eventos", ["empresa_id"])
    op.create_index("ix_eventos_entidade", "eventos", ["entidade_tipo", "entidade_id"])
    op.create_index("ix_eventos_tipo", "eventos", ["tipo"])
    op.create_index("ix_eventos_occurred_at", "eventos", ["occurred_at"])
    op.create_index("ix_eventos_correlation_id", "eventos", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_eventos_correlation_id", table_name="eventos")
    op.drop_index("ix_eventos_occurred_at", table_name="eventos")
    op.drop_index("ix_eventos_tipo", table_name="eventos")
    op.drop_index("ix_eventos_entidade", table_name="eventos")
    op.drop_index("ix_eventos_empresa_id", table_name="eventos")
    op.drop_table("eventos")
