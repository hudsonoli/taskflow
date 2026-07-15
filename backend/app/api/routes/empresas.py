from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.empresa import EmpresaCreate, EmpresaInativar, EmpresaRead, EmpresaUpdate
from app.services.empresa_service import (
    EmpresaConflictError,
    EmpresaInvalidTransitionError,
    EmpresaNotFoundError,
    EmpresaService,
)

router = APIRouter(prefix="/empresas", tags=["empresas"])
empresa_service = EmpresaService()

PATCH_ALLOWED_FIELDS = {"nome", "documento", "codigoInterno"}


def handle_empresa_error(exc: Exception) -> None:
    if isinstance(exc, EmpresaNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, EmpresaConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, EmpresaInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=EmpresaRead, status_code=status.HTTP_201_CREATED)
def create_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    try:
        created = empresa_service.create_empresa(db, empresa)
        return empresa_service.to_read(created)
    except Exception as exc:
        handle_empresa_error(exc)


@router.get("", response_model=list[EmpresaRead])
def list_empresas(
    status_empresa: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    empresas = empresa_service.list_empresas(db, status=status_empresa, limit=limit, offset=offset)
    return [empresa_service.to_read(empresa) for empresa in empresas]


@router.get("/{empresa_id}", response_model=EmpresaRead)
def get_empresa(empresa_id: UUID, db: Session = Depends(get_db)):
    try:
        empresa = empresa_service.get_empresa(db, str(empresa_id))
        return empresa_service.to_read(empresa)
    except Exception as exc:
        handle_empresa_error(exc)


@router.patch("/{empresa_id}", response_model=EmpresaRead)
def update_empresa(
    empresa_id: UUID,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Empresa: {fields}",
        )

    try:
        data = EmpresaUpdate.model_validate(payload)
        empresa = empresa_service.update_empresa(db, str(empresa_id), data)
        return empresa_service.to_read(empresa)
    except Exception as exc:
        handle_empresa_error(exc)


@router.post("/{empresa_id}/inativar", response_model=EmpresaRead)
def inativar_empresa(
    empresa_id: UUID,
    payload: EmpresaInativar | None = None,
    db: Session = Depends(get_db),
):
    try:
        empresa = empresa_service.inativar_empresa(
            db,
            str(empresa_id),
            motivo_inativacao=payload.motivo_inativacao if payload else None,
            actor_usuario_id=payload.actor_usuario_id if payload else None,
        )
        return empresa_service.to_read(empresa)
    except Exception as exc:
        handle_empresa_error(exc)


@router.post("/{empresa_id}/reativar", response_model=EmpresaRead)
def reativar_empresa(
    empresa_id: UUID,
    actor_usuario_id: str | None = Body(default=None, embed=True, alias="actorUsuarioId"),
    db: Session = Depends(get_db),
):
    try:
        empresa = empresa_service.reativar_empresa(db, str(empresa_id), actor_usuario_id=actor_usuario_id)
        return empresa_service.to_read(empresa)
    except Exception as exc:
        handle_empresa_error(exc)
