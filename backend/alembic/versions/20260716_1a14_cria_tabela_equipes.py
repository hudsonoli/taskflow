"""cria tabela equipes

Revision ID: 20260716_1a14
Revises: 20260716_1a13
Create Date: 2026-07-16 14:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260716_1a14"
down_revision: Union[str, None] = "20260716_1a13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "equipes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("codigo_interno", sa.String(length=64), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("inativado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_inativacao", sa.String(length=500), nullable=True),
        sa.Column("inativado_por_usuario_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('ativa', 'inativa', 'arquivada')", name="ck_equipes_status"),
        sa.CheckConstraint("trim(nome) <> ''", name="ck_equipes_nome_nao_vazio"),
        sa.CheckConstraint("trim(codigo_interno) <> ''", name="ck_equipes_codigo_interno_nao_vazio"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["inativado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "codigo_interno", name="uq_equipes_empresa_codigo_interno"),
        sa.UniqueConstraint("empresa_id", "nome", name="uq_equipes_empresa_nome"),
    )
    op.create_index("ix_equipes_empresa_id", "equipes", ["empresa_id"], unique=False)
    op.create_index("ix_equipes_status", "equipes", ["status"], unique=False)
    op.create_index("ix_equipes_created_at", "equipes", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_equipes_created_at", table_name="equipes")
    op.drop_index("ix_equipes_status", table_name="equipes")
    op.drop_index("ix_equipes_empresa_id", table_name="equipes")
    op.drop_table("equipes")
