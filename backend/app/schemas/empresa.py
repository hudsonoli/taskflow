from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.empresa_slug import validar_slug

EmpresaStatus = Literal["ativa", "inativa", "arquivada"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalizar_codigo(valor: str | None) -> str | None:
    """`codigo_interno` é o código de login de hoje e o login o normaliza com `.upper()`: guardar já em maiúsculas,
    sem espaços, é o que mantém a empresa alcançável."""
    if valor is None:
        return None
    codigo = valor.strip().upper()
    if not codigo or not all(c.isalnum() or c in "-_" for c in codigo):
        raise ValueError("O código interno aceita só letras, números, hífen e sublinhado.")
    return codigo


def _normalizar_slug(valor: str | None) -> str | None:
    return None if valor is None else validar_slug(valor)


class EmpresaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    # Opcional. Quando ausente, nenhuma "fantasia" é inventada.
    nome_fantasia: str | None = Field(default=None, alias="nomeFantasia", max_length=255)
    documento: str | None = Field(default=None, max_length=32)
    codigo_interno: str = Field(alias="codigoInterno", min_length=1, max_length=64)
    # Opcional: sem slug, o service deriva um (válido e livre) do `codigo_interno`.
    slug: str | None = Field(default=None)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("codigo_interno")
    @classmethod
    def _codigo(cls, value: str) -> str:
        return _normalizar_codigo(value)  # type: ignore[return-value]

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        return _normalizar_slug(value)


class EmpresaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    nome_fantasia: str | None = Field(default=None, alias="nomeFantasia", max_length=255)
    documento: str | None = Field(default=None, max_length=32)
    codigo_interno: str | None = Field(default=None, alias="codigoInterno", min_length=1, max_length=64)
    slug: str | None = Field(default=None)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("codigo_interno")
    @classmethod
    def _codigo(cls, value: str | None) -> str | None:
        return _normalizar_codigo(value)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        return _normalizar_slug(value)


class EmpresaInativar(BaseModel):
    motivo_inativacao: str | None = Field(default=None, alias="motivoInativacao", max_length=500)
    actor_usuario_id: str | None = Field(default=None, alias="actorUsuarioId", max_length=128)

    model_config = ConfigDict(populate_by_name=True)


class EmpresaRead(BaseModel):
    id: UUID
    nome: str
    nome_fantasia: str | None = Field(default=None, alias="nomeFantasia")
    documento: str | None = None
    codigo_interno: str = Field(alias="codigoInterno")
    slug: str
    status: EmpresaStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    inativado_at: datetime | None = Field(default=None, alias="inativadoAt")
    inativado_por_usuario_id: str | None = Field(default=None, alias="inativadoPorUsuarioId")
    motivo_inativacao: str | None = Field(default=None, alias="motivoInativacao")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "inativado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
