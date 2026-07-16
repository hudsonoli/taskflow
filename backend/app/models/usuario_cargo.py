from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, false, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UsuarioCargo(Base):
    __tablename__ = "usuario_cargos"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativo', 'inativo')",
            name="ck_usuario_cargos_status",
        ),
        CheckConstraint(
            "fim_em IS NULL OR fim_em >= inicio_em",
            name="ck_usuario_cargos_fim_em_maior_inicio",
        ),
        CheckConstraint(
            "(status = 'ativo' AND fim_em IS NULL) OR (status = 'inativo' AND fim_em IS NOT NULL)",
            name="ck_usuario_cargos_status_fim_em",
        ),
        CheckConstraint(
            "principal = false OR status = 'ativo'",
            name="ck_usuario_cargos_principal_ativo",
        ),
        Index("ix_usuario_cargos_empresa_id", "empresa_id"),
        Index("ix_usuario_cargos_usuario_id", "usuario_id"),
        Index("ix_usuario_cargos_cargo_id", "cargo_id"),
        Index("ix_usuario_cargos_status", "status"),
        Index("ix_usuario_cargos_created_at", "created_at"),
        Index(
            "uq_usuario_cargos_ativo_usuario_cargo",
            "usuario_id",
            "cargo_id",
            unique=True,
            postgresql_where=text("status = 'ativo'"),
            sqlite_where=text("status = 'ativo'"),
        ),
        Index(
            "uq_usuario_cargos_principal_ativo_usuario",
            "usuario_id",
            unique=True,
            postgresql_where=text("status = 'ativo' AND principal = true"),
            sqlite_where=text("status = 'ativo' AND principal = true"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    cargo_id: Mapped[str] = mapped_column(ForeignKey("cargos.id"), nullable=False)
    principal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ativo", server_default="ativo")
    inicio_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_encerramento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    criado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    encerrado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    empresa = relationship("Empresa")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    cargo = relationship("Cargo")
    criado_por_usuario = relationship("Usuario", foreign_keys=[criado_por_usuario_id])
    encerrado_por_usuario = relationship("Usuario", foreign_keys=[encerrado_por_usuario_id])
