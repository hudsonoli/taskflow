from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.escopo import resolver_escopo_demanda
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.demanda import Demanda
from app.models.usuario import Usuario
from app.schemas.demanda_checklist import (
    DemandaChecklistItemCreate,
    DemandaChecklistItemRead,
    DemandaChecklistItemUpdate,
    DemandaChecklistReordenar,
)
from app.services.demanda_checklist_service import (
    DemandaChecklistItemNotFoundError,
    DemandaChecklistReordenarInvalidoError,
    DemandaChecklistService,
)
from app.services.demanda_service import DemandaNotFoundError, DemandaService

# Checklist é parte OPERACIONAL da Demanda (ver instrução da Fase 2E.3, item 13): mesmo
# critério de acesso de criar/ler/editar a própria Demanda — qualquer autenticado dentro do
# escopo dela, sem gate adicional de perfil. Nada de admin/gestor aqui, ao contrário de
# arquivar/restaurar Demanda.
router = APIRouter(
    prefix="/demandas",
    tags=["demanda-checklist"],
    dependencies=[Depends(get_current_user_password_ready)],
)
demanda_service = DemandaService()
checklist_service = DemandaChecklistService()


def handle_checklist_error(exc: Exception) -> None:
    if isinstance(exc, (DemandaNotFoundError, DemandaChecklistItemNotFoundError)):
        # Mesma doutrina 404 de app/api/routes/demandas.py: fora do escopo ou de outra
        # empresa não se distingue de "não existe" — um 403 confirmaria a existência.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, DemandaChecklistReordenarInvalidoError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


def _demanda_no_escopo(demanda_id: UUID, current_user: Usuario, db: Session) -> Demanda:
    escopo = resolver_escopo_demanda(db, current_user)
    return demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)


@router.get("/{demanda_id}/checklist", response_model=list[DemandaChecklistItemRead])
def listar_checklist(
    demanda_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        itens = checklist_service.list_itens(db, demanda.id)
        return [checklist_service.to_read(item) for item in itens]
    except Exception as exc:
        handle_checklist_error(exc)


@router.post(
    "/{demanda_id}/checklist", response_model=DemandaChecklistItemRead, status_code=status.HTTP_201_CREATED
)
def criar_item_checklist(
    demanda_id: UUID,
    payload: DemandaChecklistItemCreate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        item = checklist_service.criar_item(db, demanda, payload, actor_usuario_id=current_user.id)
        return checklist_service.to_read(item)
    except Exception as exc:
        handle_checklist_error(exc)


@router.patch("/{demanda_id}/checklist/{item_id}", response_model=DemandaChecklistItemRead)
def atualizar_item_checklist(
    demanda_id: UUID,
    item_id: UUID,
    payload: DemandaChecklistItemUpdate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        item = checklist_service.atualizar_item(
            db, demanda, str(item_id), payload, actor_usuario_id=current_user.id
        )
        return checklist_service.to_read(item)
    except Exception as exc:
        handle_checklist_error(exc)


@router.put("/{demanda_id}/checklist/reordenar", response_model=list[DemandaChecklistItemRead])
def reordenar_checklist(
    demanda_id: UUID,
    payload: DemandaChecklistReordenar,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        item_ids = [str(item_id) for item_id in payload.item_ids]
        itens = checklist_service.reordenar(db, demanda, item_ids, actor_usuario_id=current_user.id)
        return [checklist_service.to_read(item) for item in itens]
    except Exception as exc:
        handle_checklist_error(exc)


@router.delete("/{demanda_id}/checklist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_item_checklist(
    demanda_id: UUID,
    item_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        checklist_service.excluir_item(db, demanda, str(item_id), actor_usuario_id=current_user.id)
    except Exception as exc:
        handle_checklist_error(exc)
