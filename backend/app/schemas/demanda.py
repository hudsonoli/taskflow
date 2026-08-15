from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# `arquivada` no feminino acompanha o vocabulário do próprio domínio (concluida, cancelada,
# pausada). Os demais domínios usam masculino; cada service tem sua constante local, então
# não há código genérico dependendo da grafia.
DemandaStatus = Literal[
    "rascunho",
    "planejada",
    "em_execucao",
    "pausada",
    "bloqueada",
    "aguardando_cliente",
    "concluida",
    "cancelada",
    "arquivada",
]
# `arquivada` fica fora: entra pela rota de arquivamento, com motivo obrigatório.
DemandaStatusEditavel = Literal[
    "rascunho",
    "planejada",
    "em_execucao",
    "pausada",
    "bloqueada",
    "aguardando_cliente",
    "concluida",
    "cancelada",
]
DemandaPrioridade = Literal["baixa", "media", "alta"]

# Campos que a interface conhece mas que ainda NÃO têm tabela — entram em 2E.2/2E.3/2E.4.
# Enviá-los devolve 422 por `extra="forbid"`, nunca aceite-e-descarte silencioso.
CAMPOS_SEM_PERSISTENCIA = (
    "workflowEtapas",
    "etapaAtualId",
    "checklist",
    "arquivos",
    "comentarios",
    "historico",
)


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class _DemandaCamposComuns(BaseModel):
    pit: str | None = Field(default=None, max_length=64)
    briefing: str | None = Field(default=None, max_length=8000)
    prioridade: DemandaPrioridade = "media"
    sinalizada: bool = False
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    projeto_id: UUID | None = Field(default=None, alias="projetoId")
    data_inicio: date | None = Field(default=None, alias="dataInicio")
    data_fim_prevista: date | None = Field(default=None, alias="dataFimPrevista")
    # Campo MANUAL e independente — não deriva de `prazoHoras` das etapas, e nunca derivou.
    # A Pauta ordena por ele.
    prazo_etapa_atual: datetime | None = Field(default=None, alias="prazoEtapaAtual")
    enviado_cliente_em: datetime | None = Field(default=None, alias="enviadoClienteEm")
    prazo_retorno_cliente: datetime | None = Field(default=None, alias="prazoRetornoCliente")
    retorno_recebido_em: datetime | None = Field(default=None, alias="retornoRecebidoEm")
    email_conclusao_enviado: bool = Field(default=False, alias="emailConclusaoEnviado")
    email_conclusao_data: datetime | None = Field(default=None, alias="emailConclusaoData")
    responsavel_ids: list[UUID] | None = Field(default=None, alias="usuarioResponsavelIds")
    departamento_responsavel_ids: list[UUID] | None = Field(
        default=None, alias="departamentoResponsavelIds"
    )


