from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, require_admin_or_gestor
from app.models.projeto import Projeto
from app.models.usuario import Usuario
from app.schemas.projeto_modelo_campanha import (
    ProjetoModeloCampanhaAplicar,
    ProjetoModeloCampanhaSnapshotRead,
    ProjetoModeloCampanhaUpdate,
)
from app.services.projeto_modelo_campanha_service import (
    ProjetoModeloCampanhaModeloInvalidoError,
    ProjetoModeloCampanhaNaoAplicadoError,
    ProjetoModeloCampanhaReferenciaInvalidaError,
    ProjetoModeloCampanhaService,
)
from app.services.projeto_service import ProjetoNotFoundError, ProjetoService

# Prefixo sem o path param (mesmo padrão de demanda_checklist.py/demanda_comentarios.py) —
# cada rota declara o `/{projeto_id}/...` completo.
router = APIRouter(
    prefix="/projetos",
    tags=["projetos"],
    dependencies=[Depends(get_current_user_password_ready)],
)
projeto_service = ProjetoService()
projeto_modelo_campanha_service = ProjetoModeloCampanhaService()


def handle_projeto_modelo_campanha_error(exc: Exception) -> None:
    if isinstance(exc, ProjetoNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ProjetoModeloCampanhaNaoAplicadoError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, (ProjetoModeloCampanhaModeloInvalidoError, ProjetoModeloCampanhaReferenciaInvalidaError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


def _carregar_projeto_acessivel(db: Session, projeto_id: str, current_user: Usuario) -> Projeto:
    """Cross-tenant sempre 404 (nunca vaza existência) — mesmo padrão de toda rota aninhada
    em Projeto (demanda_checklist.py, demanda_comentarios.py etc)."""
    try:
        projeto = projeto_service.get_projeto(db, projeto_id)
        ensure_resource_empresa(projeto.empresa_id, current_user)
        return projeto
    except Exception as exc:
        handle_projeto_modelo_campanha_error(exc)


@router.post("/{projeto_id}/modelo-campanha/aplicar", response_model=ProjetoModeloCampanhaSnapshotRead)
def aplicar_modelo_campanha(
    projeto_id: UUID,
    payload: ProjetoModeloCampanhaAplicar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    projeto = _carregar_projeto_acessivel(db, str(projeto_id), current_user)
    try:
        cabecalho = projeto_modelo_campanha_service.aplicar_modelo(
            db,
            projeto=projeto,
            modelo_campanha_id=str(payload.modelo_campanha_id),
            actor_usuario_id=current_user.id,
        )
        return projeto_modelo_campanha_service.to_snapshot_read(db, cabecalho)
    except Exception as exc:
        handle_projeto_modelo_campanha_error(exc)


# 200 sempre — Projeto sem snapshot ainda não é um erro, é um estado válido. 404 fica
# reservado só pra Projeto inexistente/cross-tenant (ver item 13 da Fase 2G.5C2).
@router.get("/{projeto_id}/modelo-campanha", response_model=ProjetoModeloCampanhaSnapshotRead | None)
def get_modelo_campanha_snapshot(
    projeto_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    _carregar_projeto_acessivel(db, str(projeto_id), current_user)
    cabecalho = projeto_modelo_campanha_service.get_snapshot(db, projeto_id=str(projeto_id))
    if cabecalho is None:
        return None
    return projeto_modelo_campanha_service.to_snapshot_read(db, cabecalho)


@router.patch("/{projeto_id}/modelo-campanha", response_model=ProjetoModeloCampanhaSnapshotRead)
def atualizar_modelo_campanha_snapshot(
    projeto_id: UUID,
    payload: ProjetoModeloCampanhaUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    projeto = _carregar_projeto_acessivel(db, str(projeto_id), current_user)
    try:
        cabecalho = projeto_modelo_campanha_service.atualizar_itens(
            db, projeto=projeto, data=payload, actor_usuario_id=current_user.id
        )
        return projeto_modelo_campanha_service.to_snapshot_read(db, cabecalho)
    except Exception as exc:
        handle_projeto_modelo_campanha_error(exc)
