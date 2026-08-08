from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

EquipeStatus = Literal["ativo", "inativo", "arquivado"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# `extra="forbid"`: empresaId, actorUsuarioId, codigoInterno, codigoReferencia,
# anoReferencia e sequencialReferencia no payload devolvem 422 — não são ignorados.
class EquipeCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    cor_identificacao: str = Field(alias="corIdentificacao", min_length=1, max_length=32)
    descricao: str | None = Field(default=None, max_length=2000)
    # Ausente/nulo = equipe transversal (legítimo, não é dado faltando).
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    lider_usuario_id: UUID | None = Field(default=None, alias="liderUsuarioId")
    membro_ids: list[UUID] = Field(default_factory=list, alias="membroIds")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class EquipeUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    cor_identificacao: str | None = Field(default=None, alias="corIdentificacao", min_length=1, max_length=32)
    descricao: str | None = Field(default=None, max_length=2000)
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    lider_usuario_id: UUID | None = Field(default=None, alias="liderUsuarioId")
    # Lista COMPLETA de membros (o formulário edita o conjunto inteiro). O service calcula
    # a diferença e só publica evento para mudança real.
    membro_ids: list[UUID] | None = Field(default=None, alias="membroIds")
    status: Literal["ativo", "inativo"] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class EquipeArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class EquipeRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    ano_referencia: int = Field(alias="anoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    descricao: str | None = None
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    lider_usuario_id: UUID | None = Field(default=None, alias="liderUsuarioId")
    membro_ids: list[UUID] = Field(default_factory=list, alias="membroIds")
    cor_identificacao: str = Field(alias="corIdentificacao")
    status: EquipeStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: EquipeStatus | None = Field(default=None, alias="statusAnteriorArquivamento")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Inclui arquivadas (resolução histórica) e expõe `status` para a UI decidir o que oferecer.
class EquipeDiretorioRead(BaseModel):
    id: UUID
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    cor_identificacao: str = Field(alias="corIdentificacao")
    status: EquipeStatus
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    # Necessário para o escopo "minha equipe" nas telas operacionais (Meu Departamento,
    # Central de Tráfego) — evita uma segunda chamada só para saber a composição.
    membro_ids: list[UUID] = Field(default_factory=list, alias="membroIds")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
