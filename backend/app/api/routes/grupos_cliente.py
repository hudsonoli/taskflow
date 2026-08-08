from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.grupo_cliente import (
    GrupoClienteArquivar,
    GrupoClienteCreate,
    GrupoClienteDiretorioRead,
    GrupoClienteRead,
    GrupoClienteUpdate,
)
from app.services.grupo_cliente_service import (
    GrupoClienteArquivadoConflictError,
    GrupoClienteConflictError,
    GrupoClienteInvalidTransitionError,
    GrupoClienteNotFoundError,
    GrupoClienteService,
)

router = APIRouter(prefix="/grupos-cliente", tags=["grupos-cliente"], dependencies=[Depends(get_current_user_password_ready)])
grupo_cliente_service = GrupoClienteService()


def handle_grupo_cliente_error(exc: Exception) -> None:
    if isinstance(exc, GrupoClienteNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, GrupoClienteArquivadoConflictError):
        # Ver docs/padrao-arquivamento.md — código padronizado + ID do arquivado pra UI
        # oferecer restaurar.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "GRUPO_CLIENTE_ARQUIVADO_EXISTENTE",
                "grupoClienteArquivadoId": exc.grupo_cliente_arquivado_id,
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, GrupoClienteConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, GrupoClienteInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=GrupoClienteRead, status_code=status.HTTP_201_CREATED)
def create_grupo_cliente(
    payload: GrupoClienteCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        created = grupo_cliente_service.create_grupo_cliente(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return grupo_cliente_service.to_read(created)
    except Exception as exc:
        handle_grupo_cliente_error(exc)


@router.get("", response_model=list[GrupoClienteRead])
def list_grupos_cliente(
    status_grupo: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    grupos = grupo_cliente_service.list_grupos_cliente(
        db,
        empresa_id=current_user.empresa_id,
        status=status_grupo,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [grupo_cliente_service.to_read(grupo) for grupo in grupos]


@router.get("/diretorio", response_model=list[GrupoClienteDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    grupos = grupo_cliente_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return [grupo_cliente_service.to_diretorio_read(grupo) for grupo in grupos]


@router.get("/{grupo_id}", response_model=GrupoClienteRead)
def get_grupo_cliente(
    grupo_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        grupo = grupo_cliente_service.get_grupo_cliente(db, str(grupo_id))
        ensure_resource_empresa(grupo.empresa_id, current_user)
        return grupo_cliente_service.to_read(grupo)
    except Exception as exc:
        handle_grupo_cliente_error(exc)


@router.patch("/{grupo_id}", response_model=GrupoClienteRead)
def update_grupo_cliente(
    grupo_id: UUID,
    payload: GrupoClienteUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existing = grupo_cliente_service.get_grupo_cliente(db, str(grupo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_grupo_cliente_error(exc)

    try:
        grupo = grupo_cliente_service.update_grupo_cliente(
            db, str(grupo_id), payload, actor_usuario_id=current_user.id
        )
        return grupo_cliente_service.to_read(grupo)
    except Exception as exc:
        handle_grupo_cliente_error(exc)


@router.post("/{grupo_id}/arquivar", response_model=GrupoClienteRead)
def arquivar_grupo_cliente(
    grupo_id: UUID,
    payload: GrupoClienteArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existing = grupo_cliente_service.get_grupo_cliente(db, str(grupo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_grupo_cliente_error(exc)

    try:
        grupo = grupo_cliente_service.arquivar_grupo_cliente(
            db,
            str(grupo_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return grupo_cliente_service.to_read(grupo)
    except Exception as exc:
        handle_grupo_cliente_error(exc)


@router.post("/{grupo_id}/restaurar", response_model=GrupoClienteRead)
def restaurar_grupo_cliente(
    grupo_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existing = grupo_cliente_service.get_grupo_cliente(db, str(grupo_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_grupo_cliente_error(exc)

    try:
        grupo = grupo_cliente_service.restaurar_grupo_cliente(db, str(grupo_id), actor_usuario_id=current_user.id)
        return grupo_cliente_service.to_read(grupo)
    except Exception as exc:
        handle_grupo_cliente_error(exc)
