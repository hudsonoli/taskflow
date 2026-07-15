"""cria usuario credenciais

Revision ID: 20260715_1a9
Revises: 20260715_1a8
Create Date: 2026-07-15 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260715_1a9"
down_revision: Union[str, Sequence[str], None] = "20260715_1a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuario_credenciais",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("senha_definida_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("senha_alterada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tentativas_falhas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("bloqueado_ate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", name="uq_usuario_credenciais_usuario_id"),
    )
    op.create_index("ix_usuario_credenciais_usuario_id", "usuario_credenciais", ["usuario_id"])
    op.create_index("ix_usuario_credenciais_created_at", "usuario_credenciais", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_usuario_credenciais_created_at", table_name="usuario_credenciais")
    op.drop_index("ix_usuario_credenciais_usuario_id", table_name="usuario_credenciais")
    op.drop_table("usuario_credenciais")
