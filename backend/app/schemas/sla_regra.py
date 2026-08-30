from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SlaRegraStatus = Literal["ativo", "inativo", "arquivado"]
SlaPrioridadeAlvo = Literal["baixa", "media", "alta"]
SlaUnidadePrazo = Literal["minutos", "horas", "dias_corridos", "dias_uteis"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# Sem empresaId (vem de current_user) — a API pública nunca aceita. Ver SlaRegraService.
# `prioridadeAlvo` ausente/None = "todas as prioridades" (nunca a string "todas" no payload
# nem no banco — ver docstring de app/models/sla_regra.py).
class SlaRegraCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=5000)
    prioridade_alvo: SlaPrioridadeAlvo | None = Field(default=None, alias="prioridadeAlvo")
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    prioridade_regra: int = Field(default=100, alias="prioridadeRegra", ge=1)
    prazo_primeira_resposta_quantidade: int = Field(alias="prazoPrimeiraRespostaQuantidade", gt=0)
    prazo_primeira_resposta_unidade: SlaUnidadePrazo = Field(alias="prazoPrimeiraRespostaUnidade")
    prazo_resolucao_quantidade: int = Field(alias="prazoResolucaoQuantidade", gt=0)
    prazo_resolucao_unidade: SlaUnidadePrazo = Field(alias="prazoResolucaoUnidade")
    considerar_apenas_expediente: bool = Field(default=True, alias="considerarApenasExpediente")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class SlaRegraUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=5000)
    prioridade_alvo: SlaPrioridadeAlvo | None = Field(default=None, alias="prioridadeAlvo")
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    prioridade_regra: int | None = Field(default=None, alias="prioridadeRegra", ge=1)
    prazo_primeira_resposta_quantidade: int | None = Field(
        default=None, alias="prazoPrimeiraRespostaQuantidade", gt=0
    )
    prazo_primeira_resposta_unidade: SlaUnidadePrazo | None = Field(
        default=None, alias="prazoPrimeiraRespostaUnidade"
    )
    prazo_resolucao_quantidade: int | None = Field(default=None, alias="prazoResolucaoQuantidade", gt=0)
    prazo_resolucao_unidade: SlaUnidadePrazo | None = Field(default=None, alias="prazoResolucaoUnidade")
    considerar_apenas_expediente: bool | None = Field(default=None, alias="considerarApenasExpediente")
    # "arquivado" só pela rota dedicada — mesmo padrão de TipoTarefaUpdate/WorkflowModeloUpdate.
    status: Literal["ativo", "inativo"] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# Sem actorUsuarioId (vem de current_user) — só o motivo.
class SlaRegraArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class SlaRegraRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    nome: str
    descricao: str | None = None
    prioridade_alvo: SlaPrioridadeAlvo | None = Field(default=None, alias="prioridadeAlvo")
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    prioridade_regra: int = Field(alias="prioridadeRegra")
    prazo_primeira_resposta_quantidade: int = Field(alias="prazoPrimeiraRespostaQuantidade")
    prazo_primeira_resposta_unidade: SlaUnidadePrazo = Field(alias="prazoPrimeiraRespostaUnidade")
    prazo_resolucao_quantidade: int = Field(alias="prazoResolucaoQuantidade")
    prazo_resolucao_unidade: SlaUnidadePrazo = Field(alias="prazoResolucaoUnidade")
    considerar_apenas_expediente: bool = Field(alias="considerarApenasExpediente")
    status: SlaRegraStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: SlaRegraStatus | None = Field(default=None, alias="statusAnteriorArquivamento")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
