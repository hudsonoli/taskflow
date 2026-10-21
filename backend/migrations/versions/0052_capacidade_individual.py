"""11B.2D-A — capacidade individual: jornada semanal própria opcional + ausências por data.

ADITIVA. Três tabelas novas e nenhuma coluna alterada:
- `usuario_jornadas` (UNIQUE usuario_id): a existência da linha = "este usuário tem jornada personalizada"; sem linha vale o expediente da empresa.
- `usuario_jornada_periodos`: períodos por dia da semana (mesmo padrão de `regra_expediente_periodos`).
- `usuario_ausencias`: férias/afastamento/folga/outro, DATE inclusivo, dia inteiro.

Sem backfill: usuários existentes continuam SEM jornada personalizada (usam o expediente da empresa) e não existe nenhuma ausência. Não toca `regra_expediente`, `demanda_workflow_etapas`,
`sessoes_trabalho`, `demanda_status_intervalos` nem `eventos`.

Downgrade: remove só as três tabelas (descarta jornadas e ausências cadastradas depois do upgrade).
"""
import sqlalchemy as sa
from alembic import op

revision = "f1b7c3a95d28"
down_revision = "e8a4c2d71f96"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuario_jornadas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("empresa_id", sa.String(36), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("usuario_id", sa.String(36), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("usuario_id", name="uq_usuario_jornadas_usuario_id"),
    )
    op.create_index("ix_usuario_jornadas_empresa_id", "usuario_jornadas", ["empresa_id"])

    op.create_table(
        "usuario_jornada_periodos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("jornada_id", sa.String(36), sa.ForeignKey("usuario_jornadas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dia_semana", sa.SmallInteger(), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), nullable=False),
        sa.Column("inicio", sa.Time(), nullable=False),
        sa.Column("fim", sa.Time(), nullable=False),
        sa.CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="ck_usuario_jornada_periodos_dia_semana"),
        sa.CheckConstraint("ordem >= 1", name="ck_usuario_jornada_periodos_ordem"),
        sa.CheckConstraint("inicio < fim", name="ck_usuario_jornada_periodos_inicio_fim"),
        sa.UniqueConstraint("jornada_id", "dia_semana", "ordem", name="uq_usuario_jornada_periodos_jornada_dia_ordem"),
    )
    op.create_index("ix_usuario_jornada_periodos_jornada_id", "usuario_jornada_periodos", ["jornada_id"])

    op.create_table(
        "usuario_ausencias",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("empresa_id", sa.String(36), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("usuario_id", sa.String(36), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("inicio", sa.Date(), nullable=False),
        sa.Column("fim", sa.Date(), nullable=False),
        sa.Column("observacao", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("tipo IN ('ferias', 'afastamento', 'folga', 'outro')", name="ck_usuario_ausencias_tipo"),
        sa.CheckConstraint("fim >= inicio", name="ck_usuario_ausencias_fim_apos_inicio"),
    )
    op.create_index("ix_usuario_ausencias_empresa_id", "usuario_ausencias", ["empresa_id"])
    op.create_index("ix_usuario_ausencias_usuario_id", "usuario_ausencias", ["usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_usuario_ausencias_usuario_id", table_name="usuario_ausencias")
    op.drop_index("ix_usuario_ausencias_empresa_id", table_name="usuario_ausencias")
    op.drop_table("usuario_ausencias")
    op.drop_index("ix_usuario_jornada_periodos_jornada_id", table_name="usuario_jornada_periodos")
    op.drop_table("usuario_jornada_periodos")
    op.drop_index("ix_usuario_jornadas_empresa_id", table_name="usuario_jornadas")
    op.drop_table("usuario_jornadas")
