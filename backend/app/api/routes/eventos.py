from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.evento import EventoCreate, EventoRead
from app.services.evento_service import EventoService

router = APIRouter(prefix="/eventos", tags=["eventos"])
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


@router.post("", response_model=EventoRead, status_code=status.HTTP_201_CREATED)
def create_evento(evento: EventoCreate, db: Session = Depends(get_db)):
    # API técnica provisória para fundação do Motor de Eventos.
    # Não é endpoint público definitivo e não está integrado ao frontend nesta sprint.
    created = evento_service.create_evento(db, evento)
    return evento_service.to_read(created)


@router.get("/{evento_id}", response_model=EventoRead)
def get_evento(evento_id: UUID, db: Session = Depends(get_db)):
    evento = evento_service.get_evento(db, str(evento_id))
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
    return evento_service.to_read(evento)


@router.get("", response_model=list[EventoRead])
def list_eventos(
    empresa_id: str | None = Query(default=None, alias="empresaId"),
    entidade_tipo: str | None = Query(default=None, alias="entidadeTipo"),
    entidade_id: str | None = Query(default=None, alias="entidadeId"),
    tipo: str | None = None,
    correlation_id: UUID | None = Query(default=None, alias="correlationId"),
    data_inicio: datetime | None = Query(default=None, alias="dataInicio"),
    data_fim: datetime | None = Query(default=None, alias="dataFim"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    eventos = evento_service.list_eventos(
        db,
        empresa_id=empresa_id,
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        tipo=tipo,
        correlation_id=str(correlation_id) if correlation_id else None,
        data_inicio=normalize_datetime(data_inicio),
        data_fim=normalize_datetime(data_fim),
        limit=limit,
        offset=offset,
    )
    return [evento_service.to_read(evento) for evento in eventos]
