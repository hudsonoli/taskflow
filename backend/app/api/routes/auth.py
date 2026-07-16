from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.usuario import Usuario
from app.schemas.auth import AccessTokenResponse, AuthAlterarSenhaRequest, AuthLoginRequest, AuthMeResponse
from app.services.auth_service import (
    AuthInvalidCredentialsError,
    AuthPasswordValidationError,
    AuthService,
    INVALID_CREDENTIALS_MESSAGE,
)

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()


@router.post("/login", response_model=AccessTokenResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.login(
            db,
            empresa_codigo=payload.empresa_codigo,
            email=payload.email,
            senha=payload.senha,
        )
    except AuthInvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS_MESSAGE) from exc


@router.get("/me", response_model=AuthMeResponse)
def me(current_user: Usuario = Depends(get_current_user)):
    return auth_service.me(current_user)


@router.post("/alterar-senha", status_code=status.HTTP_204_NO_CONTENT)
def alterar_senha(
    payload: AuthAlterarSenhaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        auth_service.alterar_senha(
            db,
            usuario=current_user,
            senha_atual=payload.senha_atual,
            nova_senha=payload.nova_senha,
            confirmacao_senha=payload.confirmacao_senha,
        )
    except AuthInvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS_MESSAGE) from exc
    except AuthPasswordValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return None
