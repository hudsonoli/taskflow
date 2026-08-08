from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.fornecedor import (
    FornecedorArquivar,
    FornecedorCreate,
    FornecedorDiretorioRead,
    FornecedorRead,
    FornecedorUpdate,
)
from app.services.fornecedor_service import (
    FornecedorConflictError,
    FornecedorInvalidTransitionError,
    FornecedorNotFoundError,
    FornecedorService,
)

router = APIRouter(
    prefix="/fornecedores",
    tags=["fornecedores"],
    dependencies=[Depends(get_current_user_password_ready)],
)
fornecedor_service = FornecedorService()


def handle_fornecedor_error(exc: Exception) -> None:
    if isinstance(exc, FornecedorNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, FornecedorConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, FornecedorInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=FornecedorRead, status_code=status.HTTP_201_CREATED)
def create_fornecedor(
    payload: FornecedorCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        # Avisos calculados ANTES do INSERT, senão o próprio registro apareceria. Nunca
        # bloqueiam a criação — ver docstring de app/models/fornecedor.py.
        avisos = fornecedor_service.detectar_possiveis_duplicidades(
            db, empresa_id=current_user.empresa_id, nome=payload.nome, documento=payload.documento
        )
        criado = fornecedor_service.create_fornecedor(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return fornecedor_service.to_read(criado, avisos)
    except Exception as exc:
        handle_fornecedor_error(exc)


@router.get("", response_model=list[FornecedorRead])
def list_fornecedores(
    status_fornecedor: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    fornecedores = fornecedor_service.list_fornecedores(
        db,
        empresa_id=current_user.empresa_id,
        status=status_fornecedor,
        search=search,
        limit=limit,
        offset=offset,
    )
    return fornecedor_service.to_read_lote(fornecedores)


# Só ativos e inativos. Arquivado nunca é oferecido como opção de vínculo novo — ver
# FornecedorRepository.list_diretorio. Quem precisa ver arquivados usa GET /fornecedores
# com `status=arquivado`.
@router.get("/diretorio", response_model=list[FornecedorDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    fornecedores = fornecedor_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return fornecedor_service.to_diretorio_read_lote(fornecedores)


@router.get("/{fornecedor_id}", response_model=FornecedorRead)
def get_fornecedor(
    fornecedor_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        fornecedor = fornecedor_service.get_fornecedor(db, str(fornecedor_id))
        ensure_resource_empresa(fornecedor.empresa_id, current_user)
        return fornecedor_service.to_read(fornecedor)
    except Exception as exc:
        handle_fornecedor_error(exc)


@router.patch("/{fornecedor_id}", response_model=FornecedorRead)
def update_fornecedor(
    fornecedor_id: UUID,
    payload: FornecedorUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = fornecedor_service.get_fornecedor(db, str(fornecedor_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_fornecedor_error(exc)

    try:
        avisos = fornecedor_service.detectar_possiveis_duplicidades(
            db,
            empresa_id=existente.empresa_id,
            nome=payload.nome if payload.nome is not None else existente.nome,
            documento=payload.documento if payload.documento is not None else existente.documento,
            excluir_id=existente.id,
        )
        fornecedor = fornecedor_service.update_fornecedor(
            db, str(fornecedor_id), payload, actor_usuario_id=current_user.id
        )
        return fornecedor_service.to_read(fornecedor, avisos)
    except Exception as exc:
        handle_fornecedor_error(exc)


# "Excluir" = arquivar (soft-delete permanente). Nunca há delete físico de fornecedor.
@router.post("/{fornecedor_id}/arquivar", response_model=FornecedorRead)
def arquivar_fornecedor(
    fornecedor_id: UUID,
    payload: FornecedorArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = fornecedor_service.get_fornecedor(db, str(fornecedor_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_fornecedor_error(exc)

    try:
        fornecedor = fornecedor_service.arquivar_fornecedor(
            db,
            str(fornecedor_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return fornecedor_service.to_read(fornecedor)
    except Exception as exc:
        handle_fornecedor_error(exc)


@router.post("/{fornecedor_id}/restaurar", response_model=FornecedorRead)
def restaurar_fornecedor(
    fornecedor_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = fornecedor_service.get_fornecedor(db, str(fornecedor_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_fornecedor_error(exc)

    try:
        fornecedor = fornecedor_service.restaurar_fornecedor(
            db, str(fornecedor_id), actor_usuario_id=current_user.id
        )
        return fornecedor_service.to_read(fornecedor)
    except Exception as exc:
        handle_fornecedor_error(exc)
