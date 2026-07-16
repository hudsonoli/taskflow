"""cria usuario_departamentos

Revision ID: 20260715_1a12
Revises: 20260715_1a11
Create Date: 2026-07-15 22:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260715_1a12"
down_revision: Union[str, None] = "20260715_1a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuario_departamentos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("departamento_id", sa.String(length=36), nullable=False),
        sa.Column("papel", sa.String(length=32), nullable=False),
        sa.Column("principal", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ativo", nullable=False),
        sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_encerramento", sa.String(length=500), nullable=True),
        sa.Column("criado_por_usuario_id", sa.String(length=36), nullable=True),
        sa.Column("encerrado_por_usuario_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("papel IN ('membro', 'gestor', 'head')", name="ck_usuario_departamentos_papel"),
        sa.CheckConstraint("status IN ('ativo', 'inativo')", name="ck_usuario_departamentos_status"),
        sa.CheckConstraint(
            "fim_em IS NULL OR fim_em >= inicio_em",
            name="ck_usuario_departamentos_fim_em_maior_inicio",
        ),
        sa.CheckConstraint(
            "(status = 'ativo' AND fim_em IS NULL) OR (status = 'inativo' AND fim_em IS NOT NULL)",
            name="ck_usuario_departamentos_status_fim_em",
        ),
        sa.CheckConstraint(
            "principal = false OR status = 'ativo'",
            name="ck_usuario_departamentos_principal_ativo",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["departamento_id"], ["departamentos.id"]),
        sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encerrado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usuario_departamentos_empresa_id", "usuario_departamentos", ["empresa_id"], unique=False)
    op.create_index("ix_usuario_departamentos_usuario_id", "usuario_departamentos", ["usuario_id"], unique=False)
    op.create_index("ix_usuario_departamentos_departamento_id", "usuario_departamentos", ["departamento_id"], unique=False)
    op.create_index("ix_usuario_departamentos_papel", "usuario_departamentos", ["papel"], unique=False)
    op.create_index("ix_usuario_departamentos_status", "usuario_departamentos", ["status"], unique=False)
    op.create_index("ix_usuario_departamentos_created_at", "usuario_departamentos", ["created_at"], unique=False)
    op.create_index(
        "uq_usuario_departamentos_ativo_usuario_departamento",
        "usuario_departamentos",
        ["usuario_id", "departamento_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ativo'"),
        sqlite_where=sa.text("status = 'ativo'"),
    )
    op.create_index(
        "uq_usuario_departamentos_head_ativo_departamento",
        "usuario_departamentos",
        ["departamento_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ativo' AND papel = 'head'"),
        sqlite_where=sa.text("status = 'ativo' AND papel = 'head'"),
    )
    op.create_index(
        "uq_usuario_departamentos_principal_ativo_usuario",
        "usuario_departamentos",
        ["usuario_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ativo' AND principal = true"),
        sqlite_where=sa.text("status = 'ativo' AND principal = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_usuario_departamentos_principal_ativo_usuario", table_name="usuario_departamentos")
    op.drop_index("uq_usuario_departamentos_head_ativo_departamento", table_name="usuario_departamentos")
    op.drop_index("uq_usuario_departamentos_ativo_usuario_departamento", table_name="usuario_departamentos")
    op.drop_index("ix_usuario_departamentos_created_at", table_name="usuario_departamentos")
    op.drop_index("ix_usuario_departamentos_status", table_name="usuario_departamentos")
    op.drop_index("ix_usuario_departamentos_papel", table_name="usuario_departamentos")
    op.drop_index("ix_usuario_departamentos_departamento_id", table_name="usuario_departamentos")
    op.drop_index("ix_usuario_departamentos_usuario_id", table_name="usuario_departamentos")
    op.drop_index("ix_usuario_departamentos_empresa_id", table_name="usuario_departamentos")
    op.drop_table("usuario_departamentos")
