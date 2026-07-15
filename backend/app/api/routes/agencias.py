from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import ensure_resource_empresa, ensure_same_empresa, require_admin, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.agencia import AgenciaCreate, AgenciaInativar, AgenciaResponse, AgenciaUpdate
from app.services.agencia_service import (
    AgenciaConflictError,
    AgenciaInvalidEmpresaError,
    AgenciaInvalidTransitionError,
    AgenciaNotFoundError,
    AgenciaService,
)

router = APIRouter(prefix="/agencias", tags=["agencias"])
agencia_service = AgenciaService()

PATCH_ALLOWED_FIELDS = {"codigoInterno", "nome", "sigla", "descricao"}


def handle_agencia_error(exc: Exception) -> None:
    if isinstance(exc, AgenciaNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, AgenciaConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, AgenciaInvalidEmpresaError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, AgenciaInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=AgenciaResponse, status_code=status.HTTP_201_CREATED)
def create_agencia(
    agencia: AgenciaCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(agencia.empresa_id, current_user)
    try:
        created = agencia_service.create_agencia(db, agencia, actor_usuario_id=current_user.id)
        return agencia_service.to_response(created)
    except Exception as exc:
        handle_agencia_error(exc)


@router.get("", response_model=list[AgenciaResponse])
def list_agencias(
    empresa_id: UUID = Query(alias="empresaId"),
    status_agencia: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(empresa_id, current_user)
    agencias = agencia_service.list_agencias(
        db,
        empresa_id=str(empresa_id),
        status=status_agencia,
        limit=limit,
        offset=offset,
    )
    return [agencia_service.to_response(agencia) for agencia in agencias]


@router.get("/{agencia_id}", response_model=AgenciaResponse)
def get_agencia(
    agencia_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        agencia = agencia_service.get_agencia(db, str(agencia_id))
        ensure_resource_empresa(agencia.empresa_id, current_user)
        return agencia_service.to_response(agencia)
    except Exception as exc:
        handle_agencia_error(exc)


@router.patch("/{agencia_id}", response_model=AgenciaResponse)
def update_agencia(
    agencia_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = agencia_service.get_agencia(db, str(agencia_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_agencia_error(exc)

    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Agência: {fields}",
        )

    try:
        data = AgenciaUpdate.model_validate(payload)
        agencia = agencia_service.update_agencia(db, str(agencia_id), data, actor_usuario_id=current_user.id)
        return agencia_service.to_response(agencia)
    except Exception as exc:
        handle_agencia_error(exc)


@router.post("/{agencia_id}/inativar", response_model=AgenciaResponse)
def inativar_agencia(
    agencia_id: UUID,
    payload: AgenciaInativar | None = None,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = agencia_service.get_agencia(db, str(agencia_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        agencia = agencia_service.inativar_agencia(
            db,
            str(agencia_id),
            motivo_inativacao=payload.motivo_inativacao if payload else None,
            actor_usuario_id=current_user.id,
        )
        return agencia_service.to_response(agencia)
    except Exception as exc:
        handle_agencia_error(exc)


@router.post("/{agencia_id}/reativar", response_model=AgenciaResponse)
def reativar_agencia(
    agencia_id: UUID,
    actor_usuario_id: str | None = Body(default=None, embed=True, alias="actorUsuarioId"),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = agencia_service.get_agencia(db, str(agencia_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        agencia = agencia_service.reativar_agencia(db, str(agencia_id), actor_usuario_id=current_user.id)
        return agencia_service.to_response(agencia)
    except Exception as exc:
        handle_agencia_error(exc)
