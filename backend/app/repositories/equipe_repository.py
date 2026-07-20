from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.equipe import Equipe


class EquipeRepository:
    def create(self, db: Session, equipe: Equipe) -> Equipe:
        db.add(equipe)
        db.flush()
        return equipe

    def get_by_id(self, db: Session, equipe_id: str) -> Equipe | None:
        return db.get(Equipe, equipe_id)

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> Equipe | None:
        statement = select(Equipe).where(
            Equipe.empresa_id == empresa_id,
            Equipe.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_nome(self, db: Session, *, empresa_id: str, nome: str) -> Equipe | None:
        statement = select(Equipe).where(
            Equipe.empresa_id == empresa_id,
            Equipe.nome == nome,
        )
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        departamento_id: str | None = None,
        busca: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Equipe]:
        statement = select(Equipe).where(Equipe.empresa_id == empresa_id)

        if status:
            statement = statement.where(Equipe.status == status)

        if departamento_id:
            statement = statement.where(Equipe.departamento_id == departamento_id)

        if busca:
            termo = f"%{busca}%"
            statement = statement.where(or_(Equipe.nome.ilike(termo), Equipe.codigo_interno.ilike(termo)))

        statement = statement.order_by(Equipe.created_at.desc(), Equipe.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, equipe: Equipe) -> Equipe:
        db.add(equipe)
        db.flush()
        return equipe
