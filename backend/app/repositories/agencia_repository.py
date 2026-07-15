from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agencia import Agencia


class AgenciaRepository:
    def create(self, db: Session, agencia: Agencia) -> Agencia:
        db.add(agencia)
        db.flush()
        return agencia

    def get_by_id(self, db: Session, agencia_id: str) -> Agencia | None:
        return db.get(Agencia, agencia_id)

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> Agencia | None:
        statement = select(Agencia).where(
            Agencia.empresa_id == empresa_id,
            Agencia.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_nome(self, db: Session, *, empresa_id: str, nome: str) -> Agencia | None:
        statement = select(Agencia).where(
            Agencia.empresa_id == empresa_id,
            Agencia.nome == nome,
        )
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Agencia]:
        statement = select(Agencia).where(Agencia.empresa_id == empresa_id)

        if status:
            statement = statement.where(Agencia.status == status)

        statement = statement.order_by(Agencia.created_at.desc(), Agencia.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, agencia: Agencia) -> Agencia:
        db.add(agencia)
        db.flush()
        return agencia
