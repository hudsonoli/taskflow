from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import ensure_resource_empresa, ensure_same_empresa, require_admin, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.equipe import EquipeCreate, EquipeInativar, EquipeResponse, EquipeUpdate
from app.services.equipe_service import (
    EquipeConflictError,
    EquipeInvalidDataError,
    EquipeInvalidEmpresaError,
    EquipeInvalidTransitionError,
    EquipeNotFoundError,
    EquipeService,
)

router = APIRouter(prefix="/equipes", tags=["equipes"])
equipe_service = EquipeService()

PATCH_ALLOWED_FIELDS = {"codigoInterno", "nome", "descricao"}


def handle_equipe_error(exc: Exception) -> None:
    if isinstance(exc, EquipeNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, EquipeConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, EquipeInvalidEmpresaError | EquipeInvalidDataError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, EquipeInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    raise exc


@router.post("", response_model=EquipeResponse, status_code=status.HTTP_201_CREATED)
def create_equipe(
    equipe: EquipeCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(equipe.empresa_id, current_user)
    try:
        created = equipe_service.create_equipe(db, equipe, actor_usuario_id=current_user.id)
        return equipe_service.to_response(created)
    except Exception as exc:
        handle_equipe_error(exc)


@router.get("", response_model=list[EquipeResponse])
def list_equipes(
    empresa_id: UUID = Query(alias="empresaId"),
    status_equipe: str | None = Query(default=None, alias="status"),
    busca: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(empresa_id, current_user)
    equipes = equipe_service.list_equipes(
        db,
        empresa_id=str(empresa_id),
        status=status_equipe,
        busca=busca,
        limit=limit,
        offset=offset,
    )
    return [equipe_service.to_response(equipe) for equipe in equipes]


@router.get("/{equipe_id}", response_model=EquipeResponse)
def get_equipe(
    equipe_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        equipe = equipe_service.get_equipe(db, str(equipe_id))
        ensure_resource_empresa(equipe.empresa_id, current_user)
        return equipe_service.to_response(equipe)
    except Exception as exc:
        handle_equipe_error(exc)


@router.patch("/{equipe_id}", response_model=EquipeResponse)
def update_equipe(
    equipe_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = equipe_service.get_equipe(db, str(equipe_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_equipe_error(exc)

    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Equipe: {fields}",
        )

    try:
        data = EquipeUpdate.model_validate(payload)
        equipe = equipe_service.update_equipe(db, str(equipe_id), data, actor_usuario_id=current_user.id)
        return equipe_service.to_response(equipe)
    except Exception as exc:
        handle_equipe_error(exc)


@router.post("/{equipe_id}/inativar", response_model=EquipeResponse)
def inativar_equipe(
    equipe_id: UUID,
    payload: EquipeInativar | None = None,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = equipe_service.get_equipe(db, str(equipe_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        equipe = equipe_service.inativar_equipe(
            db,
            str(equipe_id),
            motivo_inativacao=payload.motivo_inativacao if payload else None,
            actor_usuario_id=current_user.id,
        )
        return equipe_service.to_response(equipe)
    except Exception as exc:
        handle_equipe_error(exc)


@router.post("/{equipe_id}/reativar", response_model=EquipeResponse)
def reativar_equipe(
    equipe_id: UUID,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = equipe_service.get_equipe(db, str(equipe_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        equipe = equipe_service.reativar_equipe(db, str(equipe_id), actor_usuario_id=current_user.id)
        return equipe_service.to_response(equipe)
    except Exception as exc:
        handle_equipe_error(exc)
