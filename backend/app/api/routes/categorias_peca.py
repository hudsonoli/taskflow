from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.categoria_peca import (
    CategoriaPecaArquivar,
    CategoriaPecaCreate,
    CategoriaPecaDiretorioRead,
    CategoriaPecaRead,
    CategoriaPecaUpdate,
)
from app.services.categoria_peca_service import (
    CategoriaPecaArquivadaConflictError,
    CategoriaPecaConflictError,
    CategoriaPecaInvalidTransitionError,
    CategoriaPecaNotFoundError,
    CategoriaPecaService,
)

router = APIRouter(
    prefix="/categorias-peca",
    tags=["categorias-peca"],
    dependencies=[Depends(get_current_user_password_ready)],
)
categoria_peca_service = CategoriaPecaService()


def handle_categoria_peca_error(exc: Exception) -> None:
    if isinstance(exc, CategoriaPecaNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, CategoriaPecaArquivadaConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CATEGORIA_PECA_ARQUIVADA_EXISTENTE",
                "categoriaPecaArquivadaId": exc.categoria_peca_arquivada_id,
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, CategoriaPecaConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, CategoriaPecaInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=CategoriaPecaRead, status_code=status.HTTP_201_CREATED)
def create_categoria_peca(
    payload: CategoriaPecaCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        criada = categoria_peca_service.create_categoria(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return categoria_peca_service.to_read(criada)
    except Exception as exc:
        handle_categoria_peca_error(exc)


@router.get("", response_model=list[CategoriaPecaRead])
def list_categorias_peca(
    status_categoria: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    categorias = categoria_peca_service.list_categorias(
        db,
        empresa_id=current_user.empresa_id,
        status=status_categoria,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [categoria_peca_service.to_read(item) for item in categorias]


# Diretório fica admin/gestor nesta fase — único consumidor é o formulário administrativo de
# Peça (mesmo raciocínio de /tipos-tarefa/diretorio).
@router.get("/diretorio", response_model=list[CategoriaPecaDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    categorias = categoria_peca_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return [categoria_peca_service.to_diretorio_read(item) for item in categorias]


@router.get("/{categoria_id}", response_model=CategoriaPecaRead)
def get_categoria_peca(
    categoria_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        categoria = categoria_peca_service.get_categoria(db, str(categoria_id))
        ensure_resource_empresa(categoria.empresa_id, current_user)
        return categoria_peca_service.to_read(categoria)
    except Exception as exc:
        handle_categoria_peca_error(exc)


@router.patch("/{categoria_id}", response_model=CategoriaPecaRead)
def update_categoria_peca(
    categoria_id: UUID,
    payload: CategoriaPecaUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = categoria_peca_service.get_categoria(db, str(categoria_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_categoria_peca_error(exc)

    try:
        categoria = categoria_peca_service.update_categoria(
            db, str(categoria_id), payload, actor_usuario_id=current_user.id
        )
        return categoria_peca_service.to_read(categoria)
    except Exception as exc:
        handle_categoria_peca_error(exc)


@router.post("/{categoria_id}/arquivar", response_model=CategoriaPecaRead)
def arquivar_categoria_peca(
    categoria_id: UUID,
    payload: CategoriaPecaArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = categoria_peca_service.get_categoria(db, str(categoria_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_categoria_peca_error(exc)

    try:
        categoria = categoria_peca_service.arquivar_categoria(
            db,
            str(categoria_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return categoria_peca_service.to_read(categoria)
    except Exception as exc:
        handle_categoria_peca_error(exc)


@router.post("/{categoria_id}/restaurar", response_model=CategoriaPecaRead)
def restaurar_categoria_peca(
    categoria_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = categoria_peca_service.get_categoria(db, str(categoria_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_categoria_peca_error(exc)

    try:
        categoria = categoria_peca_service.restaurar_categoria(
            db, str(categoria_id), actor_usuario_id=current_user.id
        )
        return categoria_peca_service.to_read(categoria)
    except Exception as exc:
        handle_categoria_peca_error(exc)
