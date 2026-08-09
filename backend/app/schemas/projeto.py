from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProjetoStatus = Literal[
    "planejamento", "ativo", "pausado", "concluido", "cancelado", "arquivado"
]
# `arquivado` fica fora: entra pela rota de arquivamento, com motivo obrigatório.
ProjetoStatusEditavel = Literal["planejamento", "ativo", "pausado", "concluido", "cancelado"]
ProjetoPrioridade = Literal["baixa", "media", "alta"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ProjetoModeloCampanhaItem(BaseModel):
    """Item do modelo de campanha — value object, vive dentro do projeto.

    `tipoTarefaId`, `workflowSugeridoId` e `responsavelOuSetorSugeridoId` são **ids legados
    em texto**, sem FK: TipoTarefa e Workflow ainda não têm tabela. Os nomes vêm junto porque
    hoje não há de onde resolvê-los. Quando esses domínios migrarem, os ids viram relação
    real e os nomes saem — migration própria, ver docs/pendencias-arquiteturais.md.
    """

    id: str = Field(min_length=1, max_length=64)
    nome_demanda: str = Field(alias="nomeDemanda", min_length=1, max_length=255)
    tipo_tarefa_id: str | None = Field(default=None, alias="tipoTarefaId", max_length=64)
    tipo_tarefa_nome: str | None = Field(default=None, alias="tipoTarefaNome", max_length=255)
    briefing_base: str | None = Field(default=None, alias="briefingBase", max_length=4000)
    prioridade_padrao: ProjetoPrioridade = Field(default="media", alias="prioridadePadrao")
    workflow_sugerido_id: str | None = Field(default=None, alias="workflowSugeridoId", max_length=64)
    workflow_sugerido_nome: str | None = Field(default=None, alias="workflowSugeridoNome", max_length=255)
    responsavel_ou_setor_sugerido_id: str | None = Field(
        default=None, alias="responsavelOuSetorSugeridoId", max_length=64
    )
    responsavel_ou_setor_sugerido_nome: str | None = Field(
        default=None, alias="responsavelOuSetorSugeridoNome", max_length=255
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ProjetoEquipeMembroPayload(BaseModel):
    """Pessoa alocada ao projeto. `funcao` é atributo do vínculo, não da pessoa.

    Nome e departamento **não** entram: vêm por join de `usuarios` (ver docstring de
    app/models/projeto_equipe_membro.py).
    """

    usuario_id: UUID = Field(alias="usuarioId")
    funcao: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ProjetoEquipeMembroRead(BaseModel):
    usuario_id: UUID = Field(alias="usuarioId")
    funcao: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class _ProjetoCamposComuns(BaseModel):
    campanha: str | None = Field(default=None, max_length=255)
    descricao: str | None = Field(default=None, max_length=4000)
    resumo: str | None = Field(default=None, max_length=4000)
    # Nullable: projeto interno da agência não tem cliente.
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    data_inicio: date | None = Field(default=None, alias="dataInicio")
    data_fim_prevista: date | None = Field(default=None, alias="dataFimPrevista")
    modelo_campanha_id: str | None = Field(default=None, alias="modeloCampanhaId", max_length=64)
    modelo_campanha: list[ProjetoModeloCampanhaItem] | None = Field(
        default=None, alias="modeloCampanha"
    )
    # Relações por UUID. `codigoInterno` é ponte de importação e NUNCA é aceito aqui.
    responsavel_ids: list[UUID] | None = Field(default=None, alias="responsavelIds")
    departamento_responsavel_ids: list[UUID] | None = Field(
        default=None, alias="departamentoResponsavelIds"
    )
    equipe: list[ProjetoEquipeMembroPayload] | None = None


# `extra="forbid"` é deliberado: enviar empresaId, actorUsuarioId, codigoInterno,
# codigoReferencia, anoReferencia, sequencialReferencia ou o antigo `agenciaId` devolve 422
# em vez de ser ignorado em silêncio.
class ProjetoCreate(_ProjetoCamposComuns):
    nome: str = Field(min_length=1, max_length=255)
    status: ProjetoStatusEditavel = "planejamento"
    prioridade: ProjetoPrioridade = "media"

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ProjetoUpdate(_ProjetoCamposComuns):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    status: ProjetoStatusEditavel | None = None
    prioridade: ProjetoPrioridade | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ProjetoArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("motivo_arquivamento")
    @classmethod
    def motivo_nao_pode_ser_so_espaco(cls, value: str) -> str:
        """Mesma regra de FornecedorArquivar: `min_length=1` aceitaria `"   "`.

        Cliente, Departamento, Equipe e Usuário ainda aceitam — divergência conhecida,
        registrada em docs/pendencias-arquiteturais.md, item 1.
        """
        limpo = value.strip()
        if not limpo:
            raise ValueError("motivoArquivamento não pode conter apenas espaços")
        return limpo


class ProjetoRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    ano_referencia: int = Field(alias="anoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    campanha: str | None = None
    descricao: str | None = None
    resumo: str | None = None
    status: ProjetoStatus
    prioridade: ProjetoPrioridade
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    data_inicio: date | None = Field(default=None, alias="dataInicio")
    data_fim_prevista: date | None = Field(default=None, alias="dataFimPrevista")
    modelo_campanha_id: str | None = Field(default=None, alias="modeloCampanhaId")
    modelo_campanha: list[ProjetoModeloCampanhaItem] = Field(
        default_factory=list, alias="modeloCampanha"
    )
    responsavel_ids: list[UUID] = Field(default_factory=list, alias="responsavelIds")
    departamento_responsavel_ids: list[UUID] = Field(
        default_factory=list, alias="departamentoResponsavelIds"
    )
    equipe: list[ProjetoEquipeMembroRead] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: ProjetoStatus | None = Field(
        default=None, alias="statusAnteriorArquivamento"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção para seletores de vínculo. **Exclui arquivados**, mesmo critério de Fornecedor:
# arquivado nunca é oferecido como opção nova. Quem precisa ver arquivados usa
# GET /projetos com `status=arquivado`.
class ProjetoDiretorioRead(BaseModel):
    id: UUID
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    status: ProjetoStatus
    cliente_id: UUID | None = Field(default=None, alias="clienteId")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
