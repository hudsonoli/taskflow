from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _texto_nao_pode_ser_so_espaco(value: str) -> str:
    limpo = value.strip()
    if not limpo:
        raise ValueError("texto não pode conter apenas espaços")
    return limpo


class DemandaComentarioCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("texto")
    @classmethod
    def texto_valido(cls, value: str) -> str:
        return _texto_nao_pode_ser_so_espaco(value)


class DemandaComentarioUpdate(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("texto")
    @classmethod
    def texto_valido(cls, value: str) -> str:
        return _texto_nao_pode_ser_so_espaco(value)


class DemandaComentarioRead(BaseModel):
    id: UUID
    demanda_id: UUID = Field(alias="demandaId")
    autor_usuario_id: UUID | None = Field(default=None, alias="autorUsuarioId")
    texto: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    editado_em: datetime | None = Field(default=None, alias="editadoEm")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "editado_em")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
