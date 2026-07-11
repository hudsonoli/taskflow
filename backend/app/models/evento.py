from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class Evento(Base):
    __tablename__ = "eventos"
    __table_args__ = (
        Index("ix_eventos_empresa_id", "empresa_id"),
        Index("ix_eventos_entidade", "entidade_tipo", "entidade_id"),
        Index("ix_eventos_tipo", "tipo"),
        Index("ix_eventos_occurred_at", "occurred_at"),
        Index("ix_eventos_correlation_id", "correlation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(String(128), nullable=False)
    agencia_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tipo: Mapped[str] = mapped_column(String(128), nullable=False)
    entidade_tipo: Mapped[str] = mapped_column(String(128), nullable=False)
    entidade_id: Mapped[str] = mapped_column(String(128), nullable=False)
    usuario_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", json_type, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
