from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.trafego import TrafegoAgoraItem, TrafegoCargaItem, TrafegoResumo
from app.services.trafego_query_service import TrafegoQueryService

router = APIRouter(prefix="/trafego", tags=["trafego"])
trafego_service = TrafegoQueryService()


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Filtros de data devem incluir timezone",
        )
    return value.astimezone(timezone.utc)


@router.get("/agora", response_model=list[TrafegoAgoraItem])
def list_trafego_agora(
    empresa_id: str | None = Query(default=None, alias="empresaId"),
    usuario_id: str | None = Query(default=None, alias="usuarioId"),
    departamento_id: str | None = Query(default=None, alias="departamentoId"),
    demanda_id: str | None = Query(default=None, alias="demandaId"),
    workflow_etapa_id: str | None = Query(default=None, alias="workflowEtapaId"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    # Endpoint técnico provisório sem auth/RBAC. Métricas são Tempo Operacional Estimado, não folha de ponto.
    return trafego_service.list_agora(
        db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        departamento_id=departamento_id,
        demanda_id=demanda_id,
        workflow_etapa_id=workflow_etapa_id,
        limit=limit,
        offset=offset,
    )


@router.get("/carga", response_model=list[TrafegoCargaItem])
def get_trafego_carga(
    empresa_id: str = Query(alias="empresaId"),
    agrupamento: Literal["usuario", "departamento"] = Query(default="usuario"),
    db: Session = Depends(get_db),
):
    # Endpoint técnico provisório sem auth/RBAC. Métricas são Tempo Operacional Estimado, não folha de ponto.
    return trafego_service.get_carga(db, empresa_id=empresa_id, agrupamento=agrupamento)


@router.get("/resumo", response_model=TrafegoResumo)
def get_trafego_resumo(
    empresa_id: str = Query(alias="empresaId"),
    data_inicio: datetime | None = Query(default=None, alias="dataInicio"),
    data_fim: datetime | None = Query(default=None, alias="dataFim"),
    usuario_id: str | None = Query(default=None, alias="usuarioId"),
    departamento_id: str | None = Query(default=None, alias="departamentoId"),
    demanda_id: str | None = Query(default=None, alias="demandaId"),
    db: Session = Depends(get_db),
):
    # Endpoint técnico provisório sem auth/RBAC. Métricas são Tempo Operacional Estimado, não folha de ponto.
    try:
        return trafego_service.get_resumo(
            db,
            empresa_id=empresa_id,
            data_inicio=normalize_datetime(data_inicio),
            data_fim=normalize_datetime(data_fim),
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            demanda_id=demanda_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
