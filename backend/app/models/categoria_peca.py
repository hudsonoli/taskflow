from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CategoriaPeca(Base):
    """Categoria do catálogo de Peças (Fase 2G.4) — cadastro auxiliar da Empresa, referenciado
    por `Peca.categoria_id`. Ciclo de vida de 2 estados (ativo/arquivado, sem "inativo") —
    mesmo padrão de GrupoCliente: uma categoria não tem um estado intermediário de uso, só
    existe ou está arquivada.
    """

    __tablename__ = "categorias_peca"
    __table_args__ = (
        CheckConstraint("status IN ('ativo', 'arquivado')", name="ck_categorias_peca_status"),
        UniqueConstraint("empresa_id", "nome_normalizado", name="uq_categorias_peca_empresa_nome_normalizado"),
        Index("ix_categorias_peca_empresa_id", "empresa_id"),
        Index("ix_categorias_peca_status", "status"),
        Index("ix_categorias_peca_nome_normalizado", "nome_normalizado"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(100), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Nunca DELETE
    # físico: uma Peça pode continuar referenciando uma Categoria arquivada (FK sem CASCADE).
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