# `extra="forbid"` cobre dois grupos de campos proibidos, pelo mesmo motivo — ignorar em
# silêncio faria o cliente da API acreditar que o valor foi aceito:
#
# 1. **emitidos pelo servidor**: empresaId, actorUsuarioId, codigoReferencia, anoReferencia,
#    sequencialReferencia, numeroOperacional, criadoPorUsuarioId, agenciaId, codigoInterno;
# 2. **sem persistência nesta fase**: workflowEtapas, etapaAtualId, checklist, arquivos,
#    comentarios, historico — ver CAMPOS_SEM_PERSISTENCIA.
#
# O segundo grupo é o que impede a falha silenciosa que este desenho existe para evitar: o
# formulário montava etapas de workflow e elas sumiriam sem aviso.
class DemandaCreate(_DemandaCamposComuns):
    nome: str = Field(min_length=1, max_length=255)
    status: DemandaStatusEditavel = "rascunho"
    # Obrigatório quando `status == "bloqueada"` — validado abaixo.
    motivo_bloqueio: str | None = Field(default=None, alias="motivoBloqueio", max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("motivo_bloqueio")
    @classmethod
    def motivo_nao_pode_ser_so_espaco(cls, value: str | None) -> str | None:
        """`min_length` contaria `"   "` como preenchido. Bloqueio sem motivo real esvazia a
        obrigatoriedade sem que ninguém perceba."""
        if value is None:
            return None
        limpo = value.strip()
        if not limpo:
            raise ValueError("motivoBloqueio não pode conter apenas espaços")
        return limpo


class DemandaUpdate(_DemandaCamposComuns):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    status: DemandaStatusEditavel | None = None
    motivo_bloqueio: str | None = Field(default=None, alias="motivoBloqueio", max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("motivo_bloqueio")
    @classmethod
    def motivo_nao_pode_ser_so_espaco(cls, value: str | None) -> str | None:
        if value is None:
            return None
        limpo = value.strip()
        if not limpo:
            raise ValueError("motivoBloqueio não pode conter apenas espaços")
        return limpo


class DemandaArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("motivo_arquivamento")
    @classmethod
    def motivo_nao_pode_ser_so_espaco(cls, value: str) -> str:
        limpo = value.strip()
        if not limpo:
            raise ValueError("motivoArquivamento não pode conter apenas espaços")
        return limpo


class DemandaDiretorioRead(BaseModel):
    """Forma enxuta para seletores — `TrafegoIniciarSessao` escolhe uma demanda, e as telas de
    sessão resolvem `demandaId` → nome.

    **Também é escopado.** Um diretório que ignorasse o escopo devolveria o nome de toda
    demanda da empresa a qualquer autenticado — reabrindo por uma porta lateral exatamente o
    que `get_no_escopo` fecha na porta principal.
    """

    id: UUID
    numero_operacional: int = Field(alias="numeroOperacional")
    codigo_referencia: str = Field(alias="codigoReferencia")
    nome: str
    status: DemandaStatus
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    projeto_id: UUID | None = Field(default=None, alias="projetoId")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DemandaRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_referencia: str = Field(alias="codigoReferencia")
    ano_referencia: int = Field(alias="anoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    # Rótulo principal da operação — exibido como `#2063`.
    numero_operacional: int = Field(alias="numeroOperacional")
    nome: str
    pit: str | None = None
    briefing: str | None = None
    status: DemandaStatus
    prioridade: DemandaPrioridade
    sinalizada: bool
    motivo_bloqueio: str | None = Field(default=None, alias="motivoBloqueio")
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    projeto_id: UUID | None = Field(default=None, alias="projetoId")
    criado_por_usuario_id: UUID | None = Field(default=None, alias="criadoPorUsuarioId")
    data_inicio: date | None = Field(default=None, alias="dataInicio")
    data_fim_prevista: date | None = Field(default=None, alias="dataFimPrevista")
    prazo_etapa_atual: datetime | None = Field(default=None, alias="prazoEtapaAtual")
    enviado_cliente_em: datetime | None = Field(default=None, alias="enviadoClienteEm")
    prazo_retorno_cliente: datetime | None = Field(default=None, alias="prazoRetornoCliente")
    retorno_recebido_em: datetime | None = Field(default=None, alias="retornoRecebidoEm")
    email_conclusao_enviado: bool = Field(alias="emailConclusaoEnviado")
    email_conclusao_data: datetime | None = Field(default=None, alias="emailConclusaoData")
    usuario_responsavel_ids: list[UUID] = Field(default_factory=list, alias="usuarioResponsavelIds")
    departamento_responsavel_ids: list[UUID] = Field(
        default_factory=list, alias="departamentoResponsavelIds"
    )
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: DemandaStatus | None = Field(
        default=None, alias="statusAnteriorArquivamento"
    )

    # Coleções que ainda não têm tabela. Devolvidas VAZIAS para os componentes não quebrarem —
    # não para simular conteúdo. Vazio é a verdade: não há linha em tabela nenhuma. A escrita
    # é recusada com 422 (ver CAMPOS_SEM_PERSISTENCIA).
    workflow_etapas: list = Field(default_factory=list, alias="workflowEtapas")
    etapa_atual_id: None = Field(default=None, alias="etapaAtualId")
    checklist: list = Field(default_factory=list)
    arquivos: list = Field(default_factory=list)
    comentarios: list = Field(default_factory=list)
    historico: list = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator(
        "created_at",
        "updated_at",
        "arquivado_at",
        "restaurado_at",
        "prazo_etapa_atual",
        "enviado_cliente_em",
        "prazo_retorno_cliente",
        "retorno_recebido_em",
        "email_conclusao_data",
    )
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
