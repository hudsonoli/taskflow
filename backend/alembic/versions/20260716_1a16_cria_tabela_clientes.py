"""cria tabela clientes

Revision ID: 20260716_1a16
Revises: 20260716_1a15
Create Date: 2026-07-16 22:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260716_1a16"
down_revision: Union[str, None] = "20260716_1a15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("agencia_id", sa.String(length=36), nullable=True),
        sa.Column("codigo_interno", sa.String(length=64), nullable=False),
        sa.Column("tipo_pessoa", sa.String(length=32), nullable=False),
        sa.Column("documento", sa.String(length=14), nullable=True),
        sa.Column("razao_social", sa.String(length=255), nullable=True),
        sa.Column("nome_fantasia", sa.String(length=255), nullable=True),
        sa.Column("nome", sa.String(length=255), nullable=True),
        sa.Column("sigla", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telefone", sa.String(length=32), nullable=True),
        sa.Column("celular", sa.String(length=32), nullable=True),
        sa.Column("site", sa.String(length=255), nullable=True),
        sa.Column("codigo_externo", sa.String(length=128), nullable=True),
        sa.Column("observacoes", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ativo"),
        sa.Column("status_alterado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_alterado_por_usuario_id", sa.String(length=36), nullable=True),
        sa.Column("motivo_status", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("tipo_pessoa IN ('juridica', 'fisica')", name="ck_clientes_tipo_pessoa"),
        sa.CheckConstraint("status IN ('ativo', 'suspenso', 'inativo')", name="ck_clientes_status"),
        sa.CheckConstraint("trim(codigo_interno) <> ''", name="ck_clientes_codigo_interno_nao_vazio"),
        sa.CheckConstraint(
            "documento IS NULL OR length(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(documento, '0', ''), '1', ''), '2', ''), '3', ''), '4', ''), '5', ''), '6', ''), '7', ''), '8', ''), '9', '')) = 0",
            name="ck_clientes_documento_apenas_digitos",
        ),
        sa.CheckConstraint(
            "documento IS NULL OR length(documento) IN (11, 14)",
            name="ck_clientes_documento_tamanho",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["agencia_id"], ["agencias.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["status_alterado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "codigo_interno", name="uq_clientes_empresa_codigo_interno"),
    )
    op.create_index("ix_clientes_empresa_id", "clientes", ["empresa_id"], unique=False)
    op.create_index("ix_clientes_agencia_id", "clientes", ["agencia_id"], unique=False)
    op.create_index("ix_clientes_status", "clientes", ["status"], unique=False)
    op.create_index("ix_clientes_tipo_pessoa", "clientes", ["tipo_pessoa"], unique=False)
    op.create_index("ix_clientes_documento", "clientes", ["documento"], unique=False)
    op.create_index("ix_clientes_created_at", "clientes", ["created_at"], unique=False)
    op.create_index(
        "uq_clientes_empresa_documento",
        "clientes",
        ["empresa_id", "documento"],
        unique=True,
        postgresql_where=sa.text("documento IS NOT NULL AND documento <> ''"),
    )


def downgrade() -> None:
    op.drop_index("uq_clientes_empresa_documento", table_name="clientes")
    op.drop_index("ix_clientes_created_at", table_name="clientes")
    op.drop_index("ix_clientes_documento", table_name="clientes")
    op.drop_index("ix_clientes_tipo_pessoa", table_name="clientes")
    op.drop_index("ix_clientes_status", table_name="clientes")
    op.drop_index("ix_clientes_agencia_id", table_name="clientes")
    op.drop_index("ix_clientes_empresa_id", table_name="clientes")
    op.drop_table("clientes")
