from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, SmallInteger, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# `dia_semana` usa `datetime.weekday()`: 0=segunda .. 6=domingo — a MESMA convenção de `regra_expediente_periodos` (um só mapeamento de dia da semana em todo o projeto).

TIPOS_AUSENCIA = ("ferias", "afastamento", "folga", "outro")


class UsuarioJornada(Base):
    """Jornada semanal PRÓPRIA de um usuário (11B.2D-A). A EXISTÊNCIA da linha é o estado: "este usuário tem jornada personalizada". Sem linha = usa a semana da RegraExpediente da empresa
    (nada é copiado para o usuário). Existindo, ela SUBSTITUI a semana recorrente da empresa por inteiro: dia sem período = 0 minutos, sem fallback dia a dia.

    Não guarda timezone (vale o da empresa), nem percentual alocável (é da empresa), nem nada de financeiro. Sem cascade em `usuario_id`: usuário nunca é DELETE físico (arquivamento).
    """

    __tablename__ = "usuario_jornadas"
    __table_args__ = (
        UniqueConstraint("usuario_id", name="uq_usuario_jornadas_usuario_id"),
        Index("ix_usuario_jornadas_empresa_id", "empresa_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UsuarioJornadaPeriodo(Base):
    """Um período de trabalho de um dia da semana da jornada individual. Mesmo padrão de `RegraExpedientePeriodo`: 0..n por dia, início inclusivo/fim exclusivo, `inicio < fim`, sem virar a
    meia-noite; a ausência de sobreposição é validada no schema/service (o Postgres não tem constraint de intervalo sem extensão)."""

    __tablename__ = "usuario_jornada_periodos"
    __table_args__ = (
        CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="ck_usuario_jornada_periodos_dia_semana"),
        CheckConstraint("ordem >= 1", name="ck_usuario_jornada_periodos_ordem"),
        CheckConstraint("inicio < fim", name="ck_usuario_jornada_periodos_inicio_fim"),
        UniqueConstraint("jornada_id", "dia_semana", "ordem", name="uq_usuario_jornada_periodos_jornada_dia_ordem"),
        Index("ix_usuario_jornada_periodos_jornada_id", "jornada_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    jornada_id: Mapped[str] = mapped_column(ForeignKey("usuario_jornadas.id", ondelete="CASCADE"), nullable=False)
    dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ordem: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    inicio: Mapped[time] = mapped_column(Time(), nullable=False)
    fim: Mapped[time] = mapped_column(Time(), nullable=False)


class UsuarioAusencia(Base):
    """Ausência de capacidade de um usuário (férias, afastamento, folga, outro) — DIA INTEIRO, por DATE, intervalo inclusivo (`inicio`..`fim`) no calendário da empresa. Sem horas, sem meio período,
    sem banco de horas, sem saldo de férias. Ausências podem se sobrepor: o dia continua com capacidade 0 e nunca é descontado duas vezes (o cálculo deduplica por data).

    `observacao` é texto livre do gestor e NÃO vai para eventos de auditoria (pode conter dado sensível). A remoção é física: o histórico da ausência são os eventos `usuario.ausencia_*`.
    """

    __tablename__ = "usuario_ausencias"
    __table_args__ = (
        CheckConstraint("tipo IN ('ferias', 'afastamento', 'folga', 'outro')", name="ck_usuario_ausencias_tipo"),
        CheckConstraint("fim >= inicio", name="ck_usuario_ausencias_fim_apos_inicio"),
        Index("ix_usuario_ausencias_empresa_id", "empresa_id"),
        Index("ix_usuario_ausencias_usuario_id", "usuario_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    inicio: Mapped[date] = mapped_column(Date(), nullable=False)
    fim: Mapped[date] = mapped_column(Date(), nullable=False)
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
