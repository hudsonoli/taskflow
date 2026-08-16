from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkflowModelo(Base):
    """Modelo de workflow (template de etapas para execução de tarefas).

    Mesmos três identificadores de Departamento/Equipe (ver docs/padrao-migracao-dominio.md):
    `id` técnico, `codigo_referencia` (W26000001) oficial, `codigo_interno` como ponte de
    importação — Workflow está na lista de domínios com importação XLSX planejada (ver
    docs/pendencias-arquiteturais.md, item 4).

    Sem `descricao`/`cor_identificacao`: o mock nunca teve esses campos, e a interface atual
    (WorkflowsGrid) não exibe nada além de nome, contagem de etapas e badge de ativo/inativo.
    """

    __tablename__ = "workflow_modelos"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativo', 'inativo', 'arquivado')",
            name="ck_workflow_modelos_status",
        ),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_workflow_modelos_empresa_codigo_interno"),
        UniqueConstraint("empresa_id", "codigo_referencia", name="uq_workflow_modelos_empresa_codigo_referencia"),
        UniqueConstraint(
            "empresa_id",
            "ano_referencia",
            "sequencial_referencia",
            name="uq_workflow_modelos_empresa_ano_sequencial",
        ),
        # Unicidade de nome case-insensitive valendo entre ativos, inativos E arquivados.
        UniqueConstraint("empresa_id", "nome_normalizado", name="uq_workflow_modelos_empresa_nome_normalizado"),
        Index("ix_workflow_modelos_empresa_id", "empresa_id"),
        Index("ix_workflow_modelos_status", "status"),
        Index("ix_workflow_modelos_codigo_referencia", "codigo_referencia"),
        Index("ix_workflow_modelos_codigo_interno", "codigo_interno"),
        Index("ix_workflow_modelos_nome_normalizado", "nome_normalizado"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    codigo_referencia: Mapped[str] = mapped_column(String(16), nullable=False)
    ano_referencia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sequencial_referencia: Mapped[int] = mapped_column(Integer, nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Colunas de
    # ator são String(36) sem FK, como em usuario.py e departamento.py: auditoria solta, não
    # relação obrigatória.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
