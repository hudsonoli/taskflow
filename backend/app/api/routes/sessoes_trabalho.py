from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.sessao_trabalho import SessaoTrabalhoRead
from app.services.sessao_trabalho_service import SessaoTrabalhoService

router = APIRouter(prefix="/sessoes-trabalho", tags=["sessoes-trabalho"])
sessao_service = SessaoTrabalhoService()


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filtros de data devem incluir timezone",
        )
    return value.astimezone(timezone.utc)


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
    # Rota técnica provisória sem auth/RBAC. Não expor como API pública definitiva.
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
