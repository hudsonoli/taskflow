from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.workflow_modelo import (
    WorkflowModeloArquivar,
    WorkflowModeloCreate,
    WorkflowModeloDiretorioRead,
    WorkflowModeloRead,
    WorkflowModeloUpdate,
)
from app.services.workflow_modelo_service import (
    WorkflowModeloArquivadoConflictError,
    WorkflowModeloConflictError,
    WorkflowModeloInvalidTransitionError,
    WorkflowModeloNotFoundError,
    WorkflowModeloResponsavelInvalidoError,
    WorkflowModeloService,
)

router = APIRouter(
    prefix="/workflow-modelos",
    tags=["workflow-modelos"],
    dependencies=[Depends(get_current_user_password_ready)],
)
workflow_modelo_service = WorkflowModeloService()


def handle_workflow_modelo_error(exc: Exception) -> None:
    if isinstance(exc, WorkflowModeloNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, WorkflowModeloArquivadoConflictError):
        # Formato padronizado — ver docs/padrao-arquivamento.md. Traz o ID do arquivado
        # para a UI oferecer restaurar em vez de só mostrar duplicidade.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WORKFLOW_MODELO_ARQUIVADO_EXISTENTE",
                "workflowModeloArquivadoId": exc.workflow_modelo_arquivado_id,
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, WorkflowModeloConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, WorkflowModeloInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, WorkflowModeloResponsavelInvalidoError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=WorkflowModeloRead, status_code=status.HTTP_201_CREATED)
def create_workflow_modelo(
    payload: WorkflowModeloCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        criado = workflow_modelo_service.create_workflow_modelo(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return workflow_modelo_service.to_read(db, criado)
    except Exception as exc:
        handle_workflow_modelo_error(exc)


@router.get("", response_model=list[WorkflowModeloRead])
def list_workflow_modelos(
    status_workflow_modelo: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    workflow_modelos = workflow_modelo_service.list_workflow_modelos(
        db,
        empresa_id=current_user.empresa_id,
        status=status_workflow_modelo,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [workflow_modelo_service.to_read(db, item) for item in workflow_modelos]


@router.get("/diretorio", response_model=list[WorkflowModeloDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    # Aberto a qualquer autenticado — mesmo tier de leitura/criação de Demanda: selecionar
    # workflow ao criar tarefa não é administrar Workflow (isso continua require_admin_or_gestor
    # em todas as outras rotas deste router). Só ativo: não há referência histórica a
    # resolver aqui, diferente do /diretorio de Departamento/Cliente.
    workflow_modelos = workflow_modelo_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return [workflow_modelo_service.to_diretorio_read(item) for item in workflow_modelos]


@router.get("/{workflow_modelo_id}", response_model=WorkflowModeloRead)
def get_workflow_modelo(
    workflow_modelo_id: UUID,
    # Aberto a qualquer autenticado — mesmo motivo de GET /diretorio: quem pode criar
    # Demanda precisa ver o detalhe completo (etapas) do workflow escolhido antes de aplicar,
    # não só nome/id. Ainda tenant-escopado (ensure_resource_empresa abaixo); administrar
    # (POST/PATCH/arquivar/restaurar) continua admin/gestor.
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        workflow_modelo = workflow_modelo_service.get_workflow_modelo(db, str(workflow_modelo_id))
        ensure_resource_empresa(workflow_modelo.empresa_id, current_user)
        return workflow_modelo_service.to_read(db, workflow_modelo)
    except Exception as exc:
        handle_workflow_modelo_error(exc)


@router.patch("/{workflow_modelo_id}", response_model=WorkflowModeloRead)
def update_workflow_modelo(
    workflow_modelo_id: UUID,
    payload: WorkflowModeloUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = workflow_modelo_service.get_workflow_modelo(db, str(workflow_modelo_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_workflow_modelo_error(exc)

    try:
        workflow_modelo = workflow_modelo_service.update_workflow_modelo(
            db, str(workflow_modelo_id), payload, actor_usuario_id=current_user.id
        )
        return workflow_modelo_service.to_read(db, workflow_modelo)
    except Exception as exc:
        handle_workflow_modelo_error(exc)


@router.post("/{workflow_modelo_id}/arquivar", response_model=WorkflowModeloRead)
def arquivar_workflow_modelo(
    workflow_modelo_id: UUID,
    payload: WorkflowModeloArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = workflow_modelo_service.get_workflow_modelo(db, str(workflow_modelo_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_workflow_modelo_error(exc)

    try:
        workflow_modelo = workflow_modelo_service.arquivar_workflow_modelo(
            db,
            str(workflow_modelo_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return workflow_modelo_service.to_read(db, workflow_modelo)
    except Exception as exc:
        handle_workflow_modelo_error(exc)


@router.post("/{workflow_modelo_id}/restaurar", response_model=WorkflowModeloRead)
def restaurar_workflow_modelo(
    workflow_modelo_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = workflow_modelo_service.get_workflow_modelo(db, str(workflow_modelo_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_workflow_modelo_error(exc)

    try:
        workflow_modelo = workflow_modelo_service.restaurar_workflow_modelo(
            db, str(workflow_modelo_id), actor_usuario_id=current_user.id
        )
        return workflow_modelo_service.to_read(db, workflow_modelo)
    except Exception as exc:
        handle_workflow_modelo_error(exc)
