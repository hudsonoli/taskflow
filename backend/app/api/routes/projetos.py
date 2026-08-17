from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.projeto import (
    ProjetoArquivar,
    ProjetoCreate,
    ProjetoDiretorioRead,
    ProjetoRead,
    ProjetoUpdate,
)
from app.services.projeto_service import (
    ProjetoArquivadoConflictError,
    ProjetoClienteInvalidoError,
    ProjetoConflictError,
    ProjetoDepartamentoInvalidoError,
    ProjetoInvalidTransitionError,
    ProjetoNotFoundError,
    ProjetoService,
    ProjetoUsuarioInvalidoError,
)

router = APIRouter(
    prefix="/projetos",
    tags=["projetos"],
    dependencies=[Depends(get_current_user_password_ready)],
)
projeto_service = ProjetoService()


def handle_projeto_error(exc: Exception) -> None:
    if isinstance(exc, ProjetoNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ProjetoArquivadoConflictError):
        # Formato padronizado — ver docs/padrao-arquivamento.md. Traz o id do arquivado para
        # a UI oferecer restaurar em vez de só mostrar duplicidade.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PROJETO_ARQUIVADO_EXISTENTE",
                "message": str(exc),
                "projetoArquivadoId": exc.projeto_arquivado_id,
            },
        ) from exc
    if isinstance(exc, (ProjetoConflictError, ProjetoInvalidTransitionError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(
        exc,
        (ProjetoClienteInvalidoError, ProjetoUsuarioInvalidoError, ProjetoDepartamentoInvalidoError),
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=ProjetoRead, status_code=status.HTTP_201_CREATED)
def create_projeto(
    payload: ProjetoCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        criado = projeto_service.create_projeto(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return projeto_service.to_read(db, criado)
    except Exception as exc:
        handle_projeto_error(exc)


@router.get("", response_model=list[ProjetoRead])
def list_projetos(
    status_projeto: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    cliente_id: UUID | None = Query(default=None, alias="clienteId"),
    departamento_id: UUID | None = Query(default=None, alias="departamentoId"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    projetos = projeto_service.list_projetos(
        db,
        empresa_id=current_user.empresa_id,
        status=status_projeto,
        search=search,
        cliente_id=str(cliente_id) if cliente_id else None,
        departamento_id=str(departamento_id) if departamento_id else None,
        limit=limit,
        offset=offset,
    )
    return projeto_service.to_read_lote(db, projetos)


# Inclui arquivados (Fase 2E.5A/B) — precisa resolver o nome de Projeto de Demandas antigas
# mesmo depois do arquivamento. `status` vai junto: quem monta seletor de vínculo NOVO filtra
# `status !== "arquivado"` no consumidor, mesmo padrão de Cliente/Departamento/Usuário/Equipe.
@router.get("/diretorio", response_model=list[ProjetoDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    projetos = projeto_service.list_diretorio(db, empresa_id=current_user.empresa_id)
    return projeto_service.to_diretorio_read_lote(projetos)


@router.get("/{projeto_id}", response_model=ProjetoRead)
def get_projeto(
    projeto_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        projeto = projeto_service.get_projeto(db, str(projeto_id))
        ensure_resource_empresa(projeto.empresa_id, current_user)
        return projeto_service.to_read(db, projeto)
    except Exception as exc:
        handle_projeto_error(exc)


@router.patch("/{projeto_id}", response_model=ProjetoRead)
def update_projeto(
    projeto_id: UUID,
    payload: ProjetoUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = projeto_service.get_projeto(db, str(projeto_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_projeto_error(exc)

    try:
        projeto = projeto_service.update_projeto(
            db, str(projeto_id), payload, actor_usuario_id=current_user.id
        )
        return projeto_service.to_read(db, projeto)
    except Exception as exc:
        handle_projeto_error(exc)


# "Excluir" = arquivar (soft-delete permanente). Nunca há delete físico de projeto.
@router.post("/{projeto_id}/arquivar", response_model=ProjetoRead)
def arquivar_projeto(
    projeto_id: UUID,
    payload: ProjetoArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = projeto_service.get_projeto(db, str(projeto_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_projeto_error(exc)

    try:
        projeto = projeto_service.arquivar_projeto(
            db,
            str(projeto_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return projeto_service.to_read(db, projeto)
    except Exception as exc:
        handle_projeto_error(exc)


@router.post("/{projeto_id}/restaurar", response_model=ProjetoRead)
def restaurar_projeto(
    projeto_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        existente = projeto_service.get_projeto(db, str(projeto_id))
        ensure_resource_empresa(existente.empresa_id, current_user)
    except Exception as exc:
        handle_projeto_error(exc)

    try:
        projeto = projeto_service.restaurar_projeto(
            db, str(projeto_id), actor_usuario_id=current_user.id
        )
        return projeto_service.to_read(db, projeto)
    except Exception as exc:
        handle_projeto_error(exc)
