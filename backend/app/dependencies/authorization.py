from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.models.usuario import Usuario

ADMIN = "admin"
GESTOR = "gestor"
OPERADOR = "operador"


def require_profiles(*profiles: str) -> Callable[[Usuario], Usuario]:
    allowed_profiles = set(profiles)

    def dependency(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.perfil_base not in allowed_profiles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
        return current_user

    return dependency


require_admin = require_profiles(ADMIN)
require_admin_or_gestor = require_profiles(ADMIN, GESTOR)


def ensure_same_empresa(empresa_id: str | UUID, current_user: Usuario) -> None:
    if str(empresa_id) != current_user.empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")


def ensure_resource_empresa(resource_empresa_id: str | UUID, current_user: Usuario) -> None:
    if str(resource_empresa_id) != current_user.empresa_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso não encontrado")
