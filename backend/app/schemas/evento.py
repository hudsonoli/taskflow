from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventoBase(BaseModel):
    empresa_id: str = Field(alias="empresaId", min_length=1, max_length=128)
    agencia_id: str | None = Field(default=None, alias="agenciaId", max_length=128)
    tipo: str = Field(min_length=1, max_length=128)
    entidade_tipo: str = Field(alias="entidadeTipo", min_length=1, max_length=128)
    entidade_id: str = Field(alias="entidadeId", min_length=1, max_length=128)
    usuario_id: str | None = Field(default=None, alias="usuarioId", max_length=128)
    correlation_id: UUID | None = Field(default=None, alias="correlationId")
    causation_id: UUID | None = Field(default=None, alias="causationId")
    payload: dict[str, Any]
    metadata: dict[str, Any] | None = None
    occurred_at: datetime | None = Field(default=None, alias="occurredAt")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("occurred_at")
    @classmethod
    def ensure_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("occurredAt deve incluir timezone")
        return value.astimezone(timezone.utc)


class EventoCreate(EventoBase):
    pass


class EventoRead(EventoBase):
    id: UUID
    occurred_at: datetime = Field(alias="occurredAt")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
