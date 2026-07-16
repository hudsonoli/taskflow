from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import ensure_resource_empresa, ensure_same_empresa, require_admin, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioInativar, UsuarioRead, UsuarioUpdate
from app.services.usuario_service import (
    UsuarioConflictError,
    UsuarioInvalidEmpresaError,
    UsuarioInvalidTransitionError,
    UsuarioNotFoundError,
    UsuarioService,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
usuario_service = UsuarioService()

PATCH_ALLOWED_FIELDS = {"codigoInterno", "nome", "email", "perfilBase", "acessoSistema"}


def handle_usuario_error(exc: Exception) -> None:
    if isinstance(exc, UsuarioNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, UsuarioConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, UsuarioInvalidEmpresaError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, UsuarioInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def create_usuario(
    usuario: UsuarioCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(usuario.empresa_id, current_user)
    try:
        created = usuario_service.create_usuario(db, usuario, actor_usuario_id=current_user.id)
        return usuario_service.to_read(created)
    except Exception as exc:
        handle_usuario_error(exc)


@router.get("", response_model=list[UsuarioRead])
def list_usuarios(
    empresa_id: UUID = Query(alias="empresaId"),
    status_usuario: str | None = Query(default=None, alias="status"),
    perfil_base: str | None = Query(default=None, alias="perfilBase"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(empresa_id, current_user)
    usuarios = usuario_service.list_usuarios(
        db,
        empresa_id=str(empresa_id),
        status=status_usuario,
        perfil_base=perfil_base,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [usuario_service.to_read(usuario) for usuario in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioRead)
def get_usuario(
    usuario_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        usuario = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(usuario.empresa_id, current_user)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.patch("/{usuario_id}", response_model=UsuarioRead)
def update_usuario(
    usuario_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_usuario_error(exc)

    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Usuário: {fields}",
        )

    try:
        data = UsuarioUpdate.model_validate(payload)
        usuario = usuario_service.update_usuario(db, str(usuario_id), data, actor_usuario_id=current_user.id)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/inativar", response_model=UsuarioRead)
def inativar_usuario(
    usuario_id: UUID,
    payload: UsuarioInativar | None = None,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if str(usuario_id) == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.inativar_usuario(
            db,
            str(usuario_id),
            motivo_inativacao=payload.motivo_inativacao if payload else None,
            actor_usuario_id=current_user.id,
        )
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/reativar", response_model=UsuarioRead)
def reativar_usuario(
    usuario_id: UUID,
    actor_usuario_id: str | None = Body(default=None, embed=True, alias="actorUsuarioId"),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.reativar_usuario(db, str(usuario_id), actor_usuario_id=current_user.id)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/bloquear", response_model=UsuarioRead)
def bloquear_usuario(
    usuario_id: UUID,
    actor_usuario_id: str | None = Body(default=None, embed=True, alias="actorUsuarioId"),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if str(usuario_id) == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.bloquear_usuario(db, str(usuario_id), actor_usuario_id=current_user.id)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/desbloquear", response_model=UsuarioRead)
def desbloquear_usuario(
    usuario_id: UUID,
    actor_usuario_id: str | None = Body(default=None, embed=True, alias="actorUsuarioId"),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.desbloquear_usuario(db, str(usuario_id), actor_usuario_id=current_user.id)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)
