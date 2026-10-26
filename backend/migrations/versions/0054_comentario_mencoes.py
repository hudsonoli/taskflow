"""P1_AGORA_MENTIONS — @menções estruturadas em comentários de Demanda.

ADITIVA: cria `demanda_comentario_mencoes` (PK comentário+usuário, FKs com CASCADE, `empresa_id` para o isolamento por tenant). Sem backfill: os comentários existentes ficam sem menções
(o texto antigo que contenha "@" continua sendo só texto). A notificação reutiliza a central existente (evento `demanda.usuarios_mencionados`): nenhuma tabela de notificação nova.

Downgrade: remove a tabela (descarta as menções registradas depois do upgrade; os comentários e as notificações já entregues permanecem).
"""
import sqlalchemy as sa
from alembic import op

revision = "b3e7d1c85a46"
down_revision = "a9d2c6e84b17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demanda_comentario_mencoes",
        sa.Column("comentario_id", sa.String(36), sa.ForeignKey("demanda_comentarios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("usuario_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("empresa_id", sa.String(36), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_demanda_comentario_mencoes_empresa_id", "demanda_comentario_mencoes", ["empresa_id"])
    op.create_index("ix_demanda_comentario_mencoes_usuario_id", "demanda_comentario_mencoes", ["usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_demanda_comentario_mencoes_usuario_id", table_name="demanda_comentario_mencoes")
    op.drop_index("ix_demanda_comentario_mencoes_empresa_id", table_name="demanda_comentario_mencoes")
    op.drop_table("demanda_comentario_mencoes")
