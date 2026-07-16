"""cria tabela usuarios

Revision ID: 20260715_1a7
Revises: 20260715_1a6
Create Date: 2026-07-15 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260715_1a7"
down_revision: Union[str, Sequence[str], None] = "20260715_1a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("codigo_interno", sa.String(length=64), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("perfil_base", sa.String(length=32), nullable=False),
        sa.Column("acesso_sistema", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inativado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inativado_por_usuario_id", sa.String(length=36), nullable=True),
        sa.Column("motivo_inativacao", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "perfil_base IN ('admin', 'gestor', 'operador')",
            name="ck_usuarios_perfil_base",
        ),
        sa.CheckConstraint(
            "status IN ('ativo', 'inativo', 'bloqueado', 'arquivado')",
            name="ck_usuarios_status",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["inativado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "codigo_interno", name="uq_usuarios_empresa_codigo_interno"),
        sa.UniqueConstraint("empresa_id", "email", name="uq_usuarios_empresa_email"),
    )
    op.create_index("ix_usuarios_empresa_id", "usuarios", ["empresa_id"])
    op.create_index("ix_usuarios_status", "usuarios", ["status"])
    op.create_index("ix_usuarios_perfil_base", "usuarios", ["perfil_base"])
    op.create_index("ix_usuarios_created_at", "usuarios", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_usuarios_created_at", table_name="usuarios")
    op.drop_index("ix_usuarios_perfil_base", table_name="usuarios")
    op.drop_index("ix_usuarios_status", table_name="usuarios")
    op.drop_index("ix_usuarios_empresa_id", table_name="usuarios")
    op.drop_table("usuarios")
