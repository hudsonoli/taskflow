from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    false,
    true,
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
        CheckConstraint(
            "antecedencia_acesso_minutos >= 0 AND antecedencia_acesso_minutos <= 720",
            name="ck_regra_expediente_antecedencia_acesso",
        ),
        CheckConstraint(
            "NOT logout_automatico_ativo OR logout_horario IS NOT NULL",
            name="ck_regra_expediente_logout_exige_horario",
        ),
        CheckConstraint(
            "percentual_capacidade_alocavel >= 1 AND percentual_capacidade_alocavel <= 100",
            name="ck_regra_expediente_percentual_capacidade_alocavel",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False, unique=True)

    # Chave-mestra do controle de expediente — NÃO confundir com `RegraExpedienteDia.ativo`
    # (esse é por dia da semana). `ativo=True` liga o controle: dias/janelas configurados
    # abaixo passam a valer. `ativo=False` desliga o controle inteiro — a operação deixa de
    # ser bloqueada por dia ou horário, independente do que os dias tenham configurado (ver
    # `esta_dentro_expediente` em app/core/expediente.py, semântica oficializada na Fase 2G.3).
    ativo: Mapped[bool] = mapped_column(nullable=False, default=True)

    # LEGADO, semântica antiga PRESERVADA: minutos ANTES do início do 2º período em que a ENTRADA em execução já é aceita (`esta_dentro_expediente`). NÃO é a
    # antecedência de acesso (ver `antecedencia_acesso_minutos`) e não entra no cálculo de SLA nem nas funções de janela de trabalho/acesso.
    tolerancia_retomada_minutos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Fase Expediente 1 — fundação. As duas flags críticas nascem FALSE e AINDA NÃO têm efeito: nenhum gate de acesso, scheduler ou pausa automática as lê
    # (Fases 2/3). `antecedencia_acesso_minutos` é só ANTECEDÊNCIA DE ACESSO (não conta como trabalho).
    bloquear_fora_expediente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    pausar_no_fim_periodo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    antecedencia_acesso_minutos: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default="30")
    # IANA (ex.: America/Sao_Paulo), validado no backend: autoridade do calendário da empresa — nunca o relógio do navegador.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Sao_Paulo", server_default="America/Sao_Paulo")
    feriados_automaticos: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())

    # Fase Expediente 2 — LOGOUT AUTOMÁTICO: horário PRÓPRIO (hora local da empresa, `timezone`), independente do fim do último período, do bloqueio de acesso e da
    # pausa de Demandas (Fase 3). Ligado, tokens emitidos ANTES do último corte (`ultimo_corte_logout`) deixam de valer (401). Nasce desligado.
    logout_automatico_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    logout_horario: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Fase Expediente 3 — instante em que a PAUSA AUTOMÁTICA foi "armada" (flag ligada, controle-mestre religado ou calendário editado com ela ligada). Só cortes
    # POSTERIORES a ele são elegíveis: ligar às 12:15 não pausa retroativamente o corte das 12:00. NULL = nunca armada.
    pausa_automatica_ativada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 11B.2B-A — percentual do expediente NOMINAL disponível para PLANEJAMENTO de tarefas (1..100). NÃO é produtividade nem eficiência de ninguém. Default 100: empresa que nunca
    # configurou não tem a capacidade reduzida em silêncio. Alterá-lo NÃO rearma a pausa automática (não é calendário) — ver `RegraExpedienteService.atualizar`.
    percentual_capacidade_alocavel: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100, server_default="100")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegraExpedienteDia(Base):
    """Um dia da semana de uma RegraExpediente. Sempre exatamente 7 por regra (0..6) — não é
    invariante de banco (não há trigger), é mantido pelo service: `atualizar` substitui o
    conjunto inteiro numa única transação, nunca incrementalmente (mesmo raciocínio de
    `WorkflowModeloService._substituir_etapas`).

    Fase Expediente 1 — OS PERÍODOS VIVEM EM `regra_expediente_periodos` (0, 1, 2 ou mais por dia). `ativo` aqui é DERIVADO (há pelo menos um período) e só é mantido
    por compatibilidade; `manha_*`/`tarde_*` são LEGADO: espelho dos dois períodos quando o dia tem exatamente dois, `NULL` caso contrário. O cálculo NÃO as lê
    mais; saem numa fase futura. O CHECK antigo (quatro horários obrigatórios em dia ativo) foi removido pela migration 0047.
    """

    __tablename__ = "regra_expediente_dias"
    __table_args__ = (
        CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="ck_regra_expediente_dias_dia_semana"),
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


