from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.departamento import (
    DepartamentoArquivar,
    DepartamentoCreate,
    DepartamentoDiretorioRead,
    DepartamentoRead,
    DepartamentoUpdate,
)
from app.services.departamento_service import (
    DepartamentoArquivadoConflictError,
    DepartamentoConflictError,
    DepartamentoInvalidTransitionError,
    DepartamentoNotFoundError,
    DepartamentoResponsavelInvalidoError,
    DepartamentoService,
)

router = APIRouter(
    prefix="/departamentos",
    tags=["departamentos"],
    dependencies=[Depends(get_current_user_password_ready)],
)
departamento_service = DepartamentoService()


def handle_departamento_error(exc: Exception) -> None:
    if isinstance(exc, DepartamentoNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, DepartamentoArquivadoConflictError):
        # Formato padronizado — ver docs/padrao-arquivamento.md. Traz o ID do arquivado
        # para a UI oferecer restaurar em vez de só mostrar duplicidade.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DEPARTAMENTO_ARQUIVADO_EXISTENTE",
                "departamentoArquivadoId": exc.departamento_arquivado_id,
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, DepartamentoConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, DepartamentoInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, DepartamentoResponsavelInvalidoError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=DepartamentoRead, status_code=status.HTTP_201_CREATED)
def create_departamento(
    payload: DepartamentoCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        criado = departamento_service.create_departamento(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return departamento_service.to_read(criado)
    except Exception as exc:
        handle_departamento_error(exc)


@router.get("", response_model=list[DepartamentoRead])
def list_departamentos(
    status_departamento: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    departamentos = departamento_service.list_departamentos(
        db,
        empresa_id=current_user.empresa_id,
        status=status_departamento,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [departamento_service.to_read(item) for item in departamentos]


@router.get("/diretorio", response_model=list[DepartamentoDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    departamentos = departamento_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return [departamento_service.to_diretorio_read(item) for item in departamentos]


@router.get("/{departamento_id}", response_model=DepartamentoRead)
def get_departamento(
    departamento_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        departamento = departamento_service.get_departamento(db, str(departamento_id))
        ensure_resource_empresa(departamento.empresa_id, current_user)
        return departamento_service.to_read(departamento)
    except Exception as exc:
        handle_departamento_error(exc)


@router.patch("/{departamento_id}", response_model=DepartamentoRead)
def update_departamento(
    departamento_id: UUID,
    payload: DepartamentoUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = departamento_service.get_departamento(db, str(departamento_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_departamento_error(exc)

    try:
        departamento = departamento_service.update_departamento(
            db, str(departamento_id), payload, actor_usuario_id=current_user.id
        )
        return departamento_service.to_read(departamento)
    except Exception as exc:
        handle_departamento_error(exc)


@router.post("/{departamento_id}/arquivar", response_model=DepartamentoRead)
def arquivar_departamento(
    departamento_id: UUID,
    payload: DepartamentoArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = departamento_service.get_departamento(db, str(departamento_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_departamento_error(exc)

    try:
        departamento = departamento_service.arquivar_departamento(
            db,
            str(departamento_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return departamento_service.to_read(departamento)
    except Exception as exc:
        handle_departamento_error(exc)


@router.post("/{departamento_id}/restaurar", response_model=DepartamentoRead)
def restaurar_departamento(
    departamento_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = departamento_service.get_departamento(db, str(departamento_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_departamento_error(exc)

    try:
        departamento = departamento_service.restaurar_departamento(
            db, str(departamento_id), actor_usuario_id=current_user.id
        )
        return departamento_service.to_read(departamento)
    except Exception as exc:
        handle_departamento_error(exc)
