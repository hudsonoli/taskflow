from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

UsuarioCargoStatus = Literal["ativo", "inativo"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class UsuarioCargoCreate(BaseModel):
    empresa_id: UUID = Field(alias="empresaId")
    usuario_id: UUID = Field(alias="usuarioId")
    cargo_id: UUID = Field(alias="cargoId")
    principal: bool = False

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class UsuarioCargoUpdate(BaseModel):
    principal: bool | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class UsuarioCargoEncerrar(BaseModel):
    motivo_encerramento: str | None = Field(default=None, alias="motivoEncerramento", max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class UsuarioCargoResponse(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    usuario_id: UUID = Field(alias="usuarioId")
    cargo_id: UUID = Field(alias="cargoId")
    principal: bool
    status: UsuarioCargoStatus
    inicio_em: datetime = Field(alias="inicioEm")
    fim_em: datetime | None = Field(default=None, alias="fimEm")
    motivo_encerramento: str | None = Field(default=None, alias="motivoEncerramento")
    criado_por_usuario_id: str | None = Field(default=None, alias="criadoPorUsuarioId")
    encerrado_por_usuario_id: str | None = Field(default=None, alias="encerradoPorUsuarioId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("inicio_em", "fim_em", "created_at", "updated_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
