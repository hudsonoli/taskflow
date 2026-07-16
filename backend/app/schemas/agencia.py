from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AgenciaStatus = Literal["ativa", "inativa", "arquivada"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class AgenciaCreate(BaseModel):
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno", min_length=1, max_length=64)
    nome: str = Field(min_length=1, max_length=255)
    sigla: str = Field(min_length=1, max_length=32)
    descricao: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(populate_by_name=True)


class AgenciaUpdate(BaseModel):
    codigo_interno: str | None = Field(default=None, alias="codigoInterno", min_length=1, max_length=64)
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    sigla: str | None = Field(default=None, min_length=1, max_length=32)
    descricao: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(populate_by_name=True)


class AgenciaInativar(BaseModel):
    motivo_inativacao: str | None = Field(default=None, alias="motivoInativacao", max_length=500)
    actor_usuario_id: str | None = Field(default=None, alias="actorUsuarioId", max_length=36)

    model_config = ConfigDict(populate_by_name=True)


class AgenciaResponse(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    nome: str
    sigla: str
    descricao: str | None = None
    status: AgenciaStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    inativado_at: datetime | None = Field(default=None, alias="inativadoAt")
    motivo_inativacao: str | None = Field(default=None, alias="motivoInativacao")
    inativado_por_usuario_id: str | None = Field(default=None, alias="inativadoPorUsuarioId")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "inativado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
