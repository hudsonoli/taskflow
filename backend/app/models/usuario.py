from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "perfil_base IN ('admin', 'gestor', 'operador')",
            name="ck_usuarios_perfil_base",
        ),
        CheckConstraint(
            "status IN ('ativo', 'inativo', 'bloqueado', 'arquivado')",
            name="ck_usuarios_status",
        ),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_usuarios_empresa_codigo_interno"),
        UniqueConstraint("empresa_id", "email", name="uq_usuarios_empresa_email"),
        Index("ix_usuarios_empresa_id", "empresa_id"),
        Index("ix_usuarios_status", "status"),
        Index("ix_usuarios_perfil_base", "perfil_base"),
        Index("ix_usuarios_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil_base: Mapped[str] = mapped_column(String(32), nullable=False)
    acesso_sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inativado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inativado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    motivo_inativacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
