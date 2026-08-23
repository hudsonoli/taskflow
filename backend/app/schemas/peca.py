from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

PecaStatus = Literal["ativo", "inativo", "arquivado"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# Sem empresaId/codigoLegado (vêm de current_user / só o import usa) — a API pública nunca
# aceita. `tempoCalculadoExecucaoMinutos` também não entra: é sempre calculado, nunca digitado
# (ver docstring de app/models/peca.py).
class PecaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    categoria_id: UUID | None = Field(default=None, alias="categoriaId")
    tempo_estimado_minutos: int | None = Field(default=None, alias="tempoEstimadoMinutos", ge=0)
    tempo_medio_minutos: int | None = Field(default=None, alias="tempoMedioMinutos", ge=0)
    valor_tabela_centavos: int | None = Field(default=None, alias="valorTabelaCentavos", ge=0)
    sindicato_ativo: bool = Field(default=False, alias="sindicatoAtivo")
    valor_sindicato_criacao_centavos: int | None = Field(default=None, alias="valorSindicatoCriacaoCentavos", ge=0)
    valor_sindicato_adaptacao_centavos: int | None = Field(default=None, alias="valorSindicatoAdaptacaoCentavos", ge=0)
    valor_sindicato_finalizacao_centavos: int | None = Field(
        default=None, alias="valorSindicatoFinalizacaoCentavos", ge=0
    )
    briefing_padrao: str = Field(default="", alias="briefingPadrao", max_length=20000)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PecaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    categoria_id: UUID | None = Field(default=None, alias="categoriaId")
    tempo_estimado_minutos: int | None = Field(default=None, alias="tempoEstimadoMinutos", ge=0)
    tempo_medio_minutos: int | None = Field(default=None, alias="tempoMedioMinutos", ge=0)
    valor_tabela_centavos: int | None = Field(default=None, alias="valorTabelaCentavos", ge=0)
    sindicato_ativo: bool | None = Field(default=None, alias="sindicatoAtivo")
    valor_sindicato_criacao_centavos: int | None = Field(default=None, alias="valorSindicatoCriacaoCentavos", ge=0)
    valor_sindicato_adaptacao_centavos: int | None = Field(default=None, alias="valorSindicatoAdaptacaoCentavos", ge=0)
    valor_sindicato_finalizacao_centavos: int | None = Field(
        default=None, alias="valorSindicatoFinalizacaoCentavos", ge=0
    )
    briefing_padrao: str | None = Field(default=None, alias="briefingPadrao", max_length=20000)
    status: Literal["ativo", "inativo"] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PecaArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PecaRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    nome: str
    categoria_id: UUID | None = Field(default=None, alias="categoriaId")
    # Resolvido no service via join — nunca armazenado. `None` quando a Peça não tem categoria
    # OU quando a categoria não existe mais (não deveria acontecer, sem DELETE físico).
    categoria_nome: str | None = Field(default=None, alias="categoriaNome")
    tempo_estimado_minutos: int | None = Field(default=None, alias="tempoEstimadoMinutos")
    tempo_medio_minutos: int | None = Field(default=None, alias="tempoMedioMinutos")
    tempo_calculado_execucao_minutos: int | None = Field(default=None, alias="tempoCalculadoExecucaoMinutos")
    valor_tabela_centavos: int | None = Field(default=None, alias="valorTabelaCentavos")
    sindicato_ativo: bool = Field(alias="sindicatoAtivo")
    valor_sindicato_criacao_centavos: int | None = Field(default=None, alias="valorSindicatoCriacaoCentavos")
    valor_sindicato_adaptacao_centavos: int | None = Field(default=None, alias="valorSindicatoAdaptacaoCentavos")
    valor_sindicato_finalizacao_centavos: int | None = Field(default=None, alias="valorSindicatoFinalizacaoCentavos")
    briefing_padrao: str = Field(alias="briefingPadrao")
    status: PecaStatus
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


# Projeção mínima pro diretório (GET /pecas/diretorio) — contrato pronto para um futuro
# consumidor operacional (ex.: seleção de Peça em Demanda), ainda inexistente nesta fase. Só
# `ativo`, mesmo padrão de TipoTarefaDiretorioRead.
class PecaDiretorioRead(BaseModel):
    id: UUID
    nome: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
