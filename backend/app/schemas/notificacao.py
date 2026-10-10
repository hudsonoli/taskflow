from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.demanda import DemandaRead

CategoriaNotificacao = Literal["sistema", "minhas"]
GrupoPrazo = Literal["atrasadas", "hoje", "proximas"]


class NotificacaoRead(BaseModel):
    """Uma notificação = um evento de domínio (de uma demanda do usuário) + o estado "lida" DESTE usuário."""

    id: UUID  # id do evento
    categoria: CategoriaNotificacao
    tipo: str
    titulo: str
    detalhe: str | None = None
    ocorrida_em: datetime = Field(alias="ocorridaEm")
    lida: bool
    demanda_id: UUID | None = Field(default=None, alias="demandaId")
    demanda_referencia: str | None = Field(default=None, alias="demandaReferencia")
    # Identificador EMITIDO da demanda (`#845`, `BOX-2026-00846`…), o que a operação reconhece — o mesmo de `rotuloDemanda` no resto do app.
    demanda_identificador: str | None = Field(default=None, alias="demandaIdentificador")
    demanda_nome: str | None = Field(default=None, alias="demandaNome")
    autor_nome: str | None = Field(default=None, alias="autorNome")

    model_config = ConfigDict(populate_by_name=True)


class NotificacoesPaginaRead(BaseModel):
    itens: list[NotificacaoRead]
    total: int
    limit: int
    offset: int


class NaoLidasRead(BaseModel):
    sistema: int
    minhas: int
    total: int


class PrazosResumoRead(BaseModel):
    atrasadas: int
    hoje: int
    proximas: int


class NotificacoesResumoRead(BaseModel):
    """UMA fonte para o badge do menu, o sino e a página: contagem de não lidas + totais de prazos."""

    nao_lidas: NaoLidasRead = Field(alias="naoLidas")
    prazos: PrazosResumoRead

    model_config = ConfigDict(populate_by_name=True)


class MarcarLidasRequest(BaseModel):
    """`categoria` ausente/null = todas as categorias."""

    categoria: CategoriaNotificacao | None = None

    model_config = ConfigDict(extra="forbid")


class PrazosEquipePaginaRead(BaseModel):
    itens: list[DemandaRead]
    total: int
    limit: int
    offset: int
