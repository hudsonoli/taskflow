from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.tipo_tarefa import (
    TipoTarefaArquivar,
    TipoTarefaCreate,
    TipoTarefaDiretorioRead,
    TipoTarefaRead,
    TipoTarefaUpdate,
)
from app.services.tipo_tarefa_service import (
    TipoTarefaArquivadoConflictError,
    TipoTarefaConflictError,
    TipoTarefaInvalidTransitionError,
    TipoTarefaNotFoundError,
    TipoTarefaService,
)

router = APIRouter(
    prefix="/tipos-tarefa",
    tags=["tipos-tarefa"],
    dependencies=[Depends(get_current_user_password_ready)],
)
tipo_tarefa_service = TipoTarefaService()


def handle_tipo_tarefa_error(exc: Exception) -> None:
    if isinstance(exc, TipoTarefaNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, TipoTarefaArquivadoConflictError):
        # Formato padronizado — ver docs/padrao-arquivamento.md. Traz o ID do arquivado para
        # a UI oferecer restaurar em vez de só mostrar duplicidade.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "TIPO_TAREFA_ARQUIVADO_EXISTENTE",
                "tipoTarefaArquivadoId": exc.tipo_tarefa_arquivado_id,
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, TipoTarefaConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, TipoTarefaInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=TipoTarefaRead, status_code=status.HTTP_201_CREATED)
def create_tipo_tarefa(
    payload: TipoTarefaCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        criado = tipo_tarefa_service.create_tipo_tarefa(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return tipo_tarefa_service.to_read(criado)
    except Exception as exc:
        handle_tipo_tarefa_error(exc)


@router.get("", response_model=list[TipoTarefaRead])
def list_tipos_tarefa(
    status_tipo_tarefa: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    tipos_tarefa = tipo_tarefa_service.list_tipos_tarefa(
        db,
        empresa_id=current_user.empresa_id,
        status=status_tipo_tarefa,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [tipo_tarefa_service.to_read(item) for item in tipos_tarefa]


# Diretório fica admin/gestor nesta fase — o único consumidor atual (ProjetoFormSections,
# Modelo de Campanha) já é área administrativa. Diferente de /workflow-modelos/diretorio, que
# é aberto a qualquer autenticado porque Nova Tarefa (operacional) também consome.
@router.get("/diretorio", response_model=list[TipoTarefaDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    tipos_tarefa = tipo_tarefa_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return [tipo_tarefa_service.to_diretorio_read(item) for item in tipos_tarefa]


@router.get("/{tipo_tarefa_id}", response_model=TipoTarefaRead)
def get_tipo_tarefa(
    tipo_tarefa_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        tipo_tarefa = tipo_tarefa_service.get_tipo_tarefa(db, str(tipo_tarefa_id))
        ensure_resource_empresa(tipo_tarefa.empresa_id, current_user)
        return tipo_tarefa_service.to_read(tipo_tarefa)
    except Exception as exc:
        handle_tipo_tarefa_error(exc)


@router.patch("/{tipo_tarefa_id}", response_model=TipoTarefaRead)
def update_tipo_tarefa(
    tipo_tarefa_id: UUID,
    payload: TipoTarefaUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = tipo_tarefa_service.get_tipo_tarefa(db, str(tipo_tarefa_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_tipo_tarefa_error(exc)

    try:
        tipo_tarefa = tipo_tarefa_service.update_tipo_tarefa(
            db, str(tipo_tarefa_id), payload, actor_usuario_id=current_user.id
        )
        return tipo_tarefa_service.to_read(tipo_tarefa)
    except Exception as exc:
        handle_tipo_tarefa_error(exc)


@router.post("/{tipo_tarefa_id}/arquivar", response_model=TipoTarefaRead)
def arquivar_tipo_tarefa(
    tipo_tarefa_id: UUID,
    payload: TipoTarefaArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = tipo_tarefa_service.get_tipo_tarefa(db, str(tipo_tarefa_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_tipo_tarefa_error(exc)

    try:
        tipo_tarefa = tipo_tarefa_service.arquivar_tipo_tarefa(
            db,
            str(tipo_tarefa_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return tipo_tarefa_service.to_read(tipo_tarefa)
    except Exception as exc:
        handle_tipo_tarefa_error(exc)


@router.post("/{tipo_tarefa_id}/restaurar", response_model=TipoTarefaRead)
def restaurar_tipo_tarefa(
    tipo_tarefa_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = tipo_tarefa_service.get_tipo_tarefa(db, str(tipo_tarefa_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_tipo_tarefa_error(exc)

    try:
        tipo_tarefa = tipo_tarefa_service.restaurar_tipo_tarefa(
            db, str(tipo_tarefa_id), actor_usuario_id=current_user.id
        )
        return tipo_tarefa_service.to_read(tipo_tarefa)
    except Exception as exc:
        handle_tipo_tarefa_error(exc)
