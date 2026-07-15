"""cria tabela cargos

Revision ID: 20260715_1a10
Revises: 20260715_1a9
Create Date: 2026-07-15 18:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260715_1a10"
down_revision: Union[str, None] = "20260715_1a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cargos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("codigo_interno", sa.String(length=64), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inativado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_inativacao", sa.String(length=500), nullable=True),
        sa.Column("inativado_por_usuario_id", sa.String(length=36), nullable=True),
        sa.CheckConstraint("status IN ('ativa', 'inativa', 'arquivada')", name="ck_cargos_status"),
        sa.CheckConstraint("trim(nome) <> ''", name="ck_cargos_nome_nao_vazio"),
        sa.CheckConstraint("trim(codigo_interno) <> ''", name="ck_cargos_codigo_interno_nao_vazio"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["inativado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "codigo_interno", name="uq_cargos_empresa_codigo_interno"),
        sa.UniqueConstraint("empresa_id", "nome", name="uq_cargos_empresa_nome"),
    )
    op.create_index("ix_cargos_empresa_id", "cargos", ["empresa_id"], unique=False)
    op.create_index("ix_cargos_status", "cargos", ["status"], unique=False)
    op.create_index("ix_cargos_created_at", "cargos", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cargos_created_at", table_name="cargos")
    op.drop_index("ix_cargos_status", table_name="cargos")
    op.drop_index("ix_cargos_empresa_id", table_name="cargos")
    op.drop_table("cargos")
