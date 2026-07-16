from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.empresa import Empresa


class EmpresaRepository:
    def create(self, db: Session, empresa: Empresa) -> Empresa:
        db.add(empresa)
        db.flush()
        return empresa

    def get_by_id(self, db: Session, empresa_id: str) -> Empresa | None:
        return db.get(Empresa, empresa_id)

    def get_by_codigo_interno(self, db: Session, codigo_interno: str) -> Empresa | None:
        statement = select(Empresa).where(Empresa.codigo_interno == codigo_interno)
        return db.scalars(statement).first()

    def get_by_documento(self, db: Session, documento: str) -> Empresa | None:
        statement = select(Empresa).where(Empresa.documento == documento)
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Empresa]:
        statement = select(Empresa)

        if status:
            statement = statement.where(Empresa.status == status)

        statement = statement.order_by(Empresa.created_at.desc(), Empresa.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, empresa: Empresa) -> Empresa:
        db.add(empresa)
        db.flush()
        return empresa
