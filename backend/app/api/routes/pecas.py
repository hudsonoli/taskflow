from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.peca import PecaArquivar, PecaCreate, PecaDiretorioRead, PecaRead, PecaUpdate
from app.services.peca_service import (
    PecaCategoriaInvalidaError,
    PecaInvalidTransitionError,
    PecaNotFoundError,
    PecaService,
)

router = APIRouter(
    prefix="/pecas",
    tags=["pecas"],
    dependencies=[Depends(get_current_user_password_ready)],
)
peca_service = PecaService()


def handle_peca_error(exc: Exception) -> None:
    if isinstance(exc, PecaNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PecaCategoriaInvalidaError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, PecaInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=PecaRead, status_code=status.HTTP_201_CREATED)
def create_peca(
    payload: PecaCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        criada = peca_service.create_peca(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return peca_service.to_read(db, criada)
    except Exception as exc:
        handle_peca_error(exc)


@router.get("", response_model=list[PecaRead])
def list_pecas(
    status_peca: str | None = Query(default=None, alias="status"),
    categoria_id: UUID | None = Query(default=None, alias="categoriaId"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    pecas = peca_service.list_pecas(
        db,
        empresa_id=current_user.empresa_id,
        status=status_peca,
        categoria_id=str(categoria_id) if categoria_id else None,
        search=search,
        limit=limit,
        offset=offset,
    )
    return peca_service.to_read_lote(db, pecas)


# Diretório enxuto — contrato pronto pra um futuro consumidor operacional (ver docstring de
# PecaDiretorioRead). Admin/gestor nesta fase, mesmo raciocínio de /tipos-tarefa/diretorio:
# único consumidor hoje é a tela administrativa.
@router.get("/diretorio", response_model=list[PecaDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    pecas = peca_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return [peca_service.to_diretorio_read(item) for item in pecas]


@router.get("/{peca_id}", response_model=PecaRead)
def get_peca(
    peca_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        peca = peca_service.get_peca(db, str(peca_id))
        ensure_resource_empresa(peca.empresa_id, current_user)
        return peca_service.to_read(db, peca)
    except Exception as exc:
        handle_peca_error(exc)


@router.patch("/{peca_id}", response_model=PecaRead)
def update_peca(
    peca_id: UUID,
    payload: PecaUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = peca_service.get_peca(db, str(peca_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_peca_error(exc)

    try:
        peca = peca_service.update_peca(db, str(peca_id), payload, actor_usuario_id=current_user.id)
        return peca_service.to_read(db, peca)
    except Exception as exc:
        handle_peca_error(exc)


@router.post("/{peca_id}/arquivar", response_model=PecaRead)
def arquivar_peca(
    peca_id: UUID,
    payload: PecaArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = peca_service.get_peca(db, str(peca_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_peca_error(exc)

    try:
        peca = peca_service.arquivar_peca(
            db, str(peca_id), motivo_arquivamento=payload.motivo_arquivamento, actor_usuario_id=current_user.id
        )
        return peca_service.to_read(db, peca)
    except Exception as exc:
        handle_peca_error(exc)


@router.post("/{peca_id}/restaurar", response_model=PecaRead)
def restaurar_peca(
    peca_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = peca_service.get_peca(db, str(peca_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_peca_error(exc)

    try:
        peca = peca_service.restaurar_peca(db, str(peca_id), actor_usuario_id=current_user.id)
        return peca_service.to_read(db, peca)
    except Exception as exc:
        handle_peca_error(exc)
