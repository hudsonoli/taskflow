from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

WorkflowModeloStatus = Literal["ativo", "inativo", "arquivado"]
WorkflowEtapaTipo = Literal["execucao", "aprovacao"]
WorkflowUnidadePrazo = Literal["dias_corridos", "dias_uteis", "horas"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class WorkflowModeloEtapaWrite(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    tipo: WorkflowEtapaTipo
    quantidade_antes_deadline: int = Field(alias="quantidadeAntesDeadline", ge=0)
    unidade_prazo: WorkflowUnidadePrazo = Field(alias="unidadePrazo")
    usuario_responsavel_ids: list[UUID] = Field(default_factory=list, alias="usuarioResponsavelIds")
    departamento_responsavel_ids: list[UUID] = Field(
        default_factory=list, alias="departamentoResponsavelIds"
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# `extra="forbid"` é deliberado, como em departamento.py: enviar empresaId, actorUsuarioId ou
# qualquer código gerado no backend devolve 422 em vez de ser ignorado em silêncio.
class WorkflowModeloCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    # Full-replace: o form sempre edita o array inteiro de etapas de uma vez — não existem
    # endpoints incrementais de adicionar/remover etapa.
    etapas: list[WorkflowModeloEtapaWrite] = Field(min_length=1)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class WorkflowModeloUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    etapas: list[WorkflowModeloEtapaWrite] | None = Field(default=None, min_length=1)
    status: Literal["ativo", "inativo"] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class WorkflowModeloArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class WorkflowModeloEtapaRead(BaseModel):
    id: UUID
    ordem: int
    nome: str
    tipo: WorkflowEtapaTipo
    quantidade_antes_deadline: int = Field(alias="quantidadeAntesDeadline")
    unidade_prazo: WorkflowUnidadePrazo = Field(alias="unidadePrazo")
    usuario_responsavel_ids: list[UUID] = Field(alias="usuarioResponsavelIds")
    departamento_responsavel_ids: list[UUID] = Field(alias="departamentoResponsavelIds")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WorkflowModeloRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    ano_referencia: int = Field(alias="anoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    status: WorkflowModeloStatus
    etapas: list[WorkflowModeloEtapaRead]
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: WorkflowModeloStatus | None = Field(
        default=None, alias="statusAnteriorArquivamento"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção mínima pra seleção operacional (Nova Tarefa) — só ativo, sem etapas. Diferente do
# /diretorio de Departamento/Cliente, que inclui arquivado pra resolver referência histórica:
# aqui não há referência histórica nenhuma pra resolver, só seleção pra frente.
class WorkflowModeloDiretorioRead(BaseModel):
    id: UUID
    codigo_referencia: str = Field(alias="codigoReferencia")
    nome: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
