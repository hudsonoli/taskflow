from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Empresa(Base):
    __tablename__ = "empresas"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativa', 'inativa', 'arquivada')",
            name="ck_empresas_status",
        ),
        UniqueConstraint("codigo_interno", name="uq_empresas_codigo_interno"),
        UniqueConstraint("documento", name="uq_empresas_documento"),
        Index("ix_empresas_status", "status"),
        Index("ix_empresas_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(32), nullable=True)
    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inativado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inativado_por_usuario_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    motivo_inativacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
