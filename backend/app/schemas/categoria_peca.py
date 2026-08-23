from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CategoriaPecaStatus = Literal["ativo", "arquivado"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# Sem empresaId (vem de current_user) — a API pública nunca aceita.
class CategoriaPecaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    ordem: int = Field(default=0, ge=0)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CategoriaPecaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    ordem: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CategoriaPecaArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CategoriaPecaRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    nome: str
    ordem: int
    status: CategoriaPecaStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção mínima pro diretório (GET /categorias-peca/diretorio) — só ativo, mesmo padrão de
# TipoTarefaDiretorioRead: quem já referencia uma Categoria arquivada resolve pelo nome já
# denormalizado no próprio registro de Peça (categoriaNome, ver PecaRead), não por aqui.
class CategoriaPecaDiretorioRead(BaseModel):
    id: UUID
    nome: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
