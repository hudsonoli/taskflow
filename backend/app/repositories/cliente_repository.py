from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente


class ClienteRepository:
    def create(self, db: Session, cliente: Cliente) -> Cliente:
        db.add(cliente)
        db.flush()
        return cliente

    def get_by_id(self, db: Session, *, empresa_id: str, cliente_id: str) -> Cliente | None:
        statement = select(Cliente).where(
            Cliente.empresa_id == empresa_id,
            Cliente.id == cliente_id,
        )
        return db.scalars(statement).first()

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> Cliente | None:
        statement = select(Cliente).where(
            Cliente.empresa_id == empresa_id,
            Cliente.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_documento(self, db: Session, *, empresa_id: str, documento: str) -> Cliente | None:
        statement = select(Cliente).where(
            Cliente.empresa_id == empresa_id,
            Cliente.documento == documento,
        )
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        tipo_pessoa: str | None = None,
        agencia_id: str | None = None,
        busca: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Cliente]:
        statement = select(Cliente).where(Cliente.empresa_id == empresa_id)

        if status:
            statement = statement.where(Cliente.status == status)
        if tipo_pessoa:
            statement = statement.where(Cliente.tipo_pessoa == tipo_pessoa)
        if agencia_id:
            statement = statement.where(Cliente.agencia_id == agencia_id)
        if busca:
            termo = f"%{busca.strip()}%"
            statement = statement.where(
                or_(
                    Cliente.codigo_interno.ilike(termo),
                    Cliente.nome.ilike(termo),
                    Cliente.razao_social.ilike(termo),
                    Cliente.nome_fantasia.ilike(termo),
                    Cliente.sigla.ilike(termo),
                )
            )

        statement = statement.order_by(
            func.coalesce(Cliente.nome_fantasia, Cliente.razao_social, Cliente.nome, Cliente.codigo_interno).asc(),
            Cliente.codigo_interno.asc(),
            Cliente.id.asc(),
        )
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, cliente: Cliente) -> Cliente:
        db.add(cliente)
        db.flush()
        return cliente
