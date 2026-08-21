from datetime import datetime, time

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# `dia_semana` usa `datetime.weekday()` nativo do Python: 0=segunda .. 6=domingo. Mesma
# convenção de app/core/expediente.py — só um mapeamento de dia da semana em todo o projeto.


class RegraExpediente(Base):
    """Regra de expediente da Empresa (Fase 2G.3) — singleton: uma linha por Empresa.

    Model SQL, não confundir com o DTO puro `app.core.expediente.RegraExpediente` usado pelo
    cálculo (`esta_dentro_expediente`) — este módulo é persistência, aquele é cálculo sem
    SQLAlchemy. `RegraExpedienteService` converte um no outro.

    Sem soft-delete: singleton por Empresa nasce junto com a primeira consulta (ver
    `RegraExpedienteService.get_ou_criar`) e nunca é removido, só editado.
    """

    __tablename__ = "regra_expediente"
    __table_args__ = (
        Index("ix_regra_expediente_empresa_id", "empresa_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False, unique=True)

    # Chave-mestra do controle de expediente — NÃO confundir com `RegraExpedienteDia.ativo`
    # (esse é por dia da semana). `ativo=True` liga o controle: dias/janelas configurados
    # abaixo passam a valer. `ativo=False` desliga o controle inteiro — a operação deixa de
    # ser bloqueada por dia ou horário, independente do que os dias tenham configurado (ver
    # `esta_dentro_expediente` em app/core/expediente.py, semântica oficializada na Fase 2G.3).
    ativo: Mapped[bool] = mapped_column(nullable=False, default=True)
    tolerancia_retomada_minutos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegraExpedienteDia(Base):
    """Um dia da semana de uma RegraExpediente. Sempre exatamente 7 por regra (0..6) — não é
    invariante de banco (não há trigger), é mantido pelo service: `atualizar` substitui o
    conjunto inteiro numa única transação, nunca incrementalmente (mesmo raciocínio de
    `WorkflowModeloService._substituir_etapas`).

    `ativo=False` → dia inteiro fora do expediente; horários ficam `NULL` nesse caso (CHECK
    abaixo exige o oposto quando `ativo=True`: as quatro colunas de horário preenchidas,
    início < fim em cada janela, e a manhã não pode terminar depois que a tarde começa).
    """

    __tablename__ = "regra_expediente_dias"
    __table_args__ = (
        CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="ck_regra_expediente_dias_dia_semana"),
        CheckConstraint(
            "NOT ativo OR ("
            "manha_inicio IS NOT NULL AND manha_fim IS NOT NULL AND "
            "tarde_inicio IS NOT NULL AND tarde_fim IS NOT NULL AND "
            "manha_inicio < manha_fim AND tarde_inicio < tarde_fim AND manha_fim <= tarde_inicio"
            ")",
            name="ck_regra_expediente_dias_janelas_validas",
        ),
        UniqueConstraint("regra_expediente_id", "dia_semana", name="uq_regra_expediente_dias_regra_dia"),
        Index("ix_regra_expediente_dias_regra_id", "regra_expediente_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    regra_expediente_id: Mapped[str] = mapped_column(
        ForeignKey("regra_expediente.id", ondelete="CASCADE"), nullable=False
    )
    dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ativo: Mapped[bool] = mapped_column(nullable=False, default=False)

    manha_inicio: Mapped[time | None] = mapped_column(Time(), nullable=True)
    manha_fim: Mapped[time | None] = mapped_column(Time(), nullable=True)
    tarde_inicio: Mapped[time | None] = mapped_column(Time(), nullable=True)
    tarde_fim: Mapped[time | None] = mapped_column(Time(), nullable=True)
