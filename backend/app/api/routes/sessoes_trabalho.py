"""Sessões de trabalho — Central de Tráfego. Leitura e escrita restritas a admin/gestor.

Até esta correção o router respondia **sem token nenhum**: qualquer um listava quem estava
trabalhando em quê, e abria ou fechava sessão em nome de terceiros. O gate existia só em
`TrafegoView.tsx`, no navegador.

Como em `/eventos`, a empresa vem do token e o parâmetro só é aceito se coincidir.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.escopo import EscopoHorasNaoAutorizadoError
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_profiles
from app.models.usuario import Usuario
from app.schemas.evento import EventoCreate
from app.schemas.sessao_trabalho import (
    SessaoTrabalhoAbrir,
    SessaoTrabalhoFechar,
    SessaoTrabalhoHorasRead,
    SessaoTrabalhoRead,
)
from app.services.evento_service import EventoService
from app.services.sessao_trabalho_service import SessaoTrabalhoDepartamentoNaoEncontradoError, SessaoTrabalhoService

router = APIRouter(
    prefix="/sessoes-trabalho",
    tags=["sessoes-trabalho"],
    dependencies=[Depends(get_current_user_password_ready)],
)
sessao_service = SessaoTrabalhoService()
evento_service = EventoService()

require_admin_or_gestor = require_profiles("admin", "gestor")


def _empresa_do_token(empresa_id: str | None, current_user: Usuario) -> str:
    """A empresa vem SEMPRE do token; o parâmetro só é aceito se coincidir."""
    if empresa_id is not None and empresa_id != current_user.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="empresaId não corresponde à empresa da sessão",
        )
    return current_user.empresa_id


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filtros de data devem incluir timezone",
        )
    return value.astimezone(timezone.utc)


@router.post("/abrir", response_model=SessaoTrabalhoRead, status_code=status.HTTP_201_CREATED)
def abrir_sessao(
    payload: SessaoTrabalhoAbrir,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    empresa_id = _empresa_do_token(payload.empresa_id, current_user)
    agora = datetime.now(timezone.utc)
    evento = evento_service.create_evento(
        db,
        EventoCreate(
            empresaId=empresa_id,
            agenciaId=payload.agencia_id,
            tipo="sessao_trabalho_iniciada",
            entidadeTipo="demanda",
            entidadeId=payload.demanda_id,
            usuarioId=payload.usuario_id,
            payload={"demandaId": payload.demanda_id},
            occurredAt=agora,
        ),
        commit=False,
    )
    try:
        sessao = sessao_service.open_session(
            db,
            empresa_id=empresa_id,
            agencia_id=payload.agencia_id,
            demanda_id=payload.demanda_id,
            workflow_etapa_id=payload.workflow_etapa_id,
            usuario_id=payload.usuario_id,
            departamento_id=payload.departamento_id,
            evento_inicio_id=evento.id,
            inicio_em=agora,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    db.commit()
    db.refresh(sessao)
    return sessao


@router.post("/{sessao_id}/fechar", response_model=SessaoTrabalhoRead)
def fechar_sessao(
    sessao_id: UUID,
    payload: SessaoTrabalhoFechar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    sessao = sessao_service.get_session(db, str(sessao_id))
    # Sessão de outra empresa é 404, nunca 403 — 403 confirmaria que ela existe.
    if sessao is None or sessao.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão de trabalho não encontrada")

    agora = datetime.now(timezone.utc)
    evento = evento_service.create_evento(
        db,
        EventoCreate(
            empresaId=sessao.empresa_id,
            agenciaId=sessao.agencia_id,
            tipo="sessao_trabalho_encerrada",
            entidadeTipo="demanda",
            entidadeId=sessao.demanda_id,
            usuarioId=sessao.usuario_id,
            payload={"demandaId": sessao.demanda_id, "motivoEncerramento": payload.motivo_encerramento},
            occurredAt=agora,
        ),
        commit=False,
    )
    try:
        sessao = sessao_service.close_session(
            db,
            sessao,
            evento_fim_id=evento.id,
            fim_em=agora,
            motivo_encerramento=payload.motivo_encerramento,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    db.commit()
    db.refresh(sessao)
    return sessao


@router.get("", response_model=list[SessaoTrabalhoRead])
def list_sessoes_trabalho(
    empresa_id: str | None = Query(default=None, alias="empresaId"),
    demanda_id: str | None = Query(default=None, alias="demandaId"),
    usuario_id: str | None = Query(default=None, alias="usuarioId"),
    departamento_id: str | None = Query(default=None, alias="departamentoId"),
    workflow_etapa_id: str | None = Query(default=None, alias="workflowEtapaId"),
    status_sessao: str | None = Query(default=None, alias="status"),
    data_inicio: datetime | None = Query(default=None, alias="dataInicio"),
    data_fim: datetime | None = Query(default=None, alias="dataFim"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        return sessao_service.list_sessions(
            db,
            empresa_id=_empresa_do_token(empresa_id, current_user),
            demanda_id=demanda_id,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            workflow_etapa_id=workflow_etapa_id,
            status=status_sessao,
            data_inicio=normalize_datetime(data_inicio),
            data_fim=normalize_datetime(data_fim),
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/horas", response_model=SessaoTrabalhoHorasRead)
def horas_departamento(
    departamento_id: UUID = Query(alias="departamentoId"),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        horas, sessoes = sessao_service.horas_departamento(
            db,
            empresa_id=current_user.empresa_id,
            departamento_id=str(departamento_id),
            usuario=current_user,
        )
    except SessaoTrabalhoDepartamentoNaoEncontradoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except EscopoHorasNaoAutorizadoError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return SessaoTrabalhoHorasRead(
        departamento_id=str(departamento_id), horas_consumidas=horas, sessoes_consideradas=sessoes
    )


@router.get("/{sessao_id}", response_model=SessaoTrabalhoRead)
def get_sessao_trabalho(
    sessao_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    sessao = sessao_service.get_session(db, str(sessao_id))
    if sessao is None or sessao.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão de trabalho não encontrada")
    return sessao
