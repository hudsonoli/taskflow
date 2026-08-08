from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GrupoCliente(Base):
    __tablename__ = "grupos_cliente"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativo', 'arquivado')",
            name="ck_grupos_cliente_status",
        ),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_grupos_cliente_empresa_codigo_interno"),
        # Unicidade case-insensitive de nome, valendo entre ativos E arquivados (ver
        # docs/padrao-arquivamento.md e GrupoClienteService) — nome_normalizado é sempre
        # nome.strip().lower(), calculado no service ao gravar.
        UniqueConstraint("empresa_id", "nome_normalizado", name="uq_grupos_cliente_empresa_nome_normalizado"),
        Index("ix_grupos_cliente_empresa_id", "empresa_id"),
        Index("ix_grupos_cliente_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    # Estável e imutável após a criação — referência operacional/legada (ver
    # docs/padrao-arquivamento.md); gerado automaticamente pela API pública, nunca aceito
    # via schema HTTP (só a função interna de seed/importador pode fornecer um valor legado).
    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(255), nullable=False)
    cor_identificacao: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Mesmo padrão
    # de tipos de app/models/usuario.py: colunas de ator são String(36) (não sqlalchemy.Uuid)
    # porque usuarios.id já é String(36) — tipo físico diferente pro mesmo identificador
    # seria incompatível. Sem ForeignKey: campos de auditoria soltos, não relação obrigatória.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
