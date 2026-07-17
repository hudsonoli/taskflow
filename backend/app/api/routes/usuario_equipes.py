from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import ensure_resource_empresa, ensure_same_empresa, require_admin, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.usuario_equipe import (
    UsuarioEquipeCreate,
    UsuarioEquipeEncerrar,
    UsuarioEquipePapel,
    UsuarioEquipeResponse,
    UsuarioEquipeStatus,
    UsuarioEquipeUpdate,
)
from app.services.usuario_equipe_service import (
    UsuarioEquipeConflictError,
    UsuarioEquipeInvalidDataError,
    UsuarioEquipeInvalidTransitionError,
    UsuarioEquipeNotFoundError,
    UsuarioEquipeService,
)

router = APIRouter(prefix="/vinculos/equipes", tags=["vinculos-equipes"])
usuario_equipe_service = UsuarioEquipeService()

PATCH_ALLOWED_FIELDS = {"papel", "principal"}


def handle_usuario_equipe_error(exc: Exception) -> None:
    if isinstance(exc, UsuarioEquipeNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, UsuarioEquipeConflictError | UsuarioEquipeInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, UsuarioEquipeInvalidDataError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    raise exc


@router.post("", response_model=UsuarioEquipeResponse, status_code=status.HTTP_201_CREATED)
def create_usuario_equipe(
    vinculo: UsuarioEquipeCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(vinculo.empresa_id, current_user)
    try:
        created = usuario_equipe_service.vincular_usuario_equipe(
            db,
            vinculo,
            actor_usuario_id=current_user.id,
        )
        return usuario_equipe_service.to_response(created)
    except Exception as exc:
        handle_usuario_equipe_error(exc)


@router.get("", response_model=list[UsuarioEquipeResponse])
def list_usuario_equipes(
    empresa_id: UUID = Query(alias="empresaId"),
    usuario_id: UUID | None = Query(default=None, alias="usuarioId"),
    equipe_id: UUID | None = Query(default=None, alias="equipeId"),
    papel: UsuarioEquipePapel | None = Query(default=None),
    status_vinculo: UsuarioEquipeStatus | None = Query(default=None, alias="status"),
    principal: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(empresa_id, current_user)
    try:
        vinculos = usuario_equipe_service.listar_vinculos(
            db,
            empresa_id=str(empresa_id),
            usuario_id=str(usuario_id) if usuario_id else None,
            equipe_id=str(equipe_id) if equipe_id else None,
            papel=papel,
            status=status_vinculo,
            principal=principal,
            limit=limit,
            offset=offset,
        )
        return [usuario_equipe_service.to_response(vinculo) for vinculo in vinculos]
    except Exception as exc:
        handle_usuario_equipe_error(exc)


@router.get("/{vinculo_id}", response_model=UsuarioEquipeResponse)
def get_usuario_equipe(
    vinculo_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        vinculo = usuario_equipe_service.obter_vinculo(db, str(vinculo_id))
        ensure_resource_empresa(vinculo.empresa_id, current_user)
        return usuario_equipe_service.to_response(vinculo)
    except Exception as exc:
        handle_usuario_equipe_error(exc)


@router.patch("/{vinculo_id}", response_model=UsuarioEquipeResponse)
def update_usuario_equipe(
    vinculo_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_equipe_service.obter_vinculo(db, str(vinculo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_usuario_equipe_error(exc)

    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Vínculo Usuário-Equipe: {fields}",
        )

    try:
        data = UsuarioEquipeUpdate.model_validate(payload)
        vinculo = usuario_equipe_service.alterar_vinculo(
            db,
            str(vinculo_id),
            data,
            actor_usuario_id=current_user.id,
        )
        return usuario_equipe_service.to_response(vinculo)
    except Exception as exc:
        handle_usuario_equipe_error(exc)


@router.post("/{vinculo_id}/encerrar", response_model=UsuarioEquipeResponse)
def encerrar_usuario_equipe(
    vinculo_id: UUID,
    payload: UsuarioEquipeEncerrar | None = None,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_equipe_service.obter_vinculo(db, str(vinculo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        data = payload or UsuarioEquipeEncerrar()
        vinculo = usuario_equipe_service.encerrar_vinculo(
            db,
            str(vinculo_id),
            data,
            actor_usuario_id=current_user.id,
        )
        return usuario_equipe_service.to_response(vinculo)
    except Exception as exc:
        handle_usuario_equipe_error(exc)
