from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.authorization import require_admin, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.cliente import ClienteCreate, ClienteResponse, ClienteUpdate
from app.services.cliente_service import (
    ClienteConflictError,
    ClienteInvalidActorError,
    ClienteInvalidAgenciaError,
    ClienteInvalidDataError,
    ClienteInvalidEmpresaError,
    ClienteInvalidTransitionError,
    ClienteNotFoundError,
    ClienteService,
)

router = APIRouter(prefix="/clientes", tags=["clientes"])
cliente_service = ClienteService()

PATCH_ALLOWED_FIELDS = {
    "agenciaId",
    "codigoInterno",
    "tipoPessoa",
    "documento",
    "razaoSocial",
    "nomeFantasia",
    "nome",
    "sigla",
    "email",
    "telefone",
    "celular",
    "site",
    "codigoExterno",
    "observacoes",
}


class ClienteSuspenderRequest(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid")


class ClienteReativarRequest(BaseModel):
    motivo: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")


class ClienteInativarRequest(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid")


def handle_cliente_error(exc: Exception) -> None:
    if isinstance(exc, ClienteNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ClienteConflictError | ClienteInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ClienteInvalidDataError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, ClienteInvalidEmpresaError | ClienteInvalidAgenciaError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, ClienteInvalidActorError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    raise exc


@router.get("", response_model=list[ClienteResponse])
def list_clientes(
    status_cliente: str | None = Query(default=None, alias="status"),
    tipo_pessoa: str | None = Query(default=None, alias="tipoPessoa"),
    agencia_id: UUID | None = Query(default=None, alias="agenciaId"),
    busca: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        clientes = cliente_service.listar_clientes(
            db,
            empresa_id=current_user.empresa_id,
            status=status_cliente,
            tipo_pessoa=tipo_pessoa,
            agencia_id=str(agencia_id) if agencia_id else None,
            busca=busca,
            limit=limit,
            offset=offset,
        )
        return [cliente_service.to_response(cliente) for cliente in clientes]
    except Exception as exc:
        handle_cliente_error(exc)


@router.get("/{cliente_id}", response_model=ClienteResponse)
def get_cliente(
    cliente_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        cliente = cliente_service.obter_cliente(db, empresa_id=current_user.empresa_id, cliente_id=str(cliente_id))
        return cliente_service.to_response(cliente)
    except Exception as exc:
        handle_cliente_error(exc)


@router.post("", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def create_cliente(
    cliente: ClienteCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if str(cliente.empresa_id) != current_user.empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    try:
        created = cliente_service.criar_cliente(
            db,
            cliente,
            empresa_id=current_user.empresa_id,
            actor_usuario_id=current_user.id,
        )
        return cliente_service.to_response(created)
    except Exception as exc:
        handle_cliente_error(exc)


@router.patch("/{cliente_id}", response_model=ClienteResponse)
def update_cliente(
    cliente_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Cliente: {fields}",
        )

    try:
        data = ClienteUpdate.model_validate(payload)
        cliente = cliente_service.atualizar_cliente(
            db,
            empresa_id=current_user.empresa_id,
            cliente_id=str(cliente_id),
            data=data,
            actor_usuario_id=current_user.id,
        )
        return cliente_service.to_response(cliente)
    except Exception as exc:
        handle_cliente_error(exc)


@router.post("/{cliente_id}/suspender", response_model=ClienteResponse)
def suspender_cliente(
    cliente_id: UUID,
    payload: ClienteSuspenderRequest,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        cliente = cliente_service.suspender_cliente(
            db,
            empresa_id=current_user.empresa_id,
            cliente_id=str(cliente_id),
            motivo=payload.motivo,
            actor_usuario_id=current_user.id,
        )
        return cliente_service.to_response(cliente)
    except Exception as exc:
        handle_cliente_error(exc)


@router.post("/{cliente_id}/reativar", response_model=ClienteResponse)
def reativar_cliente(
    cliente_id: UUID,
    payload: ClienteReativarRequest | None = None,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        data = payload or ClienteReativarRequest()
        cliente = cliente_service.reativar_cliente(
            db,
            empresa_id=current_user.empresa_id,
            cliente_id=str(cliente_id),
            motivo=data.motivo,
            actor_usuario_id=current_user.id,
        )
        return cliente_service.to_response(cliente)
    except Exception as exc:
        handle_cliente_error(exc)


@router.post("/{cliente_id}/inativar", response_model=ClienteResponse)
def inativar_cliente(
    cliente_id: UUID,
    payload: ClienteInativarRequest,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        cliente = cliente_service.inativar_cliente(
            db,
            empresa_id=current_user.empresa_id,
            cliente_id=str(cliente_id),
            motivo=payload.motivo,
            actor_usuario_id=current_user.id,
        )
        return cliente_service.to_response(cliente)
    except Exception as exc:
        handle_cliente_error(exc)
