from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.departamento import Departamento


class DepartamentoRepository:
    def create(self, db: Session, departamento: Departamento) -> Departamento:
        db.add(departamento)
        db.flush()
        return departamento

    def get_by_id(self, db: Session, departamento_id: str) -> Departamento | None:
        return db.get(Departamento, departamento_id)

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> Departamento | None:
        statement = select(Departamento).where(
            Departamento.empresa_id == empresa_id,
            Departamento.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_nome(self, db: Session, *, empresa_id: str, nome: str) -> Departamento | None:
        statement = select(Departamento).where(
            Departamento.empresa_id == empresa_id,
            Departamento.nome == nome,
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
    ) -> list[Departamento]:
        statement = select(Departamento).where(Departamento.empresa_id == empresa_id)

        if status:
            statement = statement.where(Departamento.status == status)

        if busca:
            termo = f"%{busca}%"
            statement = statement.where(or_(Departamento.nome.ilike(termo), Departamento.codigo_interno.ilike(termo)))

        statement = statement.order_by(Departamento.created_at.desc(), Departamento.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, departamento: Departamento) -> Departamento:
        db.add(departamento)
        db.flush()
        return departamento
