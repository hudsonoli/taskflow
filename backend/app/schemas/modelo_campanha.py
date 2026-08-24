from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ModeloCampanhaStatus = Literal["ativo", "inativo", "arquivado"]
PrioridadePadrao = Literal["baixa", "media", "alta"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# `id` presente = editar item já existente do agregado (preserva referência não alterada
# mesmo que a entidade referenciada tenha sido arquivada depois — ver
# ModeloCampanhaService._ensure_referencias_validas). `id` ausente, ou que não bate com
# nenhum item atual do Modelo, = item NOVO — toda referência é validada como vínculo novo.
class ModeloCampanhaItemInput(BaseModel):
    id: UUID | None = None
    nome: str = Field(min_length=1, max_length=255)
    briefing_padrao: str | None = Field(default=None, alias="briefingPadrao", max_length=4000)
    prioridade_padrao: PrioridadePadrao = Field(default="media", alias="prioridadePadrao")
    peca_id: UUID | None = Field(default=None, alias="pecaId")
    tipo_tarefa_id: UUID | None = Field(default=None, alias="tipoTarefaId")
    workflow_modelo_id: UUID | None = Field(default=None, alias="workflowModeloId")
    responsavel_usuario_id: UUID | None = Field(default=None, alias="responsavelUsuarioId")
    responsavel_departamento_id: UUID | None = Field(default=None, alias="responsavelDepartamentoId")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def validar_responsavel_unico(self) -> "ModeloCampanhaItemInput":
        if self.responsavel_usuario_id is not None and self.responsavel_departamento_id is not None:
            raise ValueError("no máximo um responsável sugerido: usuário OU departamento, nunca os dois")
        return self


class ModeloCampanhaItemRead(BaseModel):
    id: UUID
    ordem: int
    nome: str
    briefing_padrao: str | None = Field(default=None, alias="briefingPadrao")
    prioridade_padrao: PrioridadePadrao = Field(alias="prioridadePadrao")
    peca_id: UUID | None = Field(default=None, alias="pecaId")
    peca_nome: str | None = Field(default=None, alias="pecaNome")
    tipo_tarefa_id: UUID | None = Field(default=None, alias="tipoTarefaId")
    tipo_tarefa_nome: str | None = Field(default=None, alias="tipoTarefaNome")
    workflow_modelo_id: UUID | None = Field(default=None, alias="workflowModeloId")
    workflow_modelo_nome: str | None = Field(default=None, alias="workflowModeloNome")
    responsavel_usuario_id: UUID | None = Field(default=None, alias="responsavelUsuarioId")
    responsavel_usuario_nome: str | None = Field(default=None, alias="responsavelUsuarioNome")
    responsavel_departamento_id: UUID | None = Field(default=None, alias="responsavelDepartamentoId")
    responsavel_departamento_nome: str | None = Field(default=None, alias="responsavelDepartamentoNome")

    model_config = ConfigDict(populate_by_name=True)


# Sem empresaId (vem de current_user) — a API pública nunca aceita. Itens fazem parte do
# agregado: sem endpoint próprio, sempre o conjunto inteiro (ver docstring de
# ModeloCampanhaService.atualizar).
class ModeloCampanhaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=4000)
    itens: list[ModeloCampanhaItemInput] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ModeloCampanhaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=4000)
    status: Literal["ativo", "inativo"] | None = None
    # `None` = não mexe nos itens; lista (mesmo vazia) = substitui o conjunto inteiro.
    itens: list[ModeloCampanhaItemInput] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ModeloCampanhaArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("motivo_arquivamento")
    @classmethod
    def motivo_nao_pode_ser_so_espaco(cls, value: str) -> str:
        limpo = value.strip()
        if not limpo:
            raise ValueError("motivoArquivamento não pode conter apenas espaços")
        return limpo


class ModeloCampanhaRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    nome: str
    descricao: str | None = None
    status: ModeloCampanhaStatus
    itens: list[ModeloCampanhaItemRead] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção mínima pro diretório (GET /modelos-campanha/diretorio) — só ativo, admin/gestor
# nesta fase (ver docstring da rota).
class ModeloCampanhaDiretorioRead(BaseModel):
    id: UUID
    nome: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
