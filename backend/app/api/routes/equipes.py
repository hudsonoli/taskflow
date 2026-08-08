from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.equipe import (
    EquipeArquivar,
    EquipeCreate,
    EquipeDiretorioRead,
    EquipeRead,
    EquipeUpdate,
)
from app.services.equipe_service import (
    EquipeArquivadaConflictError,
    EquipeConflictError,
    EquipeDepartamentoInvalidoError,
    EquipeInvalidTransitionError,
    EquipeMembroInvalidoError,
    EquipeNotFoundError,
    EquipeService,
)

router = APIRouter(
    prefix="/equipes",
    tags=["equipes"],
    dependencies=[Depends(get_current_user_password_ready)],
)
equipe_service = EquipeService()


def handle_equipe_error(exc: Exception) -> None:
    if isinstance(exc, EquipeNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, EquipeArquivadaConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EQUIPE_ARQUIVADA_EXISTENTE",
                "equipeArquivadaId": exc.equipe_arquivada_id,
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, EquipeConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, EquipeInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, (EquipeDepartamentoInvalidoError, EquipeMembroInvalidoError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=EquipeRead, status_code=status.HTTP_201_CREATED)
def create_equipe(
    payload: EquipeCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        criada = equipe_service.create_equipe(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return equipe_service.to_read(db, criada)
    except Exception as exc:
        handle_equipe_error(exc)


@router.get("", response_model=list[EquipeRead])
def list_equipes(
    status_equipe: str | None = Query(default=None, alias="status"),
    departamento_id: UUID | None = Query(default=None, alias="departamentoId"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    equipes = equipe_service.list_equipes(
        db,
        empresa_id=current_user.empresa_id,
        status=status_equipe,
        departamento_id=str(departamento_id) if departamento_id else None,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [equipe_service.to_read(db, item) for item in equipes]


@router.get("/diretorio", response_model=list[EquipeDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    equipes = equipe_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return [equipe_service.to_diretorio_read(db, item) for item in equipes]


@router.get("/{equipe_id}", response_model=EquipeRead)
def get_equipe(
    equipe_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        equipe = equipe_service.get_equipe(db, str(equipe_id))
        ensure_resource_empresa(equipe.empresa_id, current_user)
        return equipe_service.to_read(db, equipe)
    except Exception as exc:
        handle_equipe_error(exc)


@router.patch("/{equipe_id}", response_model=EquipeRead)
def update_equipe(
    equipe_id: UUID,
    payload: EquipeUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = equipe_service.get_equipe(db, str(equipe_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_equipe_error(exc)

    try:
        equipe = equipe_service.update_equipe(db, str(equipe_id), payload, actor_usuario_id=current_user.id)
        return equipe_service.to_read(db, equipe)
    except Exception as exc:
        handle_equipe_error(exc)


@router.post("/{equipe_id}/arquivar", response_model=EquipeRead)
def arquivar_equipe(
    equipe_id: UUID,
    payload: EquipeArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = equipe_service.get_equipe(db, str(equipe_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_equipe_error(exc)

    try:
        equipe = equipe_service.arquivar_equipe(
            db,
            str(equipe_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return equipe_service.to_read(db, equipe)
    except Exception as exc:
        handle_equipe_error(exc)


@router.post("/{equipe_id}/restaurar", response_model=EquipeRead)
def restaurar_equipe(
    equipe_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = equipe_service.get_equipe(db, str(equipe_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_equipe_error(exc)

    try:
        equipe = equipe_service.restaurar_equipe(db, str(equipe_id), actor_usuario_id=current_user.id)
        return equipe_service.to_read(db, equipe)
    except Exception as exc:
        handle_equipe_error(exc)
