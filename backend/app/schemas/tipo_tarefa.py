from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TipoTarefaStatus = Literal["ativo", "inativo", "arquivado"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# Sem empresaId (vem de current_user) — a API pública nunca aceita. Ver TipoTarefaService.
class TipoTarefaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=5000)
    ordem: int = Field(default=0, ge=0)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class TipoTarefaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=5000)
    ordem: int | None = Field(default=None, ge=0)
    status: Literal["ativo", "inativo"] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# Sem actorUsuarioId (vem de current_user) — só o motivo.
class TipoTarefaArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class TipoTarefaRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    nome: str
    descricao: str | None = None
    ordem: int
    status: TipoTarefaStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: TipoTarefaStatus | None = Field(default=None, alias="statusAnteriorArquivamento")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção mínima pro diretório (GET /tipos-tarefa/diretorio) — só ativo, sem referência
# histórica a resolver aqui, mesmo padrão de WorkflowModeloDiretorioRead (Fase 2G.1): quem já
# referencia um Tipo de Tarefa fora dessa lista resolve pelo nome já denormalizado no próprio
# item do Modelo de Campanha, no frontend.
class TipoTarefaDiretorioRead(BaseModel):
    id: UUID
    nome: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
