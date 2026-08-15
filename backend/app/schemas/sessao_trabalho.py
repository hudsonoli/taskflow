from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SessaoTrabalhoStatus = Literal["ativa", "encerrada", "cancelada"]
MotivoEncerramento = Literal[
    "pausa",
    "bloqueio",
    "aguardando_cliente",
    "mudanca_etapa",
    "conclusao",
    "cancelamento",
    "troca_responsavel",
    "substituicao_sessao_ativa",
]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class SessaoTrabalhoRead(BaseModel):
    id: UUID
    # Na LEITURA a empresa é sempre conhecida — a sessão já existe e pertence a uma.
    empresa_id: str = Field(alias="empresaId")
    agencia_id: str | None = Field(default=None, alias="agenciaId")
    demanda_id: str = Field(alias="demandaId")
    workflow_etapa_id: str | None = Field(default=None, alias="workflowEtapaId")
    # Pós-contract (0018): usuario_id/departamento_id JÁ SÃO a coluna FK final — sem alias de
    # leitura especial. Até 0018 este campo lia de usuario_uuid/departamento_uuid via
    # validation_alias (a coluna textual legada coexistia); ver histórico do arquivo.
    usuario_id: str | None = Field(default=None, alias="usuarioId")
    departamento_id: str | None = Field(default=None, alias="departamentoId")
    evento_inicio_id: UUID = Field(alias="eventoInicioId")
    evento_fim_id: UUID | None = Field(default=None, alias="eventoFimId")
    status: SessaoTrabalhoStatus
    inicio_em: datetime = Field(alias="inicioEm")
    fim_em: datetime | None = Field(default=None, alias="fimEm")
    duracao_segundos: int | None = Field(default=None, alias="duracaoSegundos")
    motivo_encerramento: MotivoEncerramento | None = Field(default=None, alias="motivoEncerramento")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("inicio_em", "fim_em", "created_at", "updated_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


class SessaoTrabalhoAbrir(BaseModel):
    # Opcional de propósito: a empresa vem do TOKEN, não do cliente. Aceito só para
    # compatibilidade, e apenas se coincidir — ver `_empresa_do_token` na rota.
    empresa_id: str | None = Field(default=None, alias="empresaId")
    agencia_id: str | None = Field(default=None, alias="agenciaId")
    demanda_id: str = Field(alias="demandaId")
    workflow_etapa_id: str | None = Field(default=None, alias="workflowEtapaId")
    # UUID real de usuarios.id/departamentos.id — validado no service
    # (_ensure_usuario_valido/_ensure_departamento_valido). Nenhuma ponte de id legado
    # ("user-1") é aceita ou reconstruída aqui; ver docstring de app/models/sessao_trabalho.py.
    usuario_id: str | None = Field(default=None, alias="usuarioId")
    departamento_id: str | None = Field(default=None, alias="departamentoId")

    model_config = ConfigDict(populate_by_name=True)


class SessaoTrabalhoFechar(BaseModel):
    motivo_encerramento: MotivoEncerramento = Field(alias="motivoEncerramento")

    model_config = ConfigDict(populate_by_name=True)


class SessaoTrabalhoHorasRead(BaseModel):
    """Agregado de horas de um departamento (`/horas`) — nunca uma lista de sessões.

    ## Semântica de pertencimento (documentar a limitação, não corrigir agora)

    Uma sessão conta para o departamento quando `sessao.departamento_id` aponta pra ele OU
    quando o USUÁRIO da sessão pertence ATUALMENTE a ele (`usuarios.departamento_id`, lido no
    momento da consulta — não uma foto do departamento de quando a sessão aconteceu). Se um
    usuário muda de departamento, sessões antigas dele sem `departamento_id` próprio migram de
    classificação junto — o agregado passa a contar (ou deixar de contar) horas que, na época,
    foram de outro departamento. Isso é uma limitação conhecida e aceita nesta fase (sem
    histórico de lotação por período); não faz parte deste plano corrigi-la.
    """

    departamento_id: str = Field(alias="departamentoId")
    horas_consumidas: float = Field(alias="horasConsumidas")
    sessoes_consideradas: int = Field(alias="sessoesConsideradas")

    model_config = ConfigDict(populate_by_name=True)
