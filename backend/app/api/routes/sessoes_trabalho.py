from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.evento import EventoCreate
from app.schemas.sessao_trabalho import SessaoTrabalhoAbrir, SessaoTrabalhoFechar, SessaoTrabalhoRead
from app.services.evento_service import EventoService
from app.services.sessao_trabalho_service import SessaoTrabalhoService

router = APIRouter(prefix="/sessoes-trabalho", tags=["sessoes-trabalho"])
sessao_service = SessaoTrabalhoService()
evento_service = EventoService()


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
def abrir_sessao(payload: SessaoTrabalhoAbrir, db: Session = Depends(get_db)):
    agora = datetime.now(timezone.utc)
    evento = evento_service.create_evento(
        db,
        EventoCreate(
            empresaId=payload.empresa_id,
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
            empresa_id=payload.empresa_id,
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
def fechar_sessao(sessao_id: UUID, payload: SessaoTrabalhoFechar, db: Session = Depends(get_db)):
    sessao = sessao_service.get_session(db, str(sessao_id))
    if sessao is None:
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
    db: Session = Depends(get_db),
):
    try:
        return sessao_service.list_sessions(
            db,
            empresa_id=empresa_id,
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


@router.get("/{sessao_id}", response_model=SessaoTrabalhoRead)
def get_sessao_trabalho(sessao_id: UUID, db: Session = Depends(get_db)):
    sessao = sessao_service.get_session(db, str(sessao_id))
    if sessao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão de trabalho não encontrada")
    return sessao
