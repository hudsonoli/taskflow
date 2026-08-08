from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.evento import Evento
from app.repositories.evento_repository import EventoRepository
from app.schemas.evento import EventoCreate, EventoRead


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class EventoService:
    def __init__(self, repository: EventoRepository | None = None) -> None:
        self.repository = repository or EventoRepository()

    def create_evento(self, db: Session, data: EventoCreate, *, commit: bool = True) -> Evento:
        now = datetime.now(timezone.utc)
        evento = Evento(
            id=str(uuid4()),
            empresa_id=data.empresa_id,
            agencia_id=data.agencia_id,
            tipo=data.tipo,
            entidade_tipo=data.entidade_tipo,
            entidade_id=data.entidade_id,
            usuario_id=data.usuario_id,
            correlation_id=str(data.correlation_id) if data.correlation_id else None,
            causation_id=str(data.causation_id) if data.causation_id else None,
            payload=data.payload,
            metadata_=data.metadata,
            occurred_at=data.occurred_at or now,
            created_at=now,
        )
        return self.repository.create(db, evento, commit=commit)

    def get_evento(self, db: Session, evento_id: str) -> Evento | None:
        return self.repository.get_by_id(db, evento_id)

    def list_eventos(self, db: Session, **filters) -> list[Evento]:
        return self.repository.list(db, **filters)

    def to_read(self, evento: Evento) -> EventoRead:
        return EventoRead(
            id=evento.id,
            empresaId=evento.empresa_id,
            agenciaId=evento.agencia_id,
            tipo=evento.tipo,
            entidadeTipo=evento.entidade_tipo,
            entidadeId=evento.entidade_id,
            usuarioId=evento.usuario_id,
            correlationId=evento.correlation_id,
            causationId=evento.causation_id,
            payload=evento.payload,
            metadata=evento.metadata_,
            occurredAt=ensure_utc(evento.occurred_at),
            createdAt=ensure_utc(evento.created_at),
        )
