from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.usuario import Usuario
from app.repositories.usuario_credencial_repository import UsuarioCredencialRepository
from app.services.auth_service import AuthService, AuthUnauthorizedError

bearer_scheme = HTTPBearer(auto_error=False)
auth_service = AuthService()
usuario_credencial_repository = UsuarioCredencialRepository()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    try:
        return auth_service.get_current_user_from_token(db, credentials.credentials)
    except AuthUnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc


def get_current_user_password_ready(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Usuario:
    """Bloqueia o restante da aplicação enquanto a troca de senha obrigatória (senha
    temporária de seed/reset) não for concluída. Só /auth/me e /auth/alterar-senha ficam
    fora desse gate — o resto de /usuarios/* passa por aqui."""
    credencial = usuario_credencial_repository.get_by_usuario_id(db, current_user.id)
    if credencial is not None and credencial.senha_deve_ser_alterada:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "SENHA_TROCA_OBRIGATORIA", "message": "Troca de senha obrigatória"},
        )
    return current_user
