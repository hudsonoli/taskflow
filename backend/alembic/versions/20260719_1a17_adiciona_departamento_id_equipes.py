"""adiciona departamento_id em equipes

Revision ID: 20260719_1a17
Revises: 20260716_1a16
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260719_1a17"
down_revision: Union[str, None] = "20260716_1a16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "equipes",
        sa.Column("departamento_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_equipes_departamento_id_departamentos",
        "equipes",
        "departamentos",
        ["departamento_id"],
        ["id"],
    )
    op.create_index(
        "ix_equipes_departamento_id",
        "equipes",
        ["departamento_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_equipes_departamento_id", table_name="equipes")
    op.drop_constraint(
        "fk_equipes_departamento_id_departamentos",
        "equipes",
        type_="foreignkey",
    )
    op.drop_column("equipes", "departamento_id")
