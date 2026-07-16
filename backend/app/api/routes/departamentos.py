from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import ensure_resource_empresa, ensure_same_empresa, require_admin, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.departamento import DepartamentoCreate, DepartamentoInativar, DepartamentoResponse, DepartamentoUpdate
from app.services.departamento_service import (
    DepartamentoConflictError,
    DepartamentoInvalidDataError,
    DepartamentoInvalidEmpresaError,
    DepartamentoInvalidTransitionError,
    DepartamentoNotFoundError,
    DepartamentoService,
)

router = APIRouter(prefix="/departamentos", tags=["departamentos"])
departamento_service = DepartamentoService()

PATCH_ALLOWED_FIELDS = {"codigoInterno", "nome", "descricao"}


def handle_departamento_error(exc: Exception) -> None:
    if isinstance(exc, DepartamentoNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, DepartamentoConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, DepartamentoInvalidEmpresaError | DepartamentoInvalidDataError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, DepartamentoInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    raise exc


@router.post("", response_model=DepartamentoResponse, status_code=status.HTTP_201_CREATED)
def create_departamento(
    departamento: DepartamentoCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(departamento.empresa_id, current_user)
    try:
        created = departamento_service.create_departamento(db, departamento, actor_usuario_id=current_user.id)
        return departamento_service.to_response(created)
    except Exception as exc:
        handle_departamento_error(exc)


@router.get("", response_model=list[DepartamentoResponse])
def list_departamentos(
    empresa_id: UUID = Query(alias="empresaId"),
    status_departamento: str | None = Query(default=None, alias="status"),
    busca: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(empresa_id, current_user)
    departamentos = departamento_service.list_departamentos(
        db,
        empresa_id=str(empresa_id),
        status=status_departamento,
        busca=busca,
        limit=limit,
        offset=offset,
    )
    return [departamento_service.to_response(departamento) for departamento in departamentos]


@router.get("/{departamento_id}", response_model=DepartamentoResponse)
def get_departamento(
    departamento_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        departamento = departamento_service.get_departamento(db, str(departamento_id))
        ensure_resource_empresa(departamento.empresa_id, current_user)
        return departamento_service.to_response(departamento)
    except Exception as exc:
        handle_departamento_error(exc)


@router.patch("/{departamento_id}", response_model=DepartamentoResponse)
def update_departamento(
    departamento_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = departamento_service.get_departamento(db, str(departamento_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_departamento_error(exc)

    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Departamento: {fields}",
        )

    try:
        data = DepartamentoUpdate.model_validate(payload)
        departamento = departamento_service.update_departamento(
            db,
            str(departamento_id),
            data,
            actor_usuario_id=current_user.id,
        )
        return departamento_service.to_response(departamento)
    except Exception as exc:
        handle_departamento_error(exc)


@router.post("/{departamento_id}/inativar", response_model=DepartamentoResponse)
def inativar_departamento(
    departamento_id: UUID,
    payload: DepartamentoInativar | None = None,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = departamento_service.get_departamento(db, str(departamento_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        departamento = departamento_service.inativar_departamento(
            db,
            str(departamento_id),
            motivo_inativacao=payload.motivo_inativacao if payload else None,
            actor_usuario_id=current_user.id,
        )
        return departamento_service.to_response(departamento)
    except Exception as exc:
        handle_departamento_error(exc)


@router.post("/{departamento_id}/reativar", response_model=DepartamentoResponse)
def reativar_departamento(
    departamento_id: UUID,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = departamento_service.get_departamento(db, str(departamento_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        departamento = departamento_service.reativar_departamento(db, str(departamento_id), actor_usuario_id=current_user.id)
        return departamento_service.to_response(departamento)
    except Exception as exc:
        handle_departamento_error(exc)
