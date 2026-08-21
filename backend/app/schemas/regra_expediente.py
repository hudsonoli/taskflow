from datetime import datetime, time, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DIAS_SEMANA_VALIDOS = frozenset(range(7))  # 0=segunda .. 6=domingo (datetime.weekday())


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class JanelaDiaWrite(BaseModel):
    dia_semana: int = Field(alias="diaSemana", ge=0, le=6)
    ativo: bool
    manha_inicio: time | None = Field(default=None, alias="manhaInicio")
    manha_fim: time | None = Field(default=None, alias="manhaFim")
    tarde_inicio: time | None = Field(default=None, alias="tardeInicio")
    tarde_fim: time | None = Field(default=None, alias="tardeFim")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def validar_janela(self) -> "JanelaDiaWrite":
        if not self.ativo:
            return self
        if None in (self.manha_inicio, self.manha_fim, self.tarde_inicio, self.tarde_fim):
            raise ValueError(f"dia {self.dia_semana} ativo precisa das quatro janelas preenchidas")
        if self.manha_inicio >= self.manha_fim:
            raise ValueError(f"dia {self.dia_semana}: manhaInicio precisa ser antes de manhaFim")
        if self.tarde_inicio >= self.tarde_fim:
            raise ValueError(f"dia {self.dia_semana}: tardeInicio precisa ser antes de tardeFim")
        if self.manha_fim > self.tarde_inicio:
            raise ValueError(f"dia {self.dia_semana}: manhã não pode terminar depois da tarde começar")
        return self


class RegraExpedienteUpdate(BaseModel):
    # Chave-mestra: True liga o controle de expediente (dias/janelas abaixo passam a valer);
    # False desliga — operação não é mais bloqueada por dia ou horário nenhum. Não confundir
    # com `JanelaDiaWrite.ativo`, que é por dia da semana.
    ativo: bool | None = None
    tolerancia_retomada_minutos: int | None = Field(default=None, alias="toleranciaRetomadaMinutos", ge=0)
    # Full-replace: quando enviado, precisa vir com os 7 dias — mesmo raciocínio de
    # WorkflowModeloUpdate.etapas (o form sempre edita o conjunto inteiro de uma vez).
    dias: list[JanelaDiaWrite] | None = Field(default=None)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

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


class JanelaDiaRead(BaseModel):
    dia_semana: int = Field(alias="diaSemana")
    ativo: bool
    manha_inicio: time | None = Field(default=None, alias="manhaInicio")
    manha_fim: time | None = Field(default=None, alias="manhaFim")
    tarde_inicio: time | None = Field(default=None, alias="tardeInicio")
    tarde_fim: time | None = Field(default=None, alias="tardeFim")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RegraExpedienteRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    ativo: bool  # ver comentário em RegraExpedienteUpdate.ativo — chave-mestra, não por dia
    tolerancia_retomada_minutos: int = Field(alias="toleranciaRetomadaMinutos")
    dias: list[JanelaDiaRead]
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
    # Duração (manhã+tarde) do dia de hoje, em horas — 0 se hoje não for dia útil. Só para
    # estimativa de capacidade (ver capacidadeAproximada no frontend); nunca os horários.
    horas_uteis_hoje: float = Field(alias="horasUteisHoje")

    model_config = ConfigDict(populate_by_name=True)
