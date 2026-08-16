from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkflowModeloEtapaDepartamentoResponsavel(Base):
    """Associação Etapa de WorkflowModelo ↔ Departamento responsável.

    Mesma forma de `workflow_modelo_etapa_responsaveis` (usuário), só que o outro lado é
    Departamento — os dois convivem: uma etapa pode ter responsáveis por usuário, por
    departamento, ou os dois. PK composta, CASCADE dos dois lados.
    """

    __tablename__ = "workflow_modelo_etapa_departamentos_responsaveis"
    __table_args__ = (
        Index("ix_workflow_modelo_etapa_dep_resp_departamento_id", "departamento_id"),
    )

    workflow_modelo_etapa_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_modelo_etapas.id", ondelete="CASCADE"), primary_key=True
    )
    departamento_id: Mapped[str] = mapped_column(
        ForeignKey("departamentos.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
