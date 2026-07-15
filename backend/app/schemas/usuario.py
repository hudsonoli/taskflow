from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

UsuarioPerfilBase = Literal["admin", "gestor", "operador"]
UsuarioStatus = Literal["ativo", "inativo", "bloqueado", "arquivado"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class UsuarioCreate(BaseModel):
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno", min_length=1, max_length=64)
    nome: str = Field(min_length=1, max_length=255)
    # A normalização de e-mail antes de persistir será responsabilidade do service na Etapa 2.
    email: str = Field(min_length=1, max_length=255)
    perfil_base: UsuarioPerfilBase = Field(alias="perfilBase")
    acesso_sistema: bool = Field(default=True, alias="acessoSistema")

    model_config = ConfigDict(populate_by_name=True)


class UsuarioUpdate(BaseModel):
    codigo_interno: str | None = Field(default=None, alias="codigoInterno", min_length=1, max_length=64)
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=1, max_length=255)
    perfil_base: UsuarioPerfilBase | None = Field(default=None, alias="perfilBase")
    acesso_sistema: bool | None = Field(default=None, alias="acessoSistema")

    model_config = ConfigDict(populate_by_name=True)


class UsuarioInativar(BaseModel):
    motivo_inativacao: str | None = Field(default=None, alias="motivoInativacao", max_length=500)
    actor_usuario_id: str | None = Field(default=None, alias="actorUsuarioId", max_length=36)

    model_config = ConfigDict(populate_by_name=True)


class UsuarioRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    nome: str
    email: str
    perfil_base: UsuarioPerfilBase = Field(alias="perfilBase")
    acesso_sistema: bool = Field(alias="acessoSistema")
    status: UsuarioStatus
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
