from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SessaoTrabalho(Base):
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
    empresa_id: Mapped[str] = mapped_column(String(128), nullable=False)
    agencia_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    demanda_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_etapa_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    usuario_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    departamento_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evento_inicio_id: Mapped[str] = mapped_column(String(36), nullable=False)
    evento_fim_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    inicio_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duracao_segundos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivo_encerramento: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
