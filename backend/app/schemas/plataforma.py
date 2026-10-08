"""Schemas da Administração da Plataforma (`/plataforma/*`) — Fase 1B.

Só o necessário: nada de secrets, hash, tokens de terceiros nem configuração interna (SMTP etc.). A senha temporária de
um Gestor recém-criado existe APENAS em `PlataformaGestorCriadoRead` (resposta da criação) e nunca mais.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.empresa import EmpresaRead


class PlataformaSessaoRead(BaseModel):
    """Token curto da plataforma (BFF guarda em cookie HttpOnly `tf_platform`; o navegador nunca o lê)."""

    access_token: str = Field(alias="accessToken")
    token_type: Literal["bearer"] = Field(default="bearer", alias="tokenType")
    expires_in: int = Field(alias="expiresIn")

    model_config = ConfigDict(populate_by_name=True)


class PlataformaAcessoRead(BaseModel):
    """Capacidade do usuário tenant logado: é Administrador da Plataforma? (decidido no backend, nunca no cliente)."""

    administrador_plataforma: bool = Field(alias="administradorPlataforma")

    model_config = ConfigDict(populate_by_name=True)


class PlataformaMeRead(BaseModel):
    administrador_id: UUID = Field(alias="administradorId")
    usuario_id: UUID = Field(alias="usuarioId")
    nome: str
    ativo: bool
    criado_em: datetime = Field(alias="criadoEm")

    model_config = ConfigDict(populate_by_name=True)


class PlataformaEmpresaRead(EmpresaRead):
    gestores_ativos: int = Field(default=0, alias="gestoresAtivos")
    hospeda_administrador_plataforma: bool = Field(default=False, alias="hospedaAdministradorPlataforma")


class PlataformaUsuarioRead(BaseModel):
    """Só metadados: nome, e-mail, perfil técnico e situação. Conta de sistema nunca entra aqui."""

    id: UUID
    nome: str
    email: str
    perfil_base: Literal["admin", "gestor", "operador"] = Field(alias="perfilBase")
    status: Literal["ativo", "inativo", "bloqueado", "arquivado"]
    acesso_sistema: bool = Field(alias="acessoSistema")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class PlataformaGestorCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PlataformaGestorCriadoRead(BaseModel):
    """Resposta ÚNICA da criação: `senhaTemporaria` aparece aqui e em nenhum outro lugar (nem log, nem evento)."""

    usuario: PlataformaUsuarioRead
    senha_temporaria: str = Field(alias="senhaTemporaria")
    deve_alterar_senha: bool = Field(default=True, alias="deveAlterarSenha")

    model_config = ConfigDict(populate_by_name=True)
