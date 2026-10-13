from datetime import date, datetime, time, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DIAS_SEMANA_VALIDOS = frozenset(range(7))  # 0=segunda .. 6=domingo (datetime.weekday())
MAX_PERIODOS_POR_DIA = 8
TIPOS_DIA_ESPECIAL_ESCRITA = ("feriado", "recesso", "trabalho_excepcional", "ignorado")

# As três flags abaixo EXISTEM mas ainda não têm efeito: não há gate de acesso, scheduler nem sincronização de feriados (Fases 2/3 e posteriores). Até lá a API recusa
# LIGÁ-LAS — assim nenhuma empresa fica "armada" antes de o mecanismo existir (desligar sempre pode).
_MENSAGEM_PROXIMA_ETAPA = "ainda não está disponível: será ativado em uma próxima etapa"


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validar_fuso_iana(valor: str) -> str:
    limpo = valor.strip()
    try:
        ZoneInfo(limpo)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"timezone inválido (use um nome IANA, ex.: America/Sao_Paulo): {valor!r}") from exc
    return limpo


class PeriodoWrite(BaseModel):
    inicio: time
    fim: time

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("inicio", "fim")
    @classmethod
    def sem_segundos(cls, value: time) -> time:
        return value.replace(second=0, microsecond=0, tzinfo=None)

    @model_validator(mode="after")
    def inicio_antes_do_fim(self) -> "PeriodoWrite":
        if self.inicio >= self.fim:
            raise ValueError("o período precisa começar antes de terminar (não atravessa a meia-noite nesta versão)")
        return self


def normalizar_periodos(periodos: list[PeriodoWrite], rotulo: str) -> list[PeriodoWrite]:
    """Ordena pelo início, recusa sobreposição (períodos que apenas se tocam — fim == início do próximo — são aceitos) e limita a quantidade."""
    if len(periodos) > MAX_PERIODOS_POR_DIA:
        raise ValueError(f"{rotulo}: no máximo {MAX_PERIODOS_POR_DIA} períodos")
    ordenados = sorted(periodos, key=lambda periodo: (periodo.inicio, periodo.fim))
    for anterior, atual in zip(ordenados, ordenados[1:]):
        if atual.inicio < anterior.fim:
            raise ValueError(f"{rotulo}: os períodos {anterior.inicio:%H:%M}–{anterior.fim:%H:%M} e {atual.inicio:%H:%M}–{atual.fim:%H:%M} se sobrepõem")
    return ordenados


class JanelaDiaWrite(BaseModel):
    """Um dia da semana. Forma NOVA: `periodos` (lista vazia = dia FECHADO). Forma LEGADA (ainda aceita): `ativo` + `manhaInicio/manhaFim/tardeInicio/tardeFim`,
    convertida em períodos. Depois da validação, `periodos` é a lista ordenada e `ativo` é derivado (há pelo menos um período)."""

    dia_semana: int = Field(alias="diaSemana", ge=0, le=6)
    ativo: bool | None = None
    periodos: list[PeriodoWrite] | None = None
    manha_inicio: time | None = Field(default=None, alias="manhaInicio")
    manha_fim: time | None = Field(default=None, alias="manhaFim")
    tarde_inicio: time | None = Field(default=None, alias="tardeInicio")
    tarde_fim: time | None = Field(default=None, alias="tardeFim")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def validar_janela(self) -> "JanelaDiaWrite":
        rotulo = f"dia {self.dia_semana}"
        legado = (self.manha_inicio, self.manha_fim, self.tarde_inicio, self.tarde_fim)
        if self.periodos is not None:
            if any(valor is not None for valor in legado):
                raise ValueError(f"{rotulo}: envie `periodos` OU os campos legados manha/tarde, não os dois")
            periodos = self.periodos
            if self.ativo is False and periodos:
                raise ValueError(f"{rotulo}: ativo=false não combina com períodos preenchidos")
        elif self.ativo is None:
            raise ValueError(f"{rotulo}: informe `periodos` (lista vazia = dia fechado)")
        elif not self.ativo:
            periodos = []
        else:
            if None in legado:
                raise ValueError(f"{rotulo} ativo precisa das quatro janelas preenchidas")
            periodos = [PeriodoWrite(inicio=self.manha_inicio, fim=self.manha_fim), PeriodoWrite(inicio=self.tarde_inicio, fim=self.tarde_fim)]
        self.periodos = normalizar_periodos(periodos, rotulo)
        self.ativo = bool(self.periodos)
        self.manha_inicio = self.manha_fim = self.tarde_inicio = self.tarde_fim = None
        return self


