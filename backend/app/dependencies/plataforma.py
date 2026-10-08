"""Autorização da Administração da Plataforma (`/plataforma/*`) — separada do RBAC tenant.

`require_platform_admin` é o ÚNICO guarda dessas rotas. Ele aceita SOMENTE o token `tipo="plataforma"` (o tenant
`access` é recusado por `decode_platform_token`, e o token de plataforma é recusado por `get_current_user`, que segue
exigindo `tipo="access"`) e, a cada requisição, reconfere no banco: a linha em `administradores_plataforma` existe e
está ativa, e o usuário existe e pode autenticar. Assim a revogação (`ativo=false`) vale já na requisição seguinte, mesmo
com o token ainda dentro do prazo. Nenhuma decisão usa e-mail, `perfil_base` ou `is_system_account`.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import AuthTokenError, decode_platform_token
from app.db.session import get_db
from app.dependencies.auth import bearer_scheme
from app.models.administrador_plataforma import AdministradorPlataforma
from app.models.usuario import Usuario
from app.repositories.administrador_plataforma_repository import AdministradorPlataformaRepository
from app.repositories.usuario_repository import UsuarioRepository

_administrador_repository = AdministradorPlataformaRepository()
_usuario_repository = UsuarioRepository()


@dataclass(frozen=True)
class ContextoPlataforma:
    administrador: AdministradorPlataforma
    usuario: Usuario


def require_platform_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> ContextoPlataforma:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    try:
        claims = decode_platform_token(credentials.credentials)
    except AuthTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc

    administrador = _administrador_repository.get_by_id(db, claims["adm"])
    usuario = _usuario_repository.get_by_id(db, claims["sub"])
    if (
        administrador is None
        or administrador.usuario_id != claims["sub"]
        or not administrador.ativo
        or usuario is None
        or usuario.status != "ativo"
        or not usuario.acesso_sistema
    ):
        # Revogada, usuário inativado ou token de outra pessoa: negado na hora (não é "token inválido": ele é bem
        # formado, mas a autoridade deixou de existir).
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return ContextoPlataforma(administrador=administrador, usuario=usuario)
