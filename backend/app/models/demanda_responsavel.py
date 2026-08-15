from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandaResponsavel(Base):
    """Associação Demanda ↔ Usuário responsável.

    Estado atual, não histórico: entradas e saídas ficam rastreáveis pelos eventos
    `demanda.responsavel_adicionado` / `.responsavel_removido`.

    O índice inverso não é conveniência — é o que sustenta o escopo "Meu Dia", que pergunta
    "de quais demandas esta pessoa é responsável" a cada abertura da tela.
    """

    __tablename__ = "demanda_responsaveis"
    __table_args__ = (Index("ix_demanda_responsaveis_usuario_id", "usuario_id"),)

    demanda_id: Mapped[str] = mapped_column(
        ForeignKey("demandas.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
