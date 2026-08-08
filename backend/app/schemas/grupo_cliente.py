from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

GrupoClienteStatus = Literal["ativo", "arquivado"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# Sem empresaId (vem de current_user) e sem codigoInterno (gerado internamente) — a API
# pública nunca aceita nenhum dos dois. Ver GrupoClienteService.create_grupo_cliente.
class GrupoClienteCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    cor_identificacao: str = Field(alias="corIdentificacao", min_length=1, max_length=32)

    model_config = ConfigDict(populate_by_name=True)


class GrupoClienteUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    cor_identificacao: str | None = Field(default=None, alias="corIdentificacao", min_length=1, max_length=32)

    model_config = ConfigDict(populate_by_name=True)


# Sem actorUsuarioId (vem de current_user) — só o motivo.
class GrupoClienteArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True)


class GrupoClienteRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    nome: str
    cor_identificacao: str = Field(alias="corIdentificacao")
    status: GrupoClienteStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: GrupoClienteStatus | None = Field(default=None, alias="statusAnteriorArquivamento")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção mínima pro diretório (GET /grupos-cliente/diretorio) — inclui arquivados de
# propósito (resolução histórica de Cliente.tagIds antigos), por isso expõe `status`: a UI
# decide o que oferecer como opção nova (só ativo) vs. o que só exibir (arquivado, com
# indicador visual).
class GrupoClienteDiretorioRead(BaseModel):
    id: UUID
    codigo_interno: str = Field(alias="codigoInterno")
    nome: str
    cor_identificacao: str = Field(alias="corIdentificacao")
    status: GrupoClienteStatus

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
