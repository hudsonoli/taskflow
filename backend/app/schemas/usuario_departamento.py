from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

UsuarioDepartamentoPapel = Literal["membro", "gestor", "head"]
UsuarioDepartamentoStatus = Literal["ativo", "inativo"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def require_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("datetime deve incluir timezone")
    return value.astimezone(timezone.utc)


class UsuarioDepartamentoCreate(BaseModel):
    empresa_id: UUID = Field(alias="empresaId")
    usuario_id: UUID = Field(alias="usuarioId")
    departamento_id: UUID = Field(alias="departamentoId")
    papel: UsuarioDepartamentoPapel
    principal: bool = False
    inicio_em: datetime = Field(alias="inicioEm")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("inicio_em")
    @classmethod
    def validate_inicio_em_timezone(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)


class UsuarioDepartamentoUpdate(BaseModel):
    papel: UsuarioDepartamentoPapel | None = None
    principal: bool | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class UsuarioDepartamentoEncerrar(BaseModel):
    fim_em: datetime = Field(alias="fimEm")
    motivo_encerramento: str | None = Field(default=None, alias="motivoEncerramento", max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("fim_em")
    @classmethod
    def validate_fim_em_timezone(cls, value: datetime) -> datetime:
        return require_timezone_aware(value)


class UsuarioDepartamentoResponse(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    usuario_id: UUID = Field(alias="usuarioId")
    departamento_id: UUID = Field(alias="departamentoId")
    papel: UsuarioDepartamentoPapel
    principal: bool
    status: UsuarioDepartamentoStatus
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
