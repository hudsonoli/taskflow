from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TipoTarefa(Base):
    """Tipo de tarefa (Fase 2G.2) — cadastro auxiliar da Empresa, referenciado hoje só pelo
    item de Modelo de Campanha de Projeto (`tipoTarefaId`, ainda em JSONB — a extração
    relacional é a Fase 2G.5).

    Sem `codigo_interno`/`codigo_referencia`: diferente de Workflow/Departamento/Cliente,
    não é documento pesquisável nem tem importação legada prevista — é só um rótulo com
    identidade por nome dentro da Empresa, igual a Categoria de Peça.
    """

    __tablename__ = "tipos_tarefa"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativo', 'inativo', 'arquivado')",
            name="ck_tipos_tarefa_status",
        ),
        UniqueConstraint("empresa_id", "nome_normalizado", name="uq_tipos_tarefa_empresa_nome_normalizado"),
        Index("ix_tipos_tarefa_empresa_id", "empresa_id"),
        Index("ix_tipos_tarefa_status", "status"),
        Index("ix_tipos_tarefa_nome_normalizado", "nome_normalizado"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Mesmo padrão de
    # WorkflowModelo/GrupoCliente/Departamento: colunas de ator são String(36) sem FK,
    # auditoria solta, não relação obrigatória.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
