from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.escopo import resolver_escopo_demanda
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.demanda import Demanda
from app.models.usuario import Usuario
from app.schemas.demanda_comentario import (
    DemandaComentarioCreate,
    DemandaComentarioRead,
    DemandaComentarioUpdate,
)
from app.services.demanda_comentario_service import (
    DemandaComentarioNaoAutorizadoError,
    DemandaComentarioNotFoundError,
    DemandaComentarioService,
)
from app.services.demanda_service import DemandaNotFoundError, DemandaService

# Mesmo critério de acesso de checklist/arquivos (Fase 2E.3): comentário é operacional,
# aberto a qualquer autenticado dentro do escopo da própria Demanda. A regra de autoria
# (só o autor edita; autor ou admin/gestor excluem) é decidida no service, não aqui.
router = APIRouter(
    prefix="/demandas",
    tags=["demanda-comentarios"],
    dependencies=[Depends(get_current_user_password_ready)],
)
demanda_service = DemandaService()
comentario_service = DemandaComentarioService()


def handle_comentario_error(exc: Exception) -> None:
    if isinstance(exc, (DemandaNotFoundError, DemandaComentarioNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, DemandaComentarioNaoAutorizadoError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    raise exc


def _demanda_no_escopo(demanda_id: UUID, current_user: Usuario, db: Session) -> Demanda:
    escopo = resolver_escopo_demanda(db, current_user)
    return demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)


@router.get("/{demanda_id}/comentarios", response_model=list[DemandaComentarioRead])
def listar_comentarios(
    demanda_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        comentarios = comentario_service.list_comentarios(db, demanda.id)
        return [comentario_service.to_read(comentario) for comentario in comentarios]
    except Exception as exc:
        handle_comentario_error(exc)


@router.post(
    "/{demanda_id}/comentarios", response_model=DemandaComentarioRead, status_code=status.HTTP_201_CREATED
)
def criar_comentario(
    demanda_id: UUID,
    payload: DemandaComentarioCreate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        comentario = comentario_service.criar_comentario(db, demanda, payload, autor=current_user)
        return comentario_service.to_read(comentario)
    except Exception as exc:
        handle_comentario_error(exc)


@router.patch("/{demanda_id}/comentarios/{comentario_id}", response_model=DemandaComentarioRead)
def editar_comentario(
    demanda_id: UUID,
    comentario_id: UUID,
    payload: DemandaComentarioUpdate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        comentario = comentario_service.editar_comentario(
            db, demanda, str(comentario_id), payload, current_user=current_user
        )
        return comentario_service.to_read(comentario)
    except Exception as exc:
        handle_comentario_error(exc)


@router.delete("/{demanda_id}/comentarios/{comentario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_comentario(
    demanda_id: UUID,
    comentario_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        comentario_service.excluir_comentario(db, demanda, str(comentario_id), current_user=current_user)
    except Exception as exc:
        handle_comentario_error(exc)
