from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsuarioCredencial(Base):
    __tablename__ = "usuario_credenciais"
    __table_args__ = (
        UniqueConstraint("usuario_id", name="uq_usuario_credenciais_usuario_id"),
        Index("ix_usuario_credenciais_usuario_id", "usuario_id"),
        Index("ix_usuario_credenciais_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    senha_definida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    senha_alterada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tentativas_falhas: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
