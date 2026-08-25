from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PrioridadePadrao = Literal["baixa", "media", "alta"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ProjetoModeloCampanhaAplicar(BaseModel):
    modelo_campanha_id: UUID = Field(alias="modeloCampanhaId")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# `id` presente = editar item já existente do snapshot (preserva referência não alterada
# mesmo que a entidade tenha sido arquivada depois — ver
# ProjetoModeloCampanhaService._preparar_itens_edicao). `id` ausente, ou que não bate com
# nenhum item atual do snapshot, = item NOVO — toda referência é validada como vínculo novo.
# Nomes snapshot NUNCA vêm do cliente aqui — são sempre resolvidos/preservados pelo backend.
class ProjetoModeloCampanhaItemInput(BaseModel):
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
    def validar_responsavel_unico(self) -> "ProjetoModeloCampanhaItemInput":
        if self.responsavel_usuario_id is not None and self.responsavel_departamento_id is not None:
            raise ValueError("no máximo um responsável sugerido: usuário OU departamento, nunca os dois")
        return self


class ProjetoModeloCampanhaItemRead(BaseModel):
    id: UUID
    ordem: int
    nome: str
    briefing_padrao: str | None = Field(default=None, alias="briefingPadrao")
    prioridade_padrao: PrioridadePadrao = Field(alias="prioridadePadrao")
    peca_id: UUID | None = Field(default=None, alias="pecaId")
    peca_nome_snapshot: str | None = Field(default=None, alias="pecaNomeSnapshot")
    tipo_tarefa_id: UUID | None = Field(default=None, alias="tipoTarefaId")
    tipo_tarefa_nome_snapshot: str | None = Field(default=None, alias="tipoTarefaNomeSnapshot")
    workflow_modelo_id: UUID | None = Field(default=None, alias="workflowModeloId")
    workflow_modelo_nome_snapshot: str | None = Field(default=None, alias="workflowModeloNomeSnapshot")
    responsavel_usuario_id: UUID | None = Field(default=None, alias="responsavelUsuarioId")
    responsavel_usuario_nome_snapshot: str | None = Field(default=None, alias="responsavelUsuarioNomeSnapshot")
    responsavel_departamento_id: UUID | None = Field(default=None, alias="responsavelDepartamentoId")
    responsavel_departamento_nome_snapshot: str | None = Field(
        default=None, alias="responsavelDepartamentoNomeSnapshot"
    )

    model_config = ConfigDict(populate_by_name=True)


class ProjetoModeloCampanhaSnapshotRead(BaseModel):
    id: UUID
    modelo_campanha_origem_id: UUID | None = Field(default=None, alias="modeloCampanhaOrigemId")
    modelo_campanha_nome_snapshot: str | None = Field(default=None, alias="modeloCampanhaNomeSnapshot")
    aplicado_at: datetime | None = Field(default=None, alias="aplicadoAt")
    aplicado_por_usuario_id: UUID | None = Field(default=None, alias="aplicadoPorUsuarioId")
    itens: list[ProjetoModeloCampanhaItemRead] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("aplicado_at", "created_at", "updated_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# PATCH edita só os itens materializados — proveniência/metadados de aplicação
# (modeloCampanhaOrigemId/NomeSnapshot/aplicadoAt/aplicadoPorUsuarioId) são controlados
# exclusivamente pelo backend via /aplicar; `extra="forbid"` garante que o cliente não possa
# tentar sobrescrevê-los por aqui.
class ProjetoModeloCampanhaUpdate(BaseModel):
    itens: list[ProjetoModeloCampanhaItemInput]

    model_config = ConfigDict(populate_by_name=True, extra="forbid")