class RegraExpedienteUpdate(BaseModel):
    # Chave-mestra: True liga o controle de expediente (dias/janelas abaixo passam a valer);
    # False desliga — operação não é mais bloqueada por dia ou horário nenhum. Não confundir
    # com `JanelaDiaWrite.ativo`, que é por dia da semana.
    ativo: bool | None = None
    # LEGADO: tolerância de ENTRADA em execução antes do 2º período (semântica antiga preservada). Não é a antecedência de acesso.
    tolerancia_retomada_minutos: int | None = Field(default=None, alias="toleranciaRetomadaMinutos", ge=0)
    bloquear_fora_expediente: bool | None = Field(default=None, alias="bloquearForaExpediente")
    pausar_no_fim_periodo: bool | None = Field(default=None, alias="pausarNoFimPeriodo")
    antecedencia_acesso_minutos: int | None = Field(default=None, alias="antecedenciaAcessoMinutos", ge=0, le=720)
    timezone: str | None = Field(default=None, max_length=64)
    feriados_automaticos: bool | None = Field(default=None, alias="feriadosAutomaticos")
    # Full-replace: quando enviado, precisa vir com os 7 dias — mesmo raciocínio de
    # WorkflowModeloUpdate.etapas (o form sempre edita o conjunto inteiro de uma vez).
    dias: list[JanelaDiaWrite] | None = Field(default=None)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("timezone")
    @classmethod
    def fuso_valido(cls, value: str | None) -> str | None:
        return None if value is None else validar_fuso_iana(value)

    @field_validator("bloquear_fora_expediente", "pausar_no_fim_periodo", "feriados_automaticos")
    @classmethod
    def so_desligar_por_enquanto(cls, value: bool | None, info) -> bool | None:
        if value:
            raise ValueError(f"{info.field_name} {_MENSAGEM_PROXIMA_ETAPA}")
        return value

    @field_validator("dias")
    @classmethod
    def validar_dias_completos(cls, value: list[JanelaDiaWrite] | None) -> list[JanelaDiaWrite] | None:
        if value is None:
            return value
        dias_informados = {dia.dia_semana for dia in value}
        if dias_informados != DIAS_SEMANA_VALIDOS:
            faltando = sorted(DIAS_SEMANA_VALIDOS - dias_informados)
            repetidos = len(value) != len(dias_informados)
            if repetidos:
                raise ValueError("dias não pode repetir diaSemana")
            raise ValueError(f"dias precisa cobrir os 7 dias da semana (faltando: {faltando})")
        return value