class RegraExpedientePeriodo(Base):
    """Um período de trabalho de um dia da semana (Fase Expediente 1). 0 períodos = dia fechado; 1 ou mais = dia útil. Sem sobreposição dentro do dia (validado
    no schema/service — o Postgres não tem constraint de intervalo sem extensão) e SEM virar a meia-noite (início < fim, V1). Fim exclusivo: `08:00–12:00` inclui
    08:00:00 e exclui 12:00:00."""

    __tablename__ = "regra_expediente_periodos"
    __table_args__ = (
        CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="ck_regra_expediente_periodos_dia_semana"),
        CheckConstraint("ordem >= 1", name="ck_regra_expediente_periodos_ordem"),
        CheckConstraint("inicio < fim", name="ck_regra_expediente_periodos_inicio_fim"),
        UniqueConstraint("regra_expediente_id", "dia_semana", "ordem", name="uq_regra_expediente_periodos_regra_dia_ordem"),
        Index("ix_regra_expediente_periodos_regra_id", "regra_expediente_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    regra_expediente_id: Mapped[str] = mapped_column(ForeignKey("regra_expediente.id", ondelete="CASCADE"), nullable=False)
    dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ordem: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    inicio: Mapped[time] = mapped_column(Time(), nullable=False)
    fim: Mapped[time] = mapped_column(Time(), nullable=False)


class RegraExpedienteDiaEspecial(Base):
    """Dia especial do calendário da empresa (feriado, recesso, dia excepcional de trabalho ou "ignorado"). Fase Expediente 1: só modelo e cadastro MANUAL — a
    importação automática (BrasilAPI) é de outra fase, e o calendário nunca é buscado fora do banco.

    - `feriado`/`recesso` ATIVOS → o dia fica FECHADO; `trabalho_excepcional` ATIVO → usa os períodos de `regra_expediente_dias_especiais_periodos` no lugar dos da
      semana; `ignorado` ATIVO → NEUTRALIZA a data (nenhum efeito próprio: vale a regra semanal, mesmo que exista um feriado automático nela). `ativo=False`
      desliga a linha.
    - Precedência (ver `app.core.expediente.resolver_dia_especial`): dia especial vence a regra semanal; numa mesma data a decisão MANUAL ativa vence a
      AUTOMÁTICA. Uma linha por (regra, data, origem).
    """

    __tablename__ = "regra_expediente_dias_especiais"
    __table_args__ = (
        CheckConstraint("origem IN ('automatico', 'manual')", name="ck_regra_expediente_dias_especiais_origem"),
        CheckConstraint(
            "tipo IN ('feriado', 'recesso', 'trabalho_excepcional', 'ignorado')", name="ck_regra_expediente_dias_especiais_tipo"
        ),
        UniqueConstraint("regra_expediente_id", "data", "origem", name="uq_regra_expediente_dias_especiais_regra_data_origem"),
        Index("ix_regra_expediente_dias_especiais_regra_data", "regra_expediente_id", "data"),
        Index("ix_regra_expediente_dias_especiais_empresa_id", "empresa_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    regra_expediente_id: Mapped[str] = mapped_column(ForeignKey("regra_expediente.id", ondelete="CASCADE"), nullable=False)
    data: Mapped[date] = mapped_column(Date(), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    origem: Mapped[str] = mapped_column(String(16), nullable=False)
    tipo: Mapped[str] = mapped_column(String(24), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegraExpedienteDiaEspecialPeriodo(Base):
    """Períodos próprios de um dia `trabalho_excepcional` (mesma forma de `RegraExpedientePeriodo`, sem dia da semana)."""

    __tablename__ = "regra_expediente_dias_especiais_periodos"
    __table_args__ = (
        CheckConstraint("ordem >= 1", name="ck_regra_expediente_dias_especiais_periodos_ordem"),
        CheckConstraint("inicio < fim", name="ck_regra_expediente_dias_especiais_periodos_inicio_fim"),
        UniqueConstraint("dia_especial_id", "ordem", name="uq_regra_expediente_dias_especiais_periodos_dia_ordem"),
        Index("ix_regra_expediente_dias_especiais_periodos_dia_id", "dia_especial_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dia_especial_id: Mapped[str] = mapped_column(
        ForeignKey("regra_expediente_dias_especiais.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    inicio: Mapped[time] = mapped_column(Time(), nullable=False)
    fim: Mapped[time] = mapped_column(Time(), nullable=False)
