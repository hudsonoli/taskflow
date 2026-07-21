"""adiciona razao_social em empresas

Revision ID: 20260721_1a19
Revises: 20260719_1a18
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260721_1a19"
down_revision: Union[str, Sequence[str], None] = "20260719_1a18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: registros existentes (ex.: EMP-TESTCLIENT) não têm razão
    # social hoje e não devem ser alterados nem receber valor fabricado.
    # A exigência de "razão social não vazia" é uma regra do bootstrap da
    # empresa piloto, não uma constraint de banco retroativa.
    op.add_column(
        "empresas",
        sa.Column("razao_social", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("empresas", "razao_social")
