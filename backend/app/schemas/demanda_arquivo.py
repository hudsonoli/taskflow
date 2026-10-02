from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

DemandaArquivoTipo = Literal["anexo", "layout", "link"]
DemandaArquivoStatusLayout = Literal["novo", "aprovado", "reprovado", "solicitar_alteracao"]

# Mesma lista em app/services/demanda_arquivo_service.py (fonte única da validação real — o
# schema só impede o óbvio na borda; o service revalida, nunca confia só no Pydantic para uma
# regra de segurança). `javascript:`/`data:`/`file:` e qualquer outro scheme ficam de fora.
_ESQUEMAS_URL_PERMITIDOS = frozenset({"http", "https"})


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validar_url_http_https(url: str) -> str:
    url = url.strip()
    partes = urlsplit(url)
    if partes.scheme.lower() not in _ESQUEMAS_URL_PERMITIDOS or not partes.hostname:
        raise ValueError("URL deve ser http:// ou https:// e conter um domínio válido")
    return url


class DemandaArquivoLinkCreate(BaseModel):
    """`POST /demandas/{demandaId}/arquivos/link` — cria um registro `tipo='link'`, sem
    arquivo físico. Mesma Demanda-mãe (tenant/escopo) do upload físico."""

    titulo: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=500)
    descricao: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validar_url_http_https(value)


class DemandaArquivoStatusLayoutUpdate(BaseModel):
    """`PATCH /demandas/{demandaId}/arquivos/{arquivoId}` — só altera `status_layout`, só
    aceito quando `tipo == 'layout'` (ver DemandaArquivoService.atualizar_status_layout)."""

    status_layout: DemandaArquivoStatusLayout = Field(alias="statusLayout")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DemandaArquivoRead(BaseModel):
    """Sem `url` de download físico: baixar exige o endpoint autenticado
    (`GET /demandas/{demandaId}/arquivos/{id}/download`), nunca um caminho estático — ver
    docs/pendencias-arquiteturais.md item 9. `url` aqui (quando presente) é o link externo de
    um registro `tipo='link'`, não um atalho para o conteúdo físico.

    `nome_original`/`tamanho_bytes` são `None` exatamente quando `tipo='link'` — reflete o
    CHECK `ck_demanda_arquivos_fisico_ou_link` do banco, nunca um estado inesperado."""

    id: UUID
    demanda_id: UUID = Field(alias="demandaId")
    nome_original: str | None = Field(default=None, alias="nomeOriginal")
    content_type: str | None = Field(default=None, alias="contentType")
    tamanho_bytes: int | None = Field(default=None, alias="tamanhoBytes")
    enviado_por_usuario_id: UUID | None = Field(default=None, alias="enviadoPorUsuarioId")
    created_at: datetime = Field(alias="createdAt")
    tipo: DemandaArquivoTipo = "anexo"
    status_layout: DemandaArquivoStatusLayout | None = Field(default=None, alias="statusLayout")
    url: str | None = None
    titulo: str | None = None
    descricao: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)


class ArquivoCentralDemandaRead(BaseModel):
    """Identificação mínima da Demanda-mãe, mesma forma de `DemandaDiretorioRead` — o suficiente
    pra exibir `#{numeroOperacional} — {nome}` no card sem precisar de um segundo fetch."""

    id: UUID
    numero_operacional: int = Field(alias="numeroOperacional")
    codigo_referencia: str = Field(alias="codigoReferencia")
    nome: str

    model_config = ConfigDict(populate_by_name=True)


class ArquivoCentralRead(BaseModel):
    """`GET /arquivos` — item da listagem central. Autossuficiente de propósito (D2-D3C/D2-D4
    ensinaram que depender de um diretório global capado pra resolver nome é como o cap de
    100/200 vaza pra fora da lista que o originou): cliente/projeto/demanda/usuário já vêm
    resolvidos NESTA resposta, pela mesma query (ver
    DemandaArquivoRepository.list_central) — nunca um segundo fetch nem
    AppDataContext."""

    id: UUID
    demanda_id: UUID = Field(alias="demandaId")
    nome: str
    mime_type: str | None = Field(default=None, alias="mimeType")
    tamanho_bytes: int | None = Field(default=None, alias="tamanhoBytes")
    tipo: DemandaArquivoTipo
    status_layout: DemandaArquivoStatusLayout | None = Field(default=None, alias="statusLayout")
    url: str | None = None
    descricao: str | None = None
    created_at: datetime = Field(alias="createdAt")
    enviado_por_usuario_id: UUID | None = Field(default=None, alias="enviadoPorUsuarioId")
    usuario_nome: str | None = Field(default=None, alias="usuarioNome")
    demanda: ArquivoCentralDemandaRead
    projeto_id: UUID | None = Field(default=None, alias="projetoId")
    projeto_nome: str | None = Field(default=None, alias="projetoNome")
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    cliente_nome: str | None = Field(default=None, alias="clienteNome")
    preview_disponivel: bool = Field(alias="previewDisponivel")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("created_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)
