from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SessaoTrabalhoStatus = Literal["ativa", "encerrada", "cancelada"]
MotivoEncerramento = Literal[
    "pausa",
    "bloqueio",
    "aguardando_cliente",
    "mudanca_etapa",
    "conclusao",
    "cancelamento",
    "troca_responsavel",
    "substituicao_sessao_ativa",
]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class SessaoTrabalhoRead(BaseModel):
    id: UUID
    empresa_id: str = Field(alias="empresaId")
    agencia_id: str | None = Field(default=None, alias="agenciaId")
    demanda_id: str = Field(alias="demandaId")
    workflow_etapa_id: str | None = Field(default=None, alias="workflowEtapaId")
    usuario_id: str | None = Field(default=None, alias="usuarioId")
    departamento_id: str | None = Field(default=None, alias="departamentoId")
    evento_inicio_id: UUID = Field(alias="eventoInicioId")
    evento_fim_id: UUID | None = Field(default=None, alias="eventoFimId")
    status: SessaoTrabalhoStatus
    inicio_em: datetime = Field(alias="inicioEm")
    fim_em: datetime | None = Field(default=None, alias="fimEm")
    duracao_segundos: int | None = Field(default=None, alias="duracaoSegundos")
    motivo_encerramento: MotivoEncerramento | None = Field(default=None, alias="motivoEncerramento")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("inicio_em", "fim_em", "created_at", "updated_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