class PeriodoRead(BaseModel):
    inicio: time
    fim: time

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class JanelaDiaRead(BaseModel):
    dia_semana: int = Field(alias="diaSemana")
    ativo: bool
    periodos: list[PeriodoRead] = Field(default_factory=list)
    # LEGADO (espelho, só para consumidores antigos): primeiro e último período quando há 2 ou mais. A fonte é `periodos`.
    manha_inicio: time | None = Field(default=None, alias="manhaInicio")
    manha_fim: time | None = Field(default=None, alias="manhaFim")
    tarde_inicio: time | None = Field(default=None, alias="tardeInicio")
    tarde_fim: time | None = Field(default=None, alias="tardeFim")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DiaEspecialWrite(BaseModel):
    """Cadastro MANUAL de dia especial. `periodos` só vale (e é obrigatório) para `trabalho_excepcional`."""

    data: date
    nome: str = Field(min_length=1, max_length=120)
    tipo: str
    ativo: bool = True
    periodos: list[PeriodoWrite] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, value: str) -> str:
        limpo = value.strip()
        if not limpo:
            raise ValueError("nome não pode conter apenas espaços")
        return limpo

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, value: str) -> str:
        if value not in TIPOS_DIA_ESPECIAL_ESCRITA:
            raise ValueError(f"tipo inválido (use um de {', '.join(TIPOS_DIA_ESPECIAL_ESCRITA)})")
        return value

    @model_validator(mode="after")
    def validar_periodos(self) -> "DiaEspecialWrite":
        if self.tipo == "trabalho_excepcional":
            if not self.periodos:
                raise ValueError("trabalho_excepcional precisa de pelo menos um período")
            self.periodos = normalizar_periodos(self.periodos, "dia especial")
        elif self.periodos:
            raise ValueError(f"o tipo {self.tipo} não usa períodos")
        return self


class DiaEspecialUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    tipo: str | None = None
    ativo: bool | None = None
    periodos: list[PeriodoWrite] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, value: str | None) -> str | None:
        if value is None:
            return None
        limpo = value.strip()
        if not limpo:
            raise ValueError("nome não pode conter apenas espaços")
        return limpo

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, value: str | None) -> str | None:
        if value is not None and value not in TIPOS_DIA_ESPECIAL_ESCRITA:
            raise ValueError(f"tipo inválido (use um de {', '.join(TIPOS_DIA_ESPECIAL_ESCRITA)})")
        return value


class DiaEspecialRead(BaseModel):
    id: UUID
    data: date
    nome: str
    origem: str
    tipo: str
    ativo: bool
    periodos: list[PeriodoRead] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)


class RegraExpedienteRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    ativo: bool  # ver comentário em RegraExpedienteUpdate.ativo — chave-mestra, não por dia
    tolerancia_retomada_minutos: int = Field(alias="toleranciaRetomadaMinutos")
    bloquear_fora_expediente: bool = Field(alias="bloquearForaExpediente")
    pausar_no_fim_periodo: bool = Field(alias="pausarNoFimPeriodo")
    antecedencia_acesso_minutos: int = Field(alias="antecedenciaAcessoMinutos")
    timezone: str
    feriados_automaticos: bool = Field(alias="feriadosAutomaticos")
    dias: list[JanelaDiaRead]
    dias_especiais: list[DiaEspecialRead] = Field(default_factory=list, alias="diasEspeciais")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)


# GET /expediente/estado — leitura operacional enxuta, aberta a qualquer autenticado (ver
# app/api/routes/expediente.py). Nunca expõe as janelas por dia (isso é admin/gestor, em
# GET /regra-expediente) — `ativo` e `horasUteisHoje` são agregados de baixa sensibilidade,
# não os horários em si.
class EstadoExpedienteRead(BaseModel):
    # False = controle de expediente desligado: `dentroExpediente` vem sempre True (gate
    # liberado, nenhuma tela deve bloquear operação por dia/horário — ver RegraExpedienteUpdate.ativo).
    ativo: bool
    dentro_expediente: bool = Field(alias="dentroExpediente")
    agora: datetime
    tolerancia_retomada_minutos: int = Field(alias="toleranciaRetomadaMinutos")
    # Duração (soma dos períodos) do dia de hoje, em horas — 0 se hoje não for dia útil. Só para
    # estimativa de capacidade (ver capacidadeAproximada no frontend); nunca os horários.
    horas_uteis_hoje: float = Field(alias="horasUteisHoje")

    model_config = ConfigDict(populate_by_name=True)
