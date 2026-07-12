from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evento import Evento


class EventoRepository:
    def create(self, db: Session, evento: Evento, *, commit: bool = True) -> Evento:
        db.add(evento)
        if commit:
            db.commit()
            db.refresh(evento)
        else:
            db.flush()
        return evento

    def get_by_id(self, db: Session, evento_id: str) -> Evento | None:
        return db.get(Evento, evento_id)

    def list(
        self,
        db: Session,
        *,
        empresa_id: str | None = None,
        entidade_tipo: str | None = None,
        entidade_id: str | None = None,
        tipo: str | None = None,
        usuario_id: str | None = None,
        correlation_id: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Evento]:
        statement = select(Evento)

        if empresa_id:
            statement = statement.where(Evento.empresa_id == empresa_id)
        if entidade_tipo:
            statement = statement.where(Evento.entidade_tipo == entidade_tipo)
        if entidade_id:
            statement = statement.where(Evento.entidade_id == entidade_id)
        if tipo:
            statement = statement.where(Evento.tipo == tipo)
        if usuario_id:
            statement = statement.where(Evento.usuario_id == usuario_id)
        if correlation_id:
            statement = statement.where(Evento.correlation_id == correlation_id)
        if data_inicio:
            statement = statement.where(Evento.occurred_at >= data_inicio)
        if data_fim:
            statement = statement.where(Evento.occurred_at <= data_fim)

        statement = statement.order_by(Evento.occurred_at.desc(), Evento.created_at.desc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())
