"""cria usuario_equipes

Revision ID: 20260716_1a15
Revises: 20260716_1a14
Create Date: 2026-07-16 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260716_1a15"
down_revision: Union[str, None] = "20260716_1a14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuario_equipes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("equipe_id", sa.String(length=36), nullable=False),
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
        sa.CheckConstraint("papel IN ('membro', 'lider', 'coordenador')", name="ck_usuario_equipes_papel"),
        sa.CheckConstraint("status IN ('ativo', 'encerrado')", name="ck_usuario_equipes_status"),
        sa.CheckConstraint(
            "fim_em IS NULL OR fim_em >= inicio_em",
            name="ck_usuario_equipes_fim_em_maior_inicio",
        ),
        sa.CheckConstraint(
            "(status = 'ativo' AND fim_em IS NULL) OR (status = 'encerrado' AND fim_em IS NOT NULL)",
            name="ck_usuario_equipes_status_fim_em",
        ),
        sa.CheckConstraint(
            "principal = false OR status = 'ativo'",
            name="ck_usuario_equipes_principal_ativo",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["equipe_id"], ["equipes.id"]),
        sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encerrado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usuario_equipes_empresa_id", "usuario_equipes", ["empresa_id"], unique=False)
    op.create_index("ix_usuario_equipes_usuario_id", "usuario_equipes", ["usuario_id"], unique=False)
    op.create_index("ix_usuario_equipes_equipe_id", "usuario_equipes", ["equipe_id"], unique=False)
    op.create_index("ix_usuario_equipes_papel", "usuario_equipes", ["papel"], unique=False)
    op.create_index("ix_usuario_equipes_status", "usuario_equipes", ["status"], unique=False)
    op.create_index("ix_usuario_equipes_created_at", "usuario_equipes", ["created_at"], unique=False)
    op.create_index(
        "uq_usuario_equipes_ativo_usuario_equipe",
        "usuario_equipes",
        ["usuario_id", "equipe_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ativo'"),
        sqlite_where=sa.text("status = 'ativo'"),
    )
    op.create_index(
        "uq_usuario_equipes_lider_ativo_equipe",
        "usuario_equipes",
        ["equipe_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ativo' AND papel = 'lider'"),
        sqlite_where=sa.text("status = 'ativo' AND papel = 'lider'"),
    )
    op.create_index(
        "uq_usuario_equipes_principal_ativo_usuario",
        "usuario_equipes",
        ["usuario_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ativo' AND principal = true"),
        sqlite_where=sa.text("status = 'ativo' AND principal = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_usuario_equipes_principal_ativo_usuario", table_name="usuario_equipes")
    op.drop_index("uq_usuario_equipes_lider_ativo_equipe", table_name="usuario_equipes")
    op.drop_index("uq_usuario_equipes_ativo_usuario_equipe", table_name="usuario_equipes")
    op.drop_index("ix_usuario_equipes_created_at", table_name="usuario_equipes")
    op.drop_index("ix_usuario_equipes_status", table_name="usuario_equipes")
    op.drop_index("ix_usuario_equipes_papel", table_name="usuario_equipes")
    op.drop_index("ix_usuario_equipes_equipe_id", table_name="usuario_equipes")
    op.drop_index("ix_usuario_equipes_usuario_id", table_name="usuario_equipes")
    op.drop_index("ix_usuario_equipes_empresa_id", table_name="usuario_equipes")
    op.drop_table("usuario_equipes")
