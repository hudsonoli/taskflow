from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Equipe(Base):
    __tablename__ = "equipes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativa', 'inativa', 'arquivada')",
            name="ck_equipes_status",
        ),
        CheckConstraint("trim(nome) <> ''", name="ck_equipes_nome_nao_vazio"),
        CheckConstraint("trim(codigo_interno) <> ''", name="ck_equipes_codigo_interno_nao_vazio"),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_equipes_empresa_codigo_interno"),
        UniqueConstraint("empresa_id", "nome", name="uq_equipes_empresa_nome"),
        Index("ix_equipes_empresa_id", "empresa_id"),
        Index("ix_equipes_departamento_id", "departamento_id"),
        Index("ix_equipes_status", "status"),
        Index("ix_equipes_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    departamento_id: Mapped[str] = mapped_column(
        ForeignKey(
            "departamentos.id",
            name="fk_equipes_departamento_id_departamentos",
        ),
        nullable=False,
    )
    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    inativado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_inativacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    inativado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    empresa = relationship("Empresa")
    departamento = relationship("Departamento")
