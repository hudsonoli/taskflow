from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SessaoTrabalho(Base):
    """Sessão de trabalho — Central de Tráfego.

    ## `usuario_id` / `departamento_id` — expand/contract concluído (migrations 0015–0018)

    Até `0018`, `usuario_id`/`departamento_id` eram texto livre legado do mock (`"user-1"`),
    sem FK — mesmo defeito já corrigido para `usuarios.departamento_id` (`0007`/`0008`/`0009`),
    aqui reaplicado com o mesmo padrão. `usuario_id`/`departamento_id`, abaixo, JÁ SÃO a coluna
    final: FK real para `usuarios`/`departamentos`, `ON DELETE SET NULL`. A coluna transitória
    `usuario_uuid`/`departamento_uuid` (que coexistiu com o texto legado durante a janela de
    expansão) foi renomeada para o nome definitivo em `0018` — não existe mais.
    """

    __tablename__ = "sessoes_trabalho"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativa', 'encerrada', 'cancelada')",
            name="ck_sessoes_trabalho_status",
        ),
        CheckConstraint(
            "duracao_segundos IS NULL OR duracao_segundos >= 0",
            name="ck_sessoes_trabalho_duracao_nao_negativa",
        ),
        CheckConstraint(
            "status != 'ativa' OR (fim_em IS NULL AND evento_fim_id IS NULL AND duracao_segundos IS NULL)",
            name="ck_sessoes_trabalho_ativa_sem_fim",
        ),
        CheckConstraint(
            "status != 'encerrada' OR (fim_em IS NOT NULL AND evento_fim_id IS NOT NULL AND duracao_segundos IS NOT NULL)",
            name="ck_sessoes_trabalho_encerrada_com_fim",
        ),
        Index("ix_sessoes_trabalho_empresa_id", "empresa_id"),
        Index("ix_sessoes_trabalho_demanda_id", "demanda_id"),
        Index("ix_sessoes_trabalho_usuario_id", "usuario_id"),
        Index("ix_sessoes_trabalho_departamento_id", "departamento_id"),
        Index("ix_sessoes_trabalho_workflow_etapa_id", "workflow_etapa_id"),
        Index("ix_sessoes_trabalho_status", "status"),
        Index("ix_sessoes_trabalho_inicio_em", "inicio_em"),
        Index("ix_sessoes_trabalho_evento_inicio_id", "evento_inicio_id", unique=True),
        Index("ix_sessoes_trabalho_evento_fim_id", "evento_fim_id"),
        Index(
            "uq_sessoes_trabalho_ativa_demanda_usuario",
            "demanda_id",
            "usuario_id",
            unique=True,
            postgresql_where=text("usuario_id IS NOT NULL AND status = 'ativa'"),
            sqlite_where=text("usuario_id IS NOT NULL AND status = 'ativa'"),
        ),
        Index(
            "uq_sessoes_trabalho_ativa_demanda_departamento",
            "demanda_id",
            "departamento_id",
            unique=True,
            postgresql_where=text("usuario_id IS NULL AND departamento_id IS NOT NULL AND status = 'ativa'"),
            sqlite_where=text("usuario_id IS NULL AND departamento_id IS NOT NULL AND status = 'ativa'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    agencia_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    demanda_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_etapa_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Nullable de propósito: vínculo por usuário OU por departamento (nunca os dois sem
    # justificativa — ver SessaoTrabalhoService._validate_responsavel). SET NULL em vez de
    # cascade: apagar um usuário/departamento nunca pode apagar a sessão.
    usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    departamento_id: Mapped[str | None] = mapped_column(
        ForeignKey("departamentos.id", ondelete="SET NULL"), nullable=True
    )
    evento_inicio_id: Mapped[str] = mapped_column(String(36), nullable=False)
    evento_fim_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    inicio_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duracao_segundos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivo_encerramento: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
