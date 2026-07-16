from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import ensure_resource_empresa, ensure_same_empresa, require_admin, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.usuario_departamento import (
    UsuarioDepartamentoCreate,
    UsuarioDepartamentoEncerrar,
    UsuarioDepartamentoPapel,
    UsuarioDepartamentoResponse,
    UsuarioDepartamentoStatus,
    UsuarioDepartamentoUpdate,
)
from app.services.usuario_departamento_service import (
    UsuarioDepartamentoConflictError,
    UsuarioDepartamentoInvalidDataError,
    UsuarioDepartamentoInvalidTransitionError,
    UsuarioDepartamentoNotFoundError,
    UsuarioDepartamentoService,
)

router = APIRouter(prefix="/vinculos/departamentos", tags=["vinculos-departamentos"])
usuario_departamento_service = UsuarioDepartamentoService()

PATCH_ALLOWED_FIELDS = {"papel", "principal"}


def handle_usuario_departamento_error(exc: Exception) -> None:
    if isinstance(exc, UsuarioDepartamentoNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, UsuarioDepartamentoConflictError | UsuarioDepartamentoInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, UsuarioDepartamentoInvalidDataError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    raise exc


@router.post("", response_model=UsuarioDepartamentoResponse, status_code=status.HTTP_201_CREATED)
def create_usuario_departamento(
    vinculo: UsuarioDepartamentoCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(vinculo.empresa_id, current_user)
    try:
        created = usuario_departamento_service.vincular_usuario_departamento(
            db,
            vinculo,
            actor_usuario_id=current_user.id,
        )
        return usuario_departamento_service.to_response(created)
    except Exception as exc:
        handle_usuario_departamento_error(exc)


@router.get("", response_model=list[UsuarioDepartamentoResponse])
def list_usuario_departamentos(
    empresa_id: UUID = Query(alias="empresaId"),
    usuario_id: UUID | None = Query(default=None, alias="usuarioId"),
    departamento_id: UUID | None = Query(default=None, alias="departamentoId"),
    papel: UsuarioDepartamentoPapel | None = Query(default=None),
    status_vinculo: UsuarioDepartamentoStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(empresa_id, current_user)
    try:
        vinculos = usuario_departamento_service.listar_vinculos(
            db,
            empresa_id=str(empresa_id),
            usuario_id=str(usuario_id) if usuario_id else None,
            departamento_id=str(departamento_id) if departamento_id else None,
            papel=papel,
            status=status_vinculo,
            limit=limit,
            offset=offset,
        )
        return [usuario_departamento_service.to_response(vinculo) for vinculo in vinculos]
    except Exception as exc:
        handle_usuario_departamento_error(exc)


@router.get("/{vinculo_id}", response_model=UsuarioDepartamentoResponse)
def get_usuario_departamento(
    vinculo_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        vinculo = usuario_departamento_service.obter_vinculo(db, str(vinculo_id))
        ensure_resource_empresa(vinculo.empresa_id, current_user)
        return usuario_departamento_service.to_response(vinculo)
    except Exception as exc:
        handle_usuario_departamento_error(exc)


@router.patch("/{vinculo_id}", response_model=UsuarioDepartamentoResponse)
def update_usuario_departamento(
    vinculo_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_departamento_service.obter_vinculo(db, str(vinculo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_usuario_departamento_error(exc)

    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Vínculo Usuário-Departamento: {fields}",
        )

    try:
        data = UsuarioDepartamentoUpdate.model_validate(payload)
        vinculo = usuario_departamento_service.alterar_vinculo(
            db,
            str(vinculo_id),
            data,
            actor_usuario_id=current_user.id,
        )
        return usuario_departamento_service.to_response(vinculo)
    except Exception as exc:
        handle_usuario_departamento_error(exc)


@router.post("/{vinculo_id}/encerrar", response_model=UsuarioDepartamentoResponse)
def encerrar_usuario_departamento(
    vinculo_id: UUID,
    payload: UsuarioDepartamentoEncerrar,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_departamento_service.obter_vinculo(db, str(vinculo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        vinculo = usuario_departamento_service.encerrar_vinculo(
            db,
            str(vinculo_id),
            payload,
            actor_usuario_id=current_user.id,
        )
        return usuario_departamento_service.to_response(vinculo)
    except Exception as exc:
        handle_usuario_departamento_error(exc)
