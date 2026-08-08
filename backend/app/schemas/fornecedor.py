from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Sem `suspenso`, de propósito — ver docstring de app/models/fornecedor.py.
FornecedorStatus = Literal["ativo", "inativo", "arquivado"]
FornecedorStatusEditavel = Literal["ativo", "inativo"]
DocumentoTipo = Literal["cnpj", "cpf"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class _FornecedorCamposComuns(BaseModel):
    documento: str | None = Field(default=None, max_length=32)
    categoria: str | None = Field(default=None, max_length=255)
    contato_nome: str | None = Field(default=None, alias="contatoNome", max_length=255)
    email: str | None = Field(default=None, max_length=255)
    whatsapp: str | None = Field(default=None, max_length=32)
    site: str | None = Field(default=None, max_length=255)
    cep: str | None = Field(default=None, max_length=9)
    bairro: str | None = Field(default=None, max_length=255)
    endereco_completo: str | None = Field(default=None, alias="enderecoCompleto", max_length=500)
    cidade: str | None = Field(default=None, max_length=255)
    uf: str | None = Field(default=None, max_length=2)
    observacoes: str | None = Field(default=None, max_length=4000)


# `extra="forbid"` é deliberado: enviar empresaId, actorUsuarioId, codigoInterno,
# codigoReferencia, anoReferencia ou sequencialReferencia devolve 422 em vez de ser ignorado
# em silêncio. Empresa e ator vêm de current_user; os códigos são gerados no backend (ver
# app/core/referencias.py).
class FornecedorCreate(_FornecedorCamposComuns):
    nome: str = Field(min_length=1, max_length=255)
    tipo_documento: DocumentoTipo = Field(alias="tipoDocumento")
    cor_identificacao: str = Field(alias="corIdentificacao", min_length=1, max_length=32)
    # Fornecedor pode nascer inativo (cadastro histórico); `arquivado` não é aceito aqui —
    # arquivamento tem rota própria e exige motivo.
    status: FornecedorStatusEditavel = "ativo"

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class FornecedorUpdate(_FornecedorCamposComuns):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    tipo_documento: DocumentoTipo | None = Field(default=None, alias="tipoDocumento")
    cor_identificacao: str | None = Field(default=None, alias="corIdentificacao", min_length=1, max_length=32)
    # Arquivar/restaurar têm rotas próprias — não passam por aqui.
    status: FornecedorStatusEditavel | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# Motivo da semelhança — lista FECHADA, para o frontend poder decidir a apresentação sem
# interpretar texto livre.
MotivoPossivelDuplicidade = Literal["nome", "documento", "nome_documento"]


class PossivelDuplicidadeFornecedor(BaseModel):
    """Fornecedor já existente parecido com o que está sendo gravado.

    **Informativo, nunca bloqueio** — mesmo contrato de PossivelDuplicidadeCliente. Não há
    UNIQUE de nome nem de documento em `fornecedores` (ver app/models/fornecedor.py): a API
    cria o registro e devolve estes dados estruturados; a interface decide como sinalizar.
    Deduplicação e merge são trabalho futuro, com revisão humana — nunca automáticos.

    Carrega `documento` além do nome porque é justamente o que permite ao operador distinguir
    "mesmo fornecedor" de "cadastro diferente" sem abrir o outro registro.

    Carrega também `sequencialReferencia`: sem ele o frontend teria de recortar o código
    (`codigoReferencia[3:]`) para montar o rótulo `#12-Nome`, que é exatamente o que
    frontend/src/lib/formatarReferencia.ts proíbe.

    **Divergência conhecida:** `PossivelDuplicidadeCliente` ainda não traz este campo, e o
    componente de Cliente recorta o código. Ver docs/pendencias-arquiteturais.md, item 2.
    """

    id: UUID
    codigo_referencia: str = Field(alias="codigoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    documento: str | None = None
    status: FornecedorStatus
    motivo: MotivoPossivelDuplicidade

    model_config = ConfigDict(populate_by_name=True)


class FornecedorArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("motivo_arquivamento")
    @classmethod
    def motivo_nao_pode_ser_so_espaco(cls, value: str) -> str:
        """`min_length=1` conta caracteres, e `"   "` tem três — passaria.

        Arquivamento é permanente e o motivo é o único registro de por que aconteceu; aceitar
        espaço em branco esvazia a obrigatoriedade sem que ninguém perceba. Guarda o valor já
        sem as pontas, para não gravar `" encerrou contrato "`.

        **Divergência conhecida:** Cliente, Departamento, Equipe e Usuário ainda aceitam
        motivo só com espaços. A padronização é uma microfase própria — ver
        docs/pendencias-arquiteturais.md, item 1.
        """
        limpo = value.strip()
        if not limpo:
            raise ValueError("motivoArquivamento não pode conter apenas espaços")
        return limpo


class FornecedorRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    ano_referencia: int = Field(alias="anoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    tipo_documento: DocumentoTipo = Field(alias="tipoDocumento")
    documento: str | None = None
    status: FornecedorStatus
    categoria: str | None = None
    contato_nome: str | None = Field(default=None, alias="contatoNome")
    email: str | None = None
    whatsapp: str | None = None
    site: str | None = None
    cep: str | None = None
    bairro: str | None = None
    endereco_completo: str | None = Field(default=None, alias="enderecoCompleto")
    cidade: str | None = None
    uf: str | None = None
    observacoes: str | None = None
    cor_identificacao: str = Field(alias="corIdentificacao")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: FornecedorStatus | None = Field(
        default=None, alias="statusAnteriorArquivamento"
    )
    # Preenchido só nas respostas de criação e alteração — calcular em toda listagem custaria
    # uma consulta por linha sem serventia. Lista vazia significa "nada parecido".
    possiveis_duplicidades: list[PossivelDuplicidadeFornecedor] = Field(
        default_factory=list, alias="possiveisDuplicidades"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção para seletores de vínculo.
#
# **Exclui arquivados**, ao contrário de ClienteDiretorioRead — divergência deliberada.
# Cliente inclui porque Demanda e Projeto carregam referências históricas que precisam
# continuar resolvendo o nome depois do arquivamento. Fornecedor não é referenciado por
# nenhum domínio, então o diretório serve a um propósito só: oferecer opções de vínculo
# novo — e arquivado nunca pode ser oferecido. Ver app/repositories/fornecedor_repository.py.
#
# Quando algum consumidor precisar resolver referência histórica, isso entra como parâmetro
# explícito (`incluirArquivados=true`), nunca como padrão.
class FornecedorDiretorioRead(BaseModel):
    id: UUID
    codigo_interno: str = Field(alias="codigoInterno")
    codigo_referencia: str = Field(alias="codigoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    nome: str
    categoria: str | None = None
    cor_identificacao: str = Field(alias="corIdentificacao")
    status: FornecedorStatus

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
