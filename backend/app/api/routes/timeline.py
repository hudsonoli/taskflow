from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.timeline import TimelineItem
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"])
timeline_service = TimelineService()


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Filtros de data devem incluir timezone",
        )
    return value.astimezone(timezone.utc)


@router.get("", response_model=list[TimelineItem])
def list_timeline(
    empresa_id: str | None = Query(default=None, alias="empresaId"),
    entidade_tipo: str | None = Query(default=None, alias="entidadeTipo"),
    entidade_id: str | None = Query(default=None, alias="entidadeId"),
    tipo: str | None = None,
    usuario_id: str | None = Query(default=None, alias="usuarioId"),
    data_inicio: datetime | None = Query(default=None, alias="dataInicio"),
    data_fim: datetime | None = Query(default=None, alias="dataFim"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    # Rota técnica provisória sem auth/RBAC. Não expor como API pública definitiva.
    return timeline_service.list_timeline(
        db,
        empresa_id=empresa_id,
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        tipo=tipo,
        usuario_id=usuario_id,
        data_inicio=normalize_datetime(data_inicio),
        data_fim=normalize_datetime(data_fim),
        limit=limit,
        offset=offset,
    )
