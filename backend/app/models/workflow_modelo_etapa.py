from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkflowModeloEtapa(Base):
    """Etapa de um WorkflowModelo (`etapas` no mock).

    `ordem` substitui a ordenação implícita do array do mock — precisa ser estável e
    consultável, por isso é coluna própria, não posição num JSON.

    Sem soft-delete próprio: etapas seguem o ciclo de vida do modelo (arquivar o modelo não
    apaga etapas; editar o modelo substitui o conjunto inteiro numa transação — ver
    WorkflowModeloService). CASCADE é seguro pelo mesmo motivo de projeto_responsaveis: o
    modelo nunca é apagado fisicamente, só arquivado.
    """

    __tablename__ = "workflow_modelo_etapas"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('execucao', 'aprovacao')",
            name="ck_workflow_modelo_etapas_tipo",
        ),
        CheckConstraint(
            "unidade_prazo IN ('dias_corridos', 'dias_uteis', 'horas')",
            name="ck_workflow_modelo_etapas_unidade_prazo",
        ),
        Index("ix_workflow_modelo_etapas_modelo_ordem", "workflow_modelo_id", "ordem"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_modelo_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_modelos.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    quantidade_antes_deadline: Mapped[int] = mapped_column(Integer, nullable=False)
    unidade_prazo: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
