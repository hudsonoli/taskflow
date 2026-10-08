"""Schemas da Dashboard da Administração da Plataforma (`GET /plataforma/dashboard`).

Só métricas AGREGADAS por empresa e datas de acesso: nenhum nome/e-mail de usuário, nenhum conteúdo operacional (demandas,
comentários, clientes, documentos).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DashboardResumoRead(BaseModel):
    """Totais globais. Usuários e adoção contam só as empresas ATIVAS (usuário de empresa inativa não consegue entrar)."""

    empresas_total: int = Field(alias="empresasTotal")
    empresas_ativas: int = Field(alias="empresasAtivas")
    usuarios: int
    cadastrados: int
    ja_acessaram: int = Field(alias="jaAcessaram")
    nunca_acessaram: int = Field(alias="nuncaAcessaram")
    ativos_7d: int = Field(alias="ativos7d")
    ativos_30d: int = Field(alias="ativos30d")
    gestores: int

    model_config = ConfigDict(populate_by_name=True)


class DashboardEmpresaRead(BaseModel):
    id: UUID
    nome: str
    nome_fantasia: str | None = Field(default=None, alias="nomeFantasia")
    slug: str
    status: Literal["ativa", "inativa", "arquivada"]
    created_at: datetime = Field(alias="createdAt")
    # Usuários humanos UTILIZÁVEIS (ativos, com acesso, fora conta de sistema). `cadastrados` inclui inativos/bloqueados
    # (só os arquivados e a conta de sistema ficam de fora).
    usuarios: int
    cadastrados: int
    ja_acessaram: int = Field(alias="jaAcessaram")
    nunca_acessaram: int = Field(alias="nuncaAcessaram")
    ativos_7d: int = Field(alias="ativos7d")
    ativos_30d: int = Field(alias="ativos30d")
    gestores: int
    # Último LOGIN bem-sucedido de qualquer usuário humano da empresa (não há rastreio de atividade além do login).
    ultimo_acesso: datetime | None = Field(default=None, alias="ultimoAcesso")
    projetos: int
    demandas: int

    model_config = ConfigDict(populate_by_name=True)


AtencaoTipo = Literal["sem_gestor", "nunca_acessaram", "sem_acesso_30d"]


class DashboardAtencaoRead(BaseModel):
    tipo: AtencaoTipo
    severidade: Literal["aviso", "info"]
    empresa_id: UUID = Field(alias="empresaId")
    empresa_nome: str = Field(alias="empresaNome")
    mensagem: str
    quantidade: int | None = None

    model_config = ConfigDict(populate_by_name=True)


class PlataformaDashboardRead(BaseModel):
    gerado_em: datetime = Field(alias="geradoEm")
    resumo: DashboardResumoRead
    empresas: list[DashboardEmpresaRead]
    atencoes: list[DashboardAtencaoRead]

    model_config = ConfigDict(populate_by_name=True)
