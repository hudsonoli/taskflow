from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClienteTipoPessoa(StrEnum):
    JURIDICA = "juridica"
    FISICA = "fisica"


class ClienteStatus(StrEnum):
    ATIVO = "ativo"
    SUSPENSO = "suspenso"
    INATIVO = "inativo"


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = (
        CheckConstraint(
            "tipo_pessoa IN ('juridica', 'fisica')",
            name="ck_clientes_tipo_pessoa",
        ),
        CheckConstraint(
            "status IN ('ativo', 'suspenso', 'inativo')",
            name="ck_clientes_status",
        ),
        CheckConstraint("trim(codigo_interno) <> ''", name="ck_clientes_codigo_interno_nao_vazio"),
        CheckConstraint(
            "documento IS NULL OR length(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(documento, '0', ''), '1', ''), '2', ''), '3', ''), '4', ''), '5', ''), '6', ''), '7', ''), '8', ''), '9', '')) = 0",
            name="ck_clientes_documento_apenas_digitos",
        ),
        CheckConstraint(
            "documento IS NULL OR length(documento) IN (11, 14)",
            name="ck_clientes_documento_tamanho",
        ),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_clientes_empresa_codigo_interno"),
        Index("ix_clientes_empresa_id", "empresa_id"),
        Index("ix_clientes_agencia_id", "agencia_id"),
        Index("ix_clientes_status", "status"),
        Index("ix_clientes_tipo_pessoa", "tipo_pessoa"),
        Index("ix_clientes_documento", "documento"),
        Index("ix_clientes_created_at", "created_at"),
        Index(
            "uq_clientes_empresa_documento",
            "empresa_id",
            "documento",
            unique=True,
            postgresql_where=text("documento IS NOT NULL AND documento <> ''"),
            sqlite_where=text("documento IS NOT NULL AND documento <> ''"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    agencia_id: Mapped[str | None] = mapped_column(
        ForeignKey("agencias.id", ondelete="SET NULL"),
        nullable=True,
    )
    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    tipo_pessoa: Mapped[str] = mapped_column(String(32), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(14), nullable=True)
    razao_social: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sigla: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    celular: Mapped[str | None] = mapped_column(String(32), nullable=True)
    site: Mapped[str | None] = mapped_column(String(255), nullable=True)
    codigo_externo: Mapped[str | None] = mapped_column(String(128), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ClienteStatus.ATIVO.value)
    status_alterado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_alterado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    motivo_status: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    empresa = relationship("Empresa")
    agencia = relationship("Agencia")
