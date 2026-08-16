from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandaWorkflowEtapaDepartamentoResponsavel(Base):
    """Associação Etapa de workflow da Demanda ↔ Departamento responsável.

    Copiado de `workflow_modelo_etapa_departamentos_responsaveis` no momento da
    materialização — vínculo próprio da Demanda, não consulta ao template depois. PK
    composta, CASCADE dos dois lados.
    """

    __tablename__ = "demanda_workflow_etapa_departamentos_responsaveis"
    __table_args__ = (
        Index("ix_demanda_workflow_etapa_dep_resp_departamento_id", "departamento_id"),
    )

    demanda_workflow_etapa_id: Mapped[str] = mapped_column(
        ForeignKey("demanda_workflow_etapas.id", ondelete="CASCADE"), primary_key=True
    )
    departamento_id: Mapped[str] = mapped_column(
        ForeignKey("departamentos.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
