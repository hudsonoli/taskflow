from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkflowModeloEtapaResponsavel(Base):
    """Associação Etapa de WorkflowModelo ↔ Usuário responsável (`usuarioResponsavelIds`).

    Mesma forma de `projeto_responsaveis`/`equipe_membros`: PK composta, CASCADE dos dois
    lados (a etapa nunca sobrevive sem o modelo; o vínculo nunca sobrevive sem a etapa).
    """

    __tablename__ = "workflow_modelo_etapa_responsaveis"
    __table_args__ = (
        Index("ix_workflow_modelo_etapa_responsaveis_usuario_id", "usuario_id"),
    )

    workflow_modelo_etapa_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_modelo_etapas.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
