from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import ensure_resource_empresa, ensure_same_empresa, require_admin, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.cargo import CargoCreate, CargoInativar, CargoResponse, CargoUpdate
from app.services.cargo_service import (
    CargoConflictError,
    CargoInvalidDataError,
    CargoInvalidEmpresaError,
    CargoInvalidTransitionError,
    CargoNotFoundError,
    CargoService,
)

router = APIRouter(prefix="/cargos", tags=["cargos"])
cargo_service = CargoService()

PATCH_ALLOWED_FIELDS = {"codigoInterno", "nome", "descricao"}


def handle_cargo_error(exc: Exception) -> None:
    if isinstance(exc, CargoNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, CargoConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, CargoInvalidEmpresaError | CargoInvalidDataError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, CargoInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    raise exc


@router.post("", response_model=CargoResponse, status_code=status.HTTP_201_CREATED)
def create_cargo(
    cargo: CargoCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(cargo.empresa_id, current_user)
    try:
        created = cargo_service.create_cargo(db, cargo, actor_usuario_id=current_user.id)
        return cargo_service.to_response(created)
    except Exception as exc:
        handle_cargo_error(exc)


@router.get("", response_model=list[CargoResponse])
def list_cargos(
    empresa_id: UUID = Query(alias="empresaId"),
    status_cargo: str | None = Query(default=None, alias="status"),
    busca: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(empresa_id, current_user)
    cargos = cargo_service.list_cargos(
        db,
        empresa_id=str(empresa_id),
        status=status_cargo,
        busca=busca,
        limit=limit,
        offset=offset,
    )
    return [cargo_service.to_response(cargo) for cargo in cargos]


@router.get("/{cargo_id}", response_model=CargoResponse)
def get_cargo(
    cargo_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        cargo = cargo_service.get_cargo(db, str(cargo_id))
        ensure_resource_empresa(cargo.empresa_id, current_user)
        return cargo_service.to_response(cargo)
    except Exception as exc:
        handle_cargo_error(exc)


@router.patch("/{cargo_id}", response_model=CargoResponse)
def update_cargo(
    cargo_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = cargo_service.get_cargo(db, str(cargo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_cargo_error(exc)

    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Cargo: {fields}",
        )

    try:
        data = CargoUpdate.model_validate(payload)
        cargo = cargo_service.update_cargo(db, str(cargo_id), data, actor_usuario_id=current_user.id)
        return cargo_service.to_response(cargo)
    except Exception as exc:
        handle_cargo_error(exc)


@router.post("/{cargo_id}/inativar", response_model=CargoResponse)
def inativar_cargo(
    cargo_id: UUID,
    payload: CargoInativar | None = None,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = cargo_service.get_cargo(db, str(cargo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        cargo = cargo_service.inativar_cargo(
            db,
            str(cargo_id),
            motivo_inativacao=payload.motivo_inativacao if payload else None,
            actor_usuario_id=current_user.id,
        )
        return cargo_service.to_response(cargo)
    except Exception as exc:
        handle_cargo_error(exc)


@router.post("/{cargo_id}/reativar", response_model=CargoResponse)
def reativar_cargo(
    cargo_id: UUID,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = cargo_service.get_cargo(db, str(cargo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        cargo = cargo_service.reativar_cargo(db, str(cargo_id), actor_usuario_id=current_user.id)
        return cargo_service.to_response(cargo)
    except Exception as exc:
        handle_cargo_error(exc)
