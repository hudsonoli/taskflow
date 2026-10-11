"""Schemas da Administração da Plataforma (`/plataforma/*`) — Fase 1B.

Só o necessário: nada de secrets, hash, tokens de terceiros nem configuração interna (SMTP etc.). A senha temporária de
um Gestor recém-criado existe APENAS em `PlataformaGestorCriadoRead` (resposta da criação) e nunca mais.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.empresa import EmpresaCreate, EmpresaRead


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
    # Convite de primeiro acesso ainda não concluído (a pessoa não definiu a própria senha). Só um sinal — nunca token nem hash.
    primeiro_acesso_pendente: bool = Field(default=False, alias="primeiroAcessoPendente")

    model_config = ConfigDict(populate_by_name=True)


_EMAIL_REGEX = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")


class PlataformaGestorCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("nome")
    @classmethod
    def _nome(cls, value: str) -> str:
        texto = re.sub(r"\s+", " ", value).strip()
        if not texto:
            raise ValueError("Informe o nome do Gestor.")
        if "<" in texto or ">" in texto:
            raise ValueError("O nome não pode conter marcação HTML.")
        return texto

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        texto = value.strip().lower()
        if not _EMAIL_REGEX.match(texto):
            raise ValueError("Informe um e-mail válido.")
        return texto


class PlataformaConviteRead(BaseModel):
    """Desfecho do convite de primeiro acesso do Gestor. NENHUMA senha existe aqui. `enviado=false` (ex.: a empresa nova ainda não tem SMTP) não desfaz a
    criação: o convite segue válido e `linkAcesso` é o link de primeiro acesso para entrega manual — presente SÓ nessa resposta (o banco guarda o hash)."""

    enviado: bool
    motivo: Literal["email_nao_configurado", "url_publica_ausente", "falha_envio"] | None = None
    expira_em: datetime = Field(alias="expiraEm")
    link_acesso: str | None = Field(default=None, alias="linkAcesso")

    model_config = ConfigDict(populate_by_name=True)


class PlataformaGestorCriadoRead(BaseModel):
    usuario: PlataformaUsuarioRead
    convite: PlataformaConviteRead


class PlataformaEmpresaOnboardingCreate(BaseModel):
    """Empresa + primeiro Gestor numa única operação ATÔMICA. Só campos reais do modelo; o Gestor é sempre `gestor` (nunca admin) e só desta empresa."""

    empresa: EmpresaCreate
    gestor: PlataformaGestorCreate

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PlataformaEmpresaOnboardingRead(BaseModel):
    empresa: PlataformaEmpresaRead
    gestor: PlataformaUsuarioRead
    convite: PlataformaConviteRead
    # `/e/<slug>/login` (absoluta quando APP_PUBLIC_URL está configurada). Sem token: é só o endereço da empresa.
    url_acesso: str = Field(alias="urlAcesso")

    model_config = ConfigDict(populate_by_name=True)
