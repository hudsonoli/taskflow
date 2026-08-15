from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandaDepartamento(Base):
    """Associação Demanda ↔ Departamento responsável.

    Uma demanda costuma envolver mais de um setor, e é por aqui que o escopo "Meu
    Departamento" filtra — o índice inverso sustenta essa consulta.

    Estado atual, não histórico — ver eventos `demanda.departamento_adicionado` /
    `.departamento_removido`.
    """

    __tablename__ = "demanda_departamentos"
    __table_args__ = (Index("ix_demanda_departamentos_departamento_id", "departamento_id"),)

    demanda_id: Mapped[str] = mapped_column(
        ForeignKey("demandas.id", ondelete="CASCADE"), primary_key=True
    )
    departamento_id: Mapped[str] = mapped_column(
        ForeignKey("departamentos.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
