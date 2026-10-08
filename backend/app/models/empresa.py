from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.core.empresa_slug import slug_a_partir_do_codigo


def _slug_padrao(contexto) -> str:
    """Rede de segurança do INSERT: quem cria Empresa sem informar `slug` (CLI/seed/testes) recebe um derivado de
    `codigo_interno`. O cadastro de verdade (EmpresaService) sempre informa e confere a unicidade antes."""
    return slug_a_partir_do_codigo(contexto.get_current_parameters().get("codigo_interno") or "", em_uso=lambda _s: False)


class Empresa(Base):
    __tablename__ = "empresas"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativa', 'inativa', 'arquivada')",
            name="ck_empresas_status",
        ),
        UniqueConstraint("codigo_interno", name="uq_empresas_codigo_interno"),
        UniqueConstraint("documento", name="uq_empresas_documento"),
        UniqueConstraint("slug", name="uq_empresas_slug"),
        CheckConstraint("slug ~ '^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$'", name="ck_empresas_slug_formato"),
        CheckConstraint(
            "slug NOT IN ('plataforma', 'api', 'login', 'logout', 'admin', 'suporte')",
            name="ck_empresas_slug_reservado",
        ),
        Index("ix_empresas_status", "status"),
        Index("ix_empresas_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(32), nullable=True)
    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    # Identificador público de URL (futuro login multiempresa) — ver app/core/empresa_slug.py.
    slug: Mapped[str] = mapped_column(String(40), nullable=False, default=_slug_padrao)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inativado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inativado_por_usuario_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    motivo_inativacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
