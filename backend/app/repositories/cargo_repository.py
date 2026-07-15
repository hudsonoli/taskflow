from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.cargo import Cargo


class CargoRepository:
    def create(self, db: Session, cargo: Cargo) -> Cargo:
        db.add(cargo)
        db.flush()
        return cargo

    def get_by_id(self, db: Session, cargo_id: str) -> Cargo | None:
        return db.get(Cargo, cargo_id)

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> Cargo | None:
        statement = select(Cargo).where(
            Cargo.empresa_id == empresa_id,
            Cargo.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_nome(self, db: Session, *, empresa_id: str, nome: str) -> Cargo | None:
        statement = select(Cargo).where(
            Cargo.empresa_id == empresa_id,
            Cargo.nome == nome,
        )
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        busca: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Cargo]:
        statement = select(Cargo).where(Cargo.empresa_id == empresa_id)

        if status:
            statement = statement.where(Cargo.status == status)

        if busca:
            termo = f"%{busca}%"
            statement = statement.where(or_(Cargo.nome.ilike(termo), Cargo.codigo_interno.ilike(termo)))

        statement = statement.order_by(Cargo.created_at.desc(), Cargo.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, cargo: Cargo) -> Cargo:
        db.add(cargo)
        db.flush()
        return cargo
