from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjetoDepartamento(Base):
    """Associação Projeto ↔ Departamento responsável (`departamentoResponsavelIds` no mock).

    Um projeto costuma envolver mais de um setor (Atendimento + Criação, por exemplo), e é
    por aqui que a operação filtra "projetos do meu departamento".

    Estado atual, não histórico — ver eventos `projeto.departamento_adicionado` /
    `projeto.departamento_removido`.
    """

    __tablename__ = "projeto_departamentos"
    __table_args__ = (
        Index("ix_projeto_departamentos_departamento_id", "departamento_id"),
    )

    projeto_id: Mapped[str] = mapped_column(
        ForeignKey("projetos.id", ondelete="CASCADE"), primary_key=True
    )
    departamento_id: Mapped[str] = mapped_column(
        ForeignKey("departamentos.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
