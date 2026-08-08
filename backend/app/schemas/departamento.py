from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

DepartamentoStatus = Literal["ativo", "inativo", "arquivado"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# `extra="forbid"` é deliberado: enviar empresaId, actorUsuarioId, codigoInterno,
# codigoReferencia, anoReferencia ou sequencialReferencia devolve 422 em vez de ser
# ignorado em silêncio. Empresa e ator vêm de current_user; os códigos são gerados no
# backend (ver app/core/referencias.py).
class DepartamentoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    cor_identificacao: str = Field(alias="corIdentificacao", min_length=1, max_length=32)
    descricao: str | None = Field(default=None, max_length=2000)
    responsavel_usuario_id: UUID | None = Field(default=None, alias="responsavelUsuarioId")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DepartamentoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    cor_identificacao: str | None = Field(default=None, alias="corIdentificacao", min_length=1, max_length=32)
    descricao: str | None = Field(default=None, max_length=2000)
    responsavel_usuario_id: UUID | None = Field(default=None, alias="responsavelUsuarioId")
    status: Literal["ativo", "inativo"] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DepartamentoArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DepartamentoRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    ano_referencia: int = Field(alias="anoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    descricao: str | None = None
    responsavel_usuario_id: UUID | None = Field(default=None, alias="responsavelUsuarioId")
    cor_identificacao: str = Field(alias="corIdentificacao")
    status: DepartamentoStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: DepartamentoStatus | None = Field(
        default=None, alias="statusAnteriorArquivamento"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção mínima para seletores. Inclui arquivados de propósito (resolução histórica de
# referências antigas) e expõe `status` para a UI decidir o que oferecer como opção nova.
class DepartamentoDiretorioRead(BaseModel):
    id: UUID
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    cor_identificacao: str = Field(alias="corIdentificacao")
    status: DepartamentoStatus
    # Necessário para resolver "head de departamento" no frontend (escopo-operacional.ts).
    responsavel_usuario_id: UUID | None = Field(default=None, alias="responsavelUsuarioId")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
