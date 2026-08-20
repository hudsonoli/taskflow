from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
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
        if correlation_id:
            statement = statement.where(Evento.correlation_id == correlation_id)
        if data_inicio:
            statement = statement.where(Evento.occurred_at >= data_inicio)
        if data_fim:
            statement = statement.where(Evento.occurred_at <= data_fim)

        statement = statement.order_by(Evento.occurred_at.desc(), Evento.created_at.desc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def contar_por_tipo_e_entidade(
        self,
        db: Session,
        *,
        empresa_id: str,
        entidade_tipo: str,
        entidade_ids: list[str],
        tipos: list[str],
    ) -> list[tuple[str, str, int]]:
        """`COUNT` agrupado por `(entidade_id, tipo)` — genérico o bastante para qualquer
        agregação futura sobre eventos de uma entidade (Fase 2F.4 usa para Demanda/Projeto,
        mas nada aqui é específico de ajuste/refação).

        `entidade_ids` vazio devolve `[]` sem consultar: um `IN ()` vazio é SQL válido que
        nunca casa, mas rodar a query mesmo assim seria trabalho sem propósito (ex.: Projeto
        sem nenhuma Demanda).
        """
        if not entidade_ids:
            return []

        statement = (
            select(Evento.entidade_id, Evento.tipo, func.count())
            .where(
                Evento.empresa_id == empresa_id,
                Evento.entidade_tipo == entidade_tipo,
                Evento.entidade_id.in_(entidade_ids),
                Evento.tipo.in_(tipos),
            )
            .group_by(Evento.entidade_id, Evento.tipo)
        )
        return [tuple(row) for row in db.execute(statement).all()]
