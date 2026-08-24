from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.modelo_campanha import (
    ModeloCampanhaArquivar,
    ModeloCampanhaCreate,
    ModeloCampanhaDiretorioRead,
    ModeloCampanhaRead,
    ModeloCampanhaUpdate,
)
from app.services.modelo_campanha_service import (
    ModeloCampanhaArquivadoConflictError,
    ModeloCampanhaConflictError,
    ModeloCampanhaInvalidTransitionError,
    ModeloCampanhaNotFoundError,
    ModeloCampanhaReferenciaInvalidaError,
    ModeloCampanhaService,
)

router = APIRouter(
    prefix="/modelos-campanha",
    tags=["modelos-campanha"],
    dependencies=[Depends(get_current_user_password_ready)],
)
modelo_campanha_service = ModeloCampanhaService()


def handle_modelo_campanha_error(exc: Exception) -> None:
    if isinstance(exc, ModeloCampanhaNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ModeloCampanhaArquivadoConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "MODELO_CAMPANHA_ARQUIVADO_EXISTENTE",
                "modeloCampanhaArquivadoId": exc.modelo_campanha_arquivado_id,
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, ModeloCampanhaConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ModeloCampanhaInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ModeloCampanhaReferenciaInvalidaError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=ModeloCampanhaRead, status_code=status.HTTP_201_CREATED)
def create_modelo_campanha(
    payload: ModeloCampanhaCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        criado = modelo_campanha_service.create_modelo(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return modelo_campanha_service.to_read(db, criado)
    except Exception as exc:
        handle_modelo_campanha_error(exc)


@router.get("", response_model=list[ModeloCampanhaRead])
def list_modelos_campanha(
    status_modelo: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    modelos = modelo_campanha_service.list_modelos(
        db,
        empresa_id=current_user.empresa_id,
        status=status_modelo,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [modelo_campanha_service.to_read(db, item) for item in modelos]


# Diretório fica admin/gestor nesta fase — diferente de WorkflowModelo/TipoTarefa (que abrem
# pra qualquer autenticado porque NovaDemandaModal consome), aqui o único consumidor real
# (biblioteca administrativa) já é área admin/gestor — ver relatório da Fase 2G.5, item 19.
@router.get("/diretorio", response_model=list[ModeloCampanhaDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    modelos = modelo_campanha_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return [modelo_campanha_service.to_diretorio_read(item) for item in modelos]


@router.get("/{modelo_id}", response_model=ModeloCampanhaRead)
def get_modelo_campanha(
    modelo_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        modelo = modelo_campanha_service.get_modelo(db, str(modelo_id))
        ensure_resource_empresa(modelo.empresa_id, current_user)
        return modelo_campanha_service.to_read(db, modelo)
    except Exception as exc:
        handle_modelo_campanha_error(exc)


@router.patch("/{modelo_id}", response_model=ModeloCampanhaRead)
def update_modelo_campanha(
    modelo_id: UUID,
    payload: ModeloCampanhaUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = modelo_campanha_service.get_modelo(db, str(modelo_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_modelo_campanha_error(exc)

    try:
        modelo = modelo_campanha_service.update_modelo(
            db, str(modelo_id), payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return modelo_campanha_service.to_read(db, modelo)
    except Exception as exc:
        handle_modelo_campanha_error(exc)


@router.post("/{modelo_id}/arquivar", response_model=ModeloCampanhaRead)
def arquivar_modelo_campanha(
    modelo_id: UUID,
    payload: ModeloCampanhaArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = modelo_campanha_service.get_modelo(db, str(modelo_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_modelo_campanha_error(exc)

    try:
        modelo = modelo_campanha_service.arquivar_modelo(
            db, str(modelo_id), motivo_arquivamento=payload.motivo_arquivamento, actor_usuario_id=current_user.id
        )
        return modelo_campanha_service.to_read(db, modelo)
    except Exception as exc:
        handle_modelo_campanha_error(exc)


@router.post("/{modelo_id}/restaurar", response_model=ModeloCampanhaRead)
def restaurar_modelo_campanha(
    modelo_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = modelo_campanha_service.get_modelo(db, str(modelo_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_modelo_campanha_error(exc)

    try:
        modelo = modelo_campanha_service.restaurar_modelo(db, str(modelo_id), actor_usuario_id=current_user.id)
        return modelo_campanha_service.to_read(db, modelo)
    except Exception as exc:
        handle_modelo_campanha_error(exc)
