from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AccessTokenClaims(BaseModel):
    sub: UUID
    empresa_id: UUID
    perfil_base: Literal["admin", "gestor", "operador"]
    iat: datetime | int | float
    exp: datetime | int | float
    tipo: Literal["access"] = "access"

    model_config = ConfigDict(populate_by_name=True)


class AccessTokenResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    token_type: Literal["bearer"] = Field(default="bearer", alias="tokenType")

    model_config = ConfigDict(populate_by_name=True)


class AuthLoginRequest(BaseModel):
    empresa_codigo: str = Field(alias="empresaCodigo", min_length=1, max_length=64)
    email: str = Field(min_length=1, max_length=255)
    senha: str = Field(min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class AuthAlterarSenhaRequest(BaseModel):
    senha_atual: str = Field(alias="senhaAtual", min_length=1)
    nova_senha: str = Field(alias="novaSenha", min_length=8)
    confirmacao_senha: str = Field(alias="confirmacaoSenha", min_length=8)

    model_config = ConfigDict(populate_by_name=True)


class AuthMeResponse(BaseModel):
    usuario_id: UUID = Field(alias="usuarioId")
    empresa_id: UUID = Field(alias="empresaId")
    nome: str
    perfil_base: Literal["admin", "gestor", "operador"] = Field(alias="perfilBase")
    acesso_sistema: bool = Field(alias="acessoSistema")
    status: Literal["ativo", "inativo", "bloqueado", "arquivado"]

    model_config = ConfigDict(populate_by_name=True)
