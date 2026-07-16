"""cria usuario_cargos

Revision ID: 20260716_1a13
Revises: 20260715_1a12
Create Date: 2026-07-16 12:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260716_1a13"
down_revision: Union[str, None] = "20260715_1a12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuario_cargos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("cargo_id", sa.String(length=36), nullable=False),
        sa.Column("principal", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ativo", nullable=False),
        sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_encerramento", sa.String(length=500), nullable=True),
        sa.Column("criado_por_usuario_id", sa.String(length=36), nullable=True),
        sa.Column("encerrado_por_usuario_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('ativo', 'inativo')", name="ck_usuario_cargos_status"),
        sa.CheckConstraint(
            "fim_em IS NULL OR fim_em >= inicio_em",
            name="ck_usuario_cargos_fim_em_maior_inicio",
        ),
        sa.CheckConstraint(
            "(status = 'ativo' AND fim_em IS NULL) OR (status = 'inativo' AND fim_em IS NOT NULL)",
            name="ck_usuario_cargos_status_fim_em",
        ),
        sa.CheckConstraint(
            "principal = false OR status = 'ativo'",
            name="ck_usuario_cargos_principal_ativo",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["cargo_id"], ["cargos.id"]),
        sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encerrado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usuario_cargos_empresa_id", "usuario_cargos", ["empresa_id"], unique=False)
    op.create_index("ix_usuario_cargos_usuario_id", "usuario_cargos", ["usuario_id"], unique=False)
    op.create_index("ix_usuario_cargos_cargo_id", "usuario_cargos", ["cargo_id"], unique=False)
    op.create_index("ix_usuario_cargos_status", "usuario_cargos", ["status"], unique=False)
    op.create_index("ix_usuario_cargos_created_at", "usuario_cargos", ["created_at"], unique=False)
    op.create_index(
        "uq_usuario_cargos_ativo_usuario_cargo",
        "usuario_cargos",
        ["usuario_id", "cargo_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ativo'"),
        sqlite_where=sa.text("status = 'ativo'"),
    )
    op.create_index(
        "uq_usuario_cargos_principal_ativo_usuario",
        "usuario_cargos",
        ["usuario_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ativo' AND principal = true"),
        sqlite_where=sa.text("status = 'ativo' AND principal = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_usuario_cargos_principal_ativo_usuario", table_name="usuario_cargos")
    op.drop_index("uq_usuario_cargos_ativo_usuario_cargo", table_name="usuario_cargos")
    op.drop_index("ix_usuario_cargos_created_at", table_name="usuario_cargos")
    op.drop_index("ix_usuario_cargos_status", table_name="usuario_cargos")
    op.drop_index("ix_usuario_cargos_cargo_id", table_name="usuario_cargos")
    op.drop_index("ix_usuario_cargos_usuario_id", table_name="usuario_cargos")
    op.drop_index("ix_usuario_cargos_empresa_id", table_name="usuario_cargos")
    op.drop_table("usuario_cargos")
