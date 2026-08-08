from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ClienteStatus = Literal["ativo", "suspenso", "inativo", "arquivado"]
ClienteStatusEditavel = Literal["ativo", "suspenso", "inativo"]
DocumentoTipo = Literal["cnpj", "cpf"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ClienteContato(BaseModel):
    """Value object — vive dentro do cliente, sem ciclo de vida próprio."""

    id: str = Field(min_length=1, max_length=64)
    nome: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    telefone: str | None = Field(default=None, max_length=32)
    cargo: str | None = Field(default=None, max_length=255)
    recebe_entregas: bool = Field(default=False, alias="recebeEntregas")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class _ClienteCamposComuns(BaseModel):
    razao_social: str | None = Field(default=None, alias="razaoSocial", max_length=255)
    documento: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    whatsapp: str | None = Field(default=None, max_length=32)
    cep: str | None = Field(default=None, max_length=9)
    bairro: str | None = Field(default=None, max_length=255)
    endereco_completo: str | None = Field(default=None, alias="enderecoCompleto", max_length=500)
    cidade: str | None = Field(default=None, max_length=255)
    uf: str | None = Field(default=None, max_length=2)
    segmento: str | None = Field(default=None, max_length=255)
    origem: str | None = Field(default=None, max_length=255)
    responsavel_comercial_id: UUID | None = Field(default=None, alias="responsavelComercialId")
    cliente_referencial: bool = Field(default=False, alias="clienteReferencial")
    avisar_conclusao_por_email: bool = Field(default=False, alias="avisarConclusaoPorEmail")
    fee_mensal_centavos: int | None = Field(default=None, alias="feeMensalCentavos", ge=0)
    horas_contratadas_mes: float | None = Field(default=None, alias="horasContratadasMes", ge=0)
    observacoes: str | None = Field(default=None, max_length=4000)
    logo_url: str | None = Field(default=None, alias="logoUrl", max_length=500)
    contatos: list[ClienteContato] | None = None
    # Grupos por UUID. `codigoInterno` é ponte de migração e NUNCA é aceito aqui — só
    # seeds e importadores o resolvem internamente.
    grupo_cliente_ids: list[UUID] | None = Field(default=None, alias="grupoClienteIds")


# `extra="forbid"` é deliberado: enviar empresaId, actorUsuarioId, codigoInterno,
# codigoReferencia, anoReferencia ou sequencialReferencia devolve 422 em vez de ser
# ignorado em silêncio. Empresa e ator vêm de current_user; os códigos são gerados no
# backend (ver app/core/referencias.py).
class ClienteCreate(_ClienteCamposComuns):
    nome: str = Field(min_length=1, max_length=255)
    tipo_documento: DocumentoTipo = Field(alias="tipoDocumento")
    cor_identificacao: str = Field(alias="corIdentificacao", min_length=1, max_length=32)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ClienteUpdate(_ClienteCamposComuns):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    tipo_documento: DocumentoTipo | None = Field(default=None, alias="tipoDocumento")
    cor_identificacao: str | None = Field(default=None, alias="corIdentificacao", min_length=1, max_length=32)
    # Arquivar/restaurar têm rotas próprias — não passam por aqui.
    status: ClienteStatusEditavel | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# Motivo da semelhança — lista FECHADA, para o frontend poder decidir a apresentação sem
# interpretar texto livre.
MotivoPossivelDuplicidade = Literal["nome", "documento", "nome_documento"]


class PossivelDuplicidadeCliente(BaseModel):
    """Cliente já existente parecido com o que está sendo gravado.

    **Informativo, nunca bloqueio.** Não há UNIQUE de nome nem de documento em `clientes`
    (ver app/models/cliente.py): a base real tem filiais homônimas com CNPJ distinto e
    empreendimentos distintos sob o mesmo CNPJ. A API cria o registro e devolve estes dados
    estruturados; a interface decide como sinalizar. Deduplicação e merge são trabalho
    futuro, com revisão humana — nunca automáticos.

    Carrega `documento` além do nome porque é justamente o que permite ao operador
    distinguir "mesma empresa" de "filial diferente" sem abrir o outro cadastro.
    """

    id: UUID
    codigo_referencia: str = Field(alias="codigoReferencia")
    nome: str
    documento: str | None = None
    status: ClienteStatus
    motivo: MotivoPossivelDuplicidade

    model_config = ConfigDict(populate_by_name=True)


class ClienteArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ClienteRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    ano_referencia: int = Field(alias="anoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    razao_social: str | None = Field(default=None, alias="razaoSocial")
    tipo_documento: DocumentoTipo = Field(alias="tipoDocumento")
    documento: str | None = None
    status: ClienteStatus
    email: str | None = None
    whatsapp: str | None = None
    cep: str | None = None
    bairro: str | None = None
    endereco_completo: str | None = Field(default=None, alias="enderecoCompleto")
    cidade: str | None = None
    uf: str | None = None
    segmento: str | None = None
    origem: str | None = None
    responsavel_comercial_id: UUID | None = Field(default=None, alias="responsavelComercialId")
    cliente_referencial: bool = Field(alias="clienteReferencial")
    avisar_conclusao_por_email: bool = Field(alias="avisarConclusaoPorEmail")
    fee_mensal_centavos: int | None = Field(default=None, alias="feeMensalCentavos")
    horas_contratadas_mes: float | None = Field(default=None, alias="horasContratadasMes")
    observacoes: str | None = None
    cor_identificacao: str = Field(alias="corIdentificacao")
    logo_url: str | None = Field(default=None, alias="logoUrl")
    contatos: list[ClienteContato] = Field(default_factory=list)
    grupo_cliente_ids: list[UUID] = Field(default_factory=list, alias="grupoClienteIds")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: ClienteStatus | None = Field(
        default=None, alias="statusAnteriorArquivamento"
    )
    # Preenchido só nas respostas de criação e alteração — calcular em toda listagem
    # custaria uma consulta por linha sem serventia. Lista vazia significa "nada parecido".
    possiveis_duplicidades: list[PossivelDuplicidadeCliente] = Field(
        default_factory=list, alias="possiveisDuplicidades"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção para seletores. Inclui arquivados de propósito (resolução histórica de
# referências antigas) e expõe `status` para a UI decidir o que oferecer como opção nova.
#
# Carrega `email`, `contatos` e `avisarConclusaoPorEmail` porque o aviso de conclusão de
# demanda precisa saber quem recebe a entrega, e ele aparece para qualquer pessoa que conclui
# uma tarefa — não só admin/gestor, que são os únicos com acesso a `GET /clientes/{id}`. São
# os mesmos contatos que o operador já usa ao trabalhar a demanda.
#
# Dado financeiro (fee mensal, horas contratadas) fica DELIBERADAMENTE fora: é restrito a
# perfis com acesso financeiro (ver podeVerDadosFinanceiros) e não tem uso em seletor.
class ClienteDiretorioRead(BaseModel):
    id: UUID
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    cor_identificacao: str = Field(alias="corIdentificacao")
    status: ClienteStatus
    grupo_cliente_ids: list[UUID] = Field(default_factory=list, alias="grupoClienteIds")
    email: str | None = None
    contatos: list[ClienteContato] = Field(default_factory=list)
    avisar_conclusao_por_email: bool = Field(default=False, alias="avisarConclusaoPorEmail")
    # Necessário para o escopo "minhas demandas" do Atendimento resolver os clientes sob
    # responsabilidade comercial de quem está logado (frontend/src/lib/escopo-operacional.ts
    # → tarefasDoAtendimento). Mesmo motivo pelo qual DepartamentoDiretorioRead carrega
    # `responsavelUsuarioId`.
    responsavel_comercial_id: UUID | None = Field(default=None, alias="responsavelComercialId")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
