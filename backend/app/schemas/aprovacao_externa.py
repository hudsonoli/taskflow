"""Contratos do Portal Externo de Aprovação (Fase 9B).

Dois lados, sem cruzamento:
  - INTERNO (usuário autenticado): criar/consultar/revogar o link de uma etapa de aprovação — pode mostrar ids internos e e-mails;
  - PÚBLICO (portador do token): o mínimo para o cliente decidir. NUNCA ids internos, e-mails internos, comentários, timeline, financeiro, responsáveis,
    outros arquivos. O `token` aparece SÓ na criação (resposta única, `no-store`) e no corpo das chamadas públicas — nunca em path/query/log.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.configuracao_personalizacao import PublicoEmpresaBrandingRead

EstadoAprovacaoExterna = Literal["pendente", "aprovada", "ajustes_solicitados", "revogada", "expirada", "obsoleta"]
DecisaoPublica = Literal["aprovar", "solicitar_ajustes"]

VALIDADE_PADRAO_DIAS = 7
VALIDADE_MIN_DIAS = 1
VALIDADE_MAX_DIAS = 30
MAX_ARTEFATOS = 10
INSTRUCAO_MAX = 1000
NOME_MIN, NOME_MAX = 3, 120
MOTIVO_MIN, MOTIVO_MAX = 3, 1000
EMAIL_MAX = 254

# `secrets.token_urlsafe(32)` → 43 caracteres base64url. Formato diferente nunca chega a consultar o banco.
_TOKEN_REGEX = re.compile(r"^[A-Za-z0-9_-]{43}$")
_EMAIL_REGEX = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")
_CONTROLE_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")  # preserva \t \n \r


def token_com_formato_valido(valor: object) -> bool:
    return isinstance(valor, str) and bool(_TOKEN_REGEX.match(valor))


def _texto_limpo(valor: str, *, minimo: int, maximo: int, campo: str, multilinha: bool = False) -> str:
    """Trim, sem caracteres de controle, sem marcação HTML (`<`/`>`), tamanho dentro do intervalo. Nada é "sanitizado" em silêncio: o que não serve é
    recusado, e a interface sempre renderiza como TEXTO."""
    texto = valor.strip()
    if _CONTROLE_REGEX.search(texto):
        raise ValueError(f"{campo} contém caracteres inválidos")
    if "<" in texto or ">" in texto:
        raise ValueError(f"{campo} não pode conter marcação HTML")
    if not multilinha:
        texto = re.sub(r"\s+", " ", texto)
    if len(texto) < minimo:
        raise ValueError(f"{campo} deve ter pelo menos {minimo} caracteres")
    if len(texto) > maximo:
        raise ValueError(f"{campo} deve ter no máximo {maximo} caracteres")
    return texto


def _email_normalizado(valor: str | None, campo: str = "e-mail") -> str | None:
    if valor is None:
        return None
    texto = valor.strip().lower()
    if not texto:
        return None
    if len(texto) > EMAIL_MAX or not _EMAIL_REGEX.match(texto):
        raise ValueError(f"{campo} inválido")
    return texto


# ======================================================================================
# Interno
# ======================================================================================


class AprovacaoExternaCriar(BaseModel):
    """Criar o link da etapa de aprovação ATUAL. Os arquivos são escolhidos entre os da PRÓPRIA Demanda (layout/anexo; PNG/JPG/PDF)."""

    arquivo_ids: list[UUID] = Field(alias="arquivoIds", min_length=1, max_length=MAX_ARTEFATOS)
    instrucao: str | None = Field(default=None)
    validade_dias: int = Field(default=VALIDADE_PADRAO_DIAS, alias="validadeDias", ge=VALIDADE_MIN_DIAS, le=VALIDADE_MAX_DIAS)
    # "Para quem o link foi destinado" — snapshot do contato do Cliente (ou digitado). Não é o aprovador nem é verificado.
    destinatario_nome: str | None = Field(default=None, alias="destinatarioNome")
    destinatario_email: str | None = Field(default=None, alias="destinatarioEmail")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("arquivo_ids")
    @classmethod
    def _sem_repetidos(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("arquivoIds contém arquivos repetidos")
        return value

    @field_validator("instrucao")
    @classmethod
    def _instrucao(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return _texto_limpo(value, minimo=1, maximo=INSTRUCAO_MAX, campo="instrucao", multilinha=True)

    @field_validator("destinatario_nome")
    @classmethod
    def _destinatario_nome(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return _texto_limpo(value, minimo=1, maximo=NOME_MAX, campo="destinatarioNome")

    @field_validator("destinatario_email")
    @classmethod
    def _destinatario_email(cls, value: str | None) -> str | None:
        return _email_normalizado(value, "destinatarioEmail")


class AprovacaoExternaArtefatoRead(BaseModel):
    ordem: int
    nome: str
    content_type: str = Field(alias="contentType")
    tamanho_bytes: int = Field(alias="tamanhoBytes")
    # `None` quando o arquivo original foi excluído (permitido só em solicitação revogada sem decisão); o snapshot continua.
    arquivo_id: UUID | None = Field(default=None, alias="arquivoId")

    model_config = ConfigDict(populate_by_name=True)


class AprovacaoExternaDecisaoRead(BaseModel):
    decisao: Literal["aprovada", "ajustes_solicitados"]
    decidida_em: datetime = Field(alias="decididaEm")
    nome_aprovador: str = Field(alias="nomeAprovador")
    email_aprovador: str | None = Field(default=None, alias="emailAprovador")
    motivo: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class AprovacaoExternaRead(BaseModel):
    id: UUID
    etapa_id: UUID = Field(alias="etapaId")
    estado: EstadoAprovacaoExterna
    instrucao: str | None = None
    criada_em: datetime = Field(alias="criadaEm")
    criada_por_nome: str | None = Field(default=None, alias="criadaPorNome")
    expira_em: datetime = Field(alias="expiraEm")
    revogada_em: datetime | None = Field(default=None, alias="revogadaEm")
    revogada_motivo: str | None = Field(default=None, alias="revogadaMotivo")
    destinatario_nome: str | None = Field(default=None, alias="destinatarioNome")
    destinatario_email: str | None = Field(default=None, alias="destinatarioEmail")
    artefatos: list[AprovacaoExternaArtefatoRead]
    decisao: AprovacaoExternaDecisaoRead | None = None

    model_config = ConfigDict(populate_by_name=True)


class AprovacaoExternaCriadaRead(AprovacaoExternaRead):
    """Resposta ÚNICA da criação: carrega o token em claro (nunca mais recuperável — o banco guarda só o SHA-256)."""

    token: str


class ContatoClienteRead(BaseModel):
    """Contato do Cliente para "destinatário pretendido" — sem id do contato, sem telefone."""

    nome: str
    email: str | None = None
    cargo: str | None = None
    recebe_entregas: bool = Field(default=False, alias="recebeEntregas")

    model_config = ConfigDict(populate_by_name=True)


class AprovacaoExternaEstadoRead(BaseModel):
    """Painel interno da etapa: o que o usuário pode fazer e a solicitação mais recente (qualquer estado)."""

    pode_gerenciar: bool = Field(alias="podeGerenciar")
    atual: AprovacaoExternaRead | None = None
    contatos: list[ContatoClienteRead] = Field(default_factory=list)
    validade_padrao_dias: int = Field(default=VALIDADE_PADRAO_DIAS, alias="validadePadraoDias")
    validade_max_dias: int = Field(default=VALIDADE_MAX_DIAS, alias="validadeMaxDias")

    model_config = ConfigDict(populate_by_name=True)


# ======================================================================================
# Público (portador do token)
# ======================================================================================


class _CorpoComToken(BaseModel):
    token: str
    model_config = ConfigDict(extra="forbid")

    @field_validator("token")
    @classmethod
    def _formato(cls, value: str) -> str:
        if not token_com_formato_valido(value):
            raise ValueError("token inválido")
        return value


class AprovacaoPublicaConsultar(_CorpoComToken):
    pass


class AprovacaoPublicaArtefatoPedido(_CorpoComToken):
    ordem: int = Field(ge=1, le=MAX_ARTEFATOS)


class AprovacaoPublicaDecisao(_CorpoComToken):
    """Contrato ESTRITO da decisão: `aprovar` (sem motivo) ou `solicitar_ajustes` (motivo 3..1000, obrigatório). Identidade declarada: nome 3..120
    obrigatório, e-mail opcional normalizado — nenhum dos dois é verificado."""

    decisao: DecisaoPublica
    nome: str
    email: str | None = None
    motivo: str | None = None

    @field_validator("nome")
    @classmethod
    def _nome(cls, value: str) -> str:
        return _texto_limpo(value, minimo=NOME_MIN, maximo=NOME_MAX, campo="nome")

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return _email_normalizado(value)

    @model_validator(mode="after")
    def _motivo_conforme_a_decisao(self) -> "AprovacaoPublicaDecisao":
        motivo = (self.motivo or "").strip()
        if self.decisao == "solicitar_ajustes":
            self.motivo = _texto_limpo(motivo, minimo=MOTIVO_MIN, maximo=MOTIVO_MAX, campo="motivo", multilinha=True)
        elif motivo:
            raise ValueError("motivo só se aplica a solicitar_ajustes")
        else:
            self.motivo = None
        return self


class AprovacaoPublicaArtefatoRead(BaseModel):
    ordem: int
    nome: str
    tipo: Literal["imagem", "pdf"]
    content_type: str = Field(alias="contentType")
    tamanho_bytes: int = Field(alias="tamanhoBytes")

    model_config = ConfigDict(populate_by_name=True)


class AprovacaoPublicaDecisaoRead(BaseModel):
    decisao: Literal["aprovada", "ajustes_solicitados"]
    decidida_em: datetime = Field(alias="decididaEm")

    model_config = ConfigDict(populate_by_name=True)


class AprovacaoPublicaRead(BaseModel):
    """O que o cliente enxerga. Estado: `pendente` (pode decidir), `aprovada` ou `ajustes_solicitados` (somente leitura). Revogada/expirada/obsoleta/
    inexistente NÃO chegam aqui: viram 404 neutro, sem distinguir o motivo."""

    empresa: PublicoEmpresaBrandingRead
    demanda_identificador: str = Field(alias="demandaIdentificador")
    demanda_nome: str = Field(alias="demandaNome")
    instrucao: str | None = None
    estado: Literal["pendente", "aprovada", "ajustes_solicitados"]
    expira_em: datetime = Field(alias="expiraEm")
    destinatario_nome: str | None = Field(default=None, alias="destinatarioNome")
    # Falso quando a etapa de aprovação é a PRIMEIRA do workflow: não há etapa anterior para devolver (semântica 8D) — a interface esconde "Solicitar ajustes".
    pode_solicitar_ajustes: bool = Field(default=True, alias="podeSolicitarAjustes")
    artefatos: list[AprovacaoPublicaArtefatoRead]
    decisao: AprovacaoPublicaDecisaoRead | None = None

    model_config = ConfigDict(populate_by_name=True)


class AprovacaoPublicaDecisaoResultadoRead(BaseModel):
    estado: Literal["aprovada", "ajustes_solicitados"]
    decidida_em: datetime = Field(alias="decididaEm")

    model_config = ConfigDict(populate_by_name=True)
