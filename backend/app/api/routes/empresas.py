from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import ensure_same_empresa, require_admin, require_admin_or_gestor
from app.models.usuario import Usuario
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
def create_empresa(
    empresa: EmpresaCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Criação de Empresa indisponível nesta etapa")


@router.get("", response_model=list[EmpresaRead])
def list_empresas(
    status_empresa: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        empresa = empresa_service.get_empresa(db, current_user.empresa_id)
    except Exception as exc:
        handle_empresa_error(exc)
    if status_empresa and empresa.status != status_empresa:
        return []
    if offset > 0:
        return []
    return [empresa_service.to_read(empresa)][:limit]


@router.get("/{empresa_id}", response_model=EmpresaRead)
def get_empresa(
    empresa_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    if str(empresa_id) != current_user.empresa_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    try:
        empresa = empresa_service.get_empresa(db, str(empresa_id))
        return empresa_service.to_read(empresa)
    except Exception as exc:
        handle_empresa_error(exc)


@router.patch("/{empresa_id}", response_model=EmpresaRead)
def update_empresa(
    empresa_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(empresa_id, current_user)
    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Empresa: {fields}",
        )

    try:
        data = EmpresaUpdate.model_validate(payload)
        empresa = empresa_service.update_empresa(db, str(empresa_id), data, actor_usuario_id=current_user.id)
        return empresa_service.to_read(empresa)
    except Exception as exc:
        handle_empresa_error(exc)


@router.post("/{empresa_id}/inativar", response_model=EmpresaRead)
def inativar_empresa(
    empresa_id: UUID,
    payload: EmpresaInativar | None = None,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ciclo de vida de Empresa indisponível nesta etapa")


@router.post("/{empresa_id}/reativar", response_model=EmpresaRead)
def reativar_empresa(
    empresa_id: UUID,
    actor_usuario_id: str | None = Body(default=None, embed=True, alias="actorUsuarioId"),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ciclo de vida de Empresa indisponível nesta etapa")
