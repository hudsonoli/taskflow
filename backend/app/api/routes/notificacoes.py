"""Central de Notificações (ver `NotificacaoService`): notificações = visão tipada dos eventos de domínio das
demandas DO PRÓPRIO usuário (+ estado "lida" por usuário); prazos da equipe = derivado de Demandas no escopo real
(`core/escopo.py`). Qualquer autenticado com senha em dia usa a própria central; a identidade e a empresa vêm
sempre do token."""

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.escopo import EscopoDemanda, resolver_escopo_demanda
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.permissoes import require_permissao
from app.models.usuario import Usuario
from app.repositories.demanda_repository import SortDemandas
from app.schemas.notificacao import (
    CategoriaNotificacao,
    GrupoPrazo,
    MarcarLidasRequest,
    NotificacoesPaginaRead,
    NotificacoesResumoRead,
    PrazosEquipePaginaRead,
)
from app.services.demanda_service import DemandaService
from app.services.notificacao_service import NotificacaoNaoEncontradaError, NotificacaoService, janelas_prazo
from app.services.usuario_permissao_service import UsuarioPermissaoService

router = APIRouter(
    prefix="/notificacoes",
    tags=["notificacoes"],
    dependencies=[Depends(get_current_user_password_ready)],
)
notificacao_service = NotificacaoService()
demanda_service = DemandaService()
permissao_service = UsuarioPermissaoService()


def _escopo(db: Session, usuario: Usuario) -> EscopoDemanda:
    return resolver_escopo_demanda(db, usuario)


def _contagem_prazos(db: Session, usuario: Usuario) -> dict[str, int]:
    """Totais de prazos no escopo REAL do usuário. Sem `demandas.visualizar` → zeros (como a listagem de
    demandas, que seria 403)."""
    if "demandas.visualizar" not in permissao_service.obter_permissoes_efetivas(db, usuario):
        return {"atrasadas": 0, "hoje": 0, "proximas": 0}
    agora, fim_hoje, fim_proximas = janelas_prazo()
    return demanda_service.contar_prazos(
        db, escopo=_escopo(db, usuario), agora=agora, fim_hoje=fim_hoje, fim_proximas=fim_proximas
    )


@router.get("/resumo", response_model=NotificacoesResumoRead)
def resumo(current_user: Usuario = Depends(get_current_user_password_ready), db: Session = Depends(get_db)):
    """Fonte ÚNICA do badge (menu do avatar e sino) e dos contadores da página."""
    return notificacao_service.resumo(db, current_user, prazos=_contagem_prazos(db, current_user))


@router.get("", response_model=NotificacoesPaginaRead)
def listar(
    categoria: CategoriaNotificacao | None = Query(default=None),
    apenas_nao_lidas: bool = Query(default=False, alias="apenasNaoLidas"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    return notificacao_service.listar(
        db, current_user, categoria=categoria, apenas_nao_lidas=apenas_nao_lidas, limit=limit, offset=offset
    )


@router.post("/lidas", response_model=NotificacoesResumoRead)
def marcar_todas_lidas(
    payload: MarcarLidasRequest | None = None,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    notificacao_service.marcar_todas_lidas(db, current_user, categoria=payload.categoria if payload else None)
    return notificacao_service.resumo(db, current_user, prazos=_contagem_prazos(db, current_user))


@router.get("/prazos-equipe", response_model=PrazosEquipePaginaRead)
def prazos_equipe(
    grupo: GrupoPrazo = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_permissao("demandas.visualizar")),
    db: Session = Depends(get_db),
):
    """Demandas abertas com prazo, no escopo REAL do usuário (admin/gestor: empresa; head/atendimento/
    operador: o que `GET /demandas` já permite — esta rota nunca amplia o acesso). Paginada no servidor."""
    escopo = _escopo(db, current_user)
    agora, fim_hoje, fim_proximas = janelas_prazo()
    totais = demanda_service.contar_prazos(
        db, escopo=escopo, agora=agora, fim_hoje=fim_hoje, fim_proximas=fim_proximas
    )
    filtros: dict = {"escopo": escopo, "sort": SortDemandas.PRAZO_ASC, "limit": limit, "offset": offset}
    if grupo == "atrasadas":
        filtros["atrasada"] = True
    elif grupo == "hoje":
        filtros.update(nao_finalizada=True, prazo_inicio=agora, prazo_fim=fim_hoje)
    else:
        filtros.update(nao_finalizada=True, prazo_inicio=fim_hoje + timedelta(microseconds=1), prazo_fim=fim_proximas)
    demandas = demanda_service.list_demandas(db, **filtros)
    return PrazosEquipePaginaRead(
        itens=demanda_service.to_read_lote(db, demandas), total=totais[grupo], limit=limit, offset=offset
    )


@router.post("/{evento_id}/lida", response_model=NotificacoesResumoRead)
def marcar_lida(
    evento_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Idempotente. Evento que não é notificação DESTE usuário (de outro usuário/empresa ou inexistente) → 404."""
    try:
        notificacao_service.marcar_lida(db, current_user, str(evento_id))
    except NotificacaoNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return notificacao_service.resumo(db, current_user, prazos=_contagem_prazos(db, current_user))
