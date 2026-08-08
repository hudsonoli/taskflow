from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SequenciaReferencia(Base):
    """Contador de códigos de referência, isolado por empresa + tipo de entidade + ano.

    Uma linha por (empresa, tipo, ano). A virada de ano não reseta nada: cria-se uma linha
    nova de 2027 começando em 1 e a de 2026 permanece intacta, preservando o histórico de
    quantos códigos foram emitidos em cada ano.

    O incremento é feito por INSERT ... ON CONFLICT ... DO UPDATE ... RETURNING (ver
    app/core/referencias.py) — nunca por MAX()+1 nem por cálculo em Python.
    """

    __tablename__ = "sequencias_referencia"
    __table_args__ = (
        UniqueConstraint("empresa_id", "tipo_entidade", "ano", name="uq_sequencias_referencia_escopo"),
        Index("ix_sequencias_referencia_empresa_id", "empresa_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    # Valor da lista fechada em app/core/referencias.py (departamento, equipe). A validação
    # é feita em Python antes de chegar aqui — a coluna é livre de propósito, para não
    # exigir migration a cada domínio novo entrar no mapa.
    tipo_entidade: Mapped[str] = mapped_column(String(32), nullable=False)
    ano: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ultimo_numero: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
