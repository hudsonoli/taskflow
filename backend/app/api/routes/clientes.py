from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.cliente import (
    ClienteArquivar,
    ClienteCreate,
    ClienteDiretorioRead,
    ClienteRead,
    ClienteUpdate,
)
from app.services.cliente_service import (
    ClienteConflictError,
    ClienteGrupoInvalidoError,
    ClienteInvalidTransitionError,
    ClienteNotFoundError,
    ClienteResponsavelInvalidoError,
    ClienteService,
)

router = APIRouter(
    prefix="/clientes",
    tags=["clientes"],
    dependencies=[Depends(get_current_user_password_ready)],
)
cliente_service = ClienteService()


def handle_cliente_error(exc: Exception) -> None:
    if isinstance(exc, ClienteNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ClienteConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ClienteInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ClienteResponsavelInvalidoError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, ClienteGrupoInvalidoError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
def create_cliente(
    payload: ClienteCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        # Avisos calculados ANTES do INSERT, senão o próprio registro apareceria. Nunca
        # bloqueiam a criação — ver docstring de app/models/cliente.py.
        avisos = cliente_service.detectar_possiveis_duplicidades(
            db, empresa_id=current_user.empresa_id, nome=payload.nome, documento=payload.documento
        )
        criado = cliente_service.create_cliente(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return cliente_service.to_read(db, criado, avisos)
    except Exception as exc:
        handle_cliente_error(exc)


@router.get("", response_model=list[ClienteRead])
def list_clientes(
    status_cliente: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    grupo_cliente_id: UUID | None = Query(default=None, alias="grupoClienteId"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    clientes = cliente_service.list_clientes(
        db,
        empresa_id=current_user.empresa_id,
        status=status_cliente,
        search=search,
        grupo_cliente_id=str(grupo_cliente_id) if grupo_cliente_id else None,
        limit=limit,
        offset=offset,
    )
    return cliente_service.to_read_lote(db, clientes)


@router.get("/diretorio", response_model=list[ClienteDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    clientes = cliente_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return cliente_service.to_diretorio_read_lote(db, clientes)


@router.get("/{cliente_id}", response_model=ClienteRead)
def get_cliente(
    cliente_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        cliente = cliente_service.get_cliente(db, str(cliente_id))
        ensure_resource_empresa(cliente.empresa_id, current_user)
        return cliente_service.to_read(db, cliente)
    except Exception as exc:
        handle_cliente_error(exc)


@router.patch("/{cliente_id}", response_model=ClienteRead)
def update_cliente(
    cliente_id: UUID,
    payload: ClienteUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = cliente_service.get_cliente(db, str(cliente_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_cliente_error(exc)

    try:
        avisos = cliente_service.detectar_possiveis_duplicidades(
            db,
            empresa_id=existente.empresa_id,
            nome=payload.nome if payload.nome is not None else existente.nome,
            documento=payload.documento if payload.documento is not None else existente.documento,
            excluir_id=existente.id,
        )
        cliente = cliente_service.update_cliente(
            db, str(cliente_id), payload, actor_usuario_id=current_user.id
        )
        return cliente_service.to_read(db, cliente, avisos)
    except Exception as exc:
        handle_cliente_error(exc)


# "Excluir" = arquivar (soft-delete permanente). Nunca há delete físico de cliente.
@router.post("/{cliente_id}/arquivar", response_model=ClienteRead)
def arquivar_cliente(
    cliente_id: UUID,
    payload: ClienteArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = cliente_service.get_cliente(db, str(cliente_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_cliente_error(exc)

    try:
        cliente = cliente_service.arquivar_cliente(
            db,
            str(cliente_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return cliente_service.to_read(db, cliente)
    except Exception as exc:
        handle_cliente_error(exc)


@router.post("/{cliente_id}/restaurar", response_model=ClienteRead)
def restaurar_cliente(
    cliente_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = cliente_service.get_cliente(db, str(cliente_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_cliente_error(exc)

    try:
        cliente = cliente_service.restaurar_cliente(
            db, str(cliente_id), actor_usuario_id=current_user.id
        )
        return cliente_service.to_read(db, cliente)
    except Exception as exc:
        handle_cliente_error(exc)
