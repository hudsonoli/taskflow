from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.sla_regra import SlaRegraArquivar, SlaRegraCreate, SlaRegraRead, SlaRegraUpdate
from app.services.sla_regra_service import (
    SlaRegraArquivadaConflictError,
    SlaRegraClienteInvalidoError,
    SlaRegraConflictError,
    SlaRegraDepartamentoInvalidoError,
    SlaRegraInvalidTransitionError,
    SlaRegraNotFoundError,
    SlaRegraService,
)

router = APIRouter(
    prefix="/slas",
    tags=["slas"],
    dependencies=[Depends(get_current_user_password_ready)],
)
sla_regra_service = SlaRegraService()


def handle_sla_regra_error(exc: Exception) -> None:
    if isinstance(exc, SlaRegraNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, SlaRegraArquivadaConflictError):
        # Formato padronizado — ver docs/padrao-arquivamento.md. Traz o ID do arquivado para
        # a UI oferecer restaurar em vez de só mostrar duplicidade.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SLA_REGRA_ARQUIVADA_EXISTENTE",
                "slaRegraArquivadaId": exc.sla_regra_arquivada_id,
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, SlaRegraConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, SlaRegraInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, (SlaRegraClienteInvalidoError, SlaRegraDepartamentoInvalidoError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=SlaRegraRead, status_code=status.HTTP_201_CREATED)
def create_sla_regra(
    payload: SlaRegraCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        criada = sla_regra_service.create_sla_regra(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return sla_regra_service.to_read(criada)
    except Exception as exc:
        handle_sla_regra_error(exc)


@router.get("", response_model=list[SlaRegraRead])
def list_sla_regras(
    status_sla_regra: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    sla_regras = sla_regra_service.list_sla_regras(
        db,
        empresa_id=current_user.empresa_id,
        status=status_sla_regra,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [sla_regra_service.to_read(item) for item in sla_regras]


@router.get("/{sla_regra_id}", response_model=SlaRegraRead)
def get_sla_regra(
    sla_regra_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        sla_regra = sla_regra_service.get_sla_regra(db, str(sla_regra_id))
        ensure_resource_empresa(sla_regra.empresa_id, current_user)
        return sla_regra_service.to_read(sla_regra)
    except Exception as exc:
        handle_sla_regra_error(exc)


@router.patch("/{sla_regra_id}", response_model=SlaRegraRead)
def update_sla_regra(
    sla_regra_id: UUID,
    payload: SlaRegraUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = sla_regra_service.get_sla_regra(db, str(sla_regra_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_sla_regra_error(exc)

    try:
        sla_regra = sla_regra_service.update_sla_regra(
            db, str(sla_regra_id), payload, actor_usuario_id=current_user.id
        )
        return sla_regra_service.to_read(sla_regra)
    except Exception as exc:
        handle_sla_regra_error(exc)


@router.post("/{sla_regra_id}/arquivar", response_model=SlaRegraRead)
def arquivar_sla_regra(
    sla_regra_id: UUID,
    payload: SlaRegraArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = sla_regra_service.get_sla_regra(db, str(sla_regra_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_sla_regra_error(exc)

    try:
        sla_regra = sla_regra_service.arquivar_sla_regra(
            db,
            str(sla_regra_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return sla_regra_service.to_read(sla_regra)
    except Exception as exc:
        handle_sla_regra_error(exc)


@router.post("/{sla_regra_id}/restaurar", response_model=SlaRegraRead)
def restaurar_sla_regra(
    sla_regra_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = sla_regra_service.get_sla_regra(db, str(sla_regra_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_sla_regra_error(exc)

    try:
        sla_regra = sla_regra_service.restaurar_sla_regra(
            db, str(sla_regra_id), actor_usuario_id=current_user.id
        )
        return sla_regra_service.to_read(sla_regra)
    except Exception as exc:
        handle_sla_regra_error(exc)
