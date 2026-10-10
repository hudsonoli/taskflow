"""Aprovação externa — lado INTERNO (Fase 9B): o usuário autenticado gera, consulta e revoga o link de aprovação da etapa de aprovação ATUAL.

Escopo: o mesmo da progressão de workflow (base OU derivado da etapa atual — Fase 8C.1); a autoridade final é do serviço
(`pode_gerenciar_aprovacao_externa`: responsável da etapa, Head do departamento, gestor/admin do tenant, responsável da Demanda — NÃO Atendimento por perfil).
O token só aparece na resposta da CRIAÇÃO (`Cache-Control: no-store`).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.escopo_leitura import demanda_com_acesso_de_workflow
from app.api.routes.demandas import demanda_service, handle_demanda_error
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.usuario import Usuario
from app.schemas.aprovacao_externa import (
    AprovacaoExternaCriadaRead,
    AprovacaoExternaCriar,
    AprovacaoExternaEstadoRead,
    AprovacaoExternaRead,
)
from app.services.aprovacao_externa_service import (
    AprovacaoExternaConflitoError,
    AprovacaoExternaEntradaInvalidaError,
    AprovacaoExternaNaoEncontradaError,
    AprovacaoExternaSemAutoridadeError,
    AprovacaoExternaService,
)

router = APIRouter(
    prefix="/demandas",
    tags=["aprovacao-externa"],
    dependencies=[Depends(get_current_user_password_ready)],
)
aprovacao_service = AprovacaoExternaService(demanda_service=demanda_service)

_CAMINHO = "/{demanda_id}/workflow/etapas/{etapa_id}/aprovacao-externa"


def _tratar_erro(exc: Exception) -> None:
    if isinstance(exc, AprovacaoExternaNaoEncontradaError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, AprovacaoExternaSemAutoridadeError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, AprovacaoExternaEntradaInvalidaError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, AprovacaoExternaConflitoError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": exc.codigo, "message": str(exc)}) from exc
    handle_demanda_error(exc)  # 404 da Demanda, 409 de workflow (arquivada / etapa não atual / pausada…), demais


@router.get(_CAMINHO, response_model=AprovacaoExternaEstadoRead)
def consultar_aprovacao_externa(
    demanda_id: UUID,
    etapa_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Painel da etapa: `podeGerenciar`, a solicitação mais recente (qualquer estado) e os contatos do Cliente para o "destinatário pretendido"."""
    try:
        demanda, _via = demanda_com_acesso_de_workflow(db, current_user, str(demanda_id), demanda_service)
        return aprovacao_service.consultar_etapa(db, demanda, etapa_id=str(etapa_id), usuario=current_user)
    except Exception as exc:
        _tratar_erro(exc)


@router.post(_CAMINHO, response_model=AprovacaoExternaCriadaRead, status_code=status.HTTP_201_CREATED)
def criar_aprovacao_externa(
    demanda_id: UUID,
    etapa_id: UUID,
    payload: AprovacaoExternaCriar,
    response: Response,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Gera um NOVO link (e revoga o aberto anterior da etapa). A resposta é a ÚNICA vez em que o token existe em claro."""
    try:
        demanda, _via = demanda_com_acesso_de_workflow(db, current_user, str(demanda_id), demanda_service)
        criada = aprovacao_service.criar(db, demanda, etapa_id=str(etapa_id), payload=payload, usuario=current_user)
        response.headers["Cache-Control"] = "no-store"
        return criada
    except Exception as exc:
        _tratar_erro(exc)


@router.post(_CAMINHO + "/{aprovacao_id}/revogar", response_model=AprovacaoExternaRead)
def revogar_aprovacao_externa(
    demanda_id: UUID,
    etapa_id: UUID,
    aprovacao_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Revoga o link (o cliente passa a ver "indisponível"). Aprovação já decidida → 409; já revogada → idempotente."""
    try:
        demanda, _via = demanda_com_acesso_de_workflow(db, current_user, str(demanda_id), demanda_service)
        return aprovacao_service.revogar(
            db, demanda, etapa_id=str(etapa_id), aprovacao_id=str(aprovacao_id), usuario=current_user
        )
    except Exception as exc:
        _tratar_erro(exc)
