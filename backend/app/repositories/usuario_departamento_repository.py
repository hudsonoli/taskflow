from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario_departamento import UsuarioDepartamento


class UsuarioDepartamentoRepository:
    def create(self, db: Session, vinculo: UsuarioDepartamento) -> UsuarioDepartamento:
        db.add(vinculo)
        db.flush()
        return vinculo

    def get_by_id(self, db: Session, vinculo_id: str) -> UsuarioDepartamento | None:
        return db.get(UsuarioDepartamento, vinculo_id)

    def list_by_empresa(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        papel: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UsuarioDepartamento]:
        statement = select(UsuarioDepartamento).where(UsuarioDepartamento.empresa_id == empresa_id)

        if usuario_id:
            statement = statement.where(UsuarioDepartamento.usuario_id == usuario_id)
        if departamento_id:
            statement = statement.where(UsuarioDepartamento.departamento_id == departamento_id)
        if papel:
            statement = statement.where(UsuarioDepartamento.papel == papel)
        if status:
            statement = statement.where(UsuarioDepartamento.status == status)

        statement = statement.order_by(UsuarioDepartamento.created_at.desc(), UsuarioDepartamento.id.asc())
        statement = statement.limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    def list_by_usuario(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str,
        status: str | None = None,
    ) -> list[UsuarioDepartamento]:
        statement = select(UsuarioDepartamento).where(
            UsuarioDepartamento.empresa_id == empresa_id,
            UsuarioDepartamento.usuario_id == usuario_id,
        )
        if status:
            statement = statement.where(UsuarioDepartamento.status == status)
        statement = statement.order_by(UsuarioDepartamento.created_at.desc(), UsuarioDepartamento.id.asc())
        return list(db.scalars(statement).all())

    def list_by_departamento(
        self,
        db: Session,
        *,
        empresa_id: str,
        departamento_id: str,
        status: str | None = None,
    ) -> list[UsuarioDepartamento]:
        statement = select(UsuarioDepartamento).where(
            UsuarioDepartamento.empresa_id == empresa_id,
            UsuarioDepartamento.departamento_id == departamento_id,
        )
        if status:
            statement = statement.where(UsuarioDepartamento.status == status)
        statement = statement.order_by(UsuarioDepartamento.created_at.desc(), UsuarioDepartamento.id.asc())
        return list(db.scalars(statement).all())

    def get_active_by_usuario_departamento(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str,
        departamento_id: str,
    ) -> UsuarioDepartamento | None:
        statement = select(UsuarioDepartamento).where(
            UsuarioDepartamento.empresa_id == empresa_id,
            UsuarioDepartamento.usuario_id == usuario_id,
            UsuarioDepartamento.departamento_id == departamento_id,
            UsuarioDepartamento.status == "ativo",
        )
        return db.scalars(statement).first()

    def get_active_head_by_departamento(
        self,
        db: Session,
        *,
        empresa_id: str,
        departamento_id: str,
    ) -> UsuarioDepartamento | None:
        statement = select(UsuarioDepartamento).where(
            UsuarioDepartamento.empresa_id == empresa_id,
            UsuarioDepartamento.departamento_id == departamento_id,
            UsuarioDepartamento.papel == "head",
            UsuarioDepartamento.status == "ativo",
        )
        return db.scalars(statement).first()

    def get_active_principal_by_usuario(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str,
    ) -> UsuarioDepartamento | None:
        statement = select(UsuarioDepartamento).where(
            UsuarioDepartamento.empresa_id == empresa_id,
            UsuarioDepartamento.usuario_id == usuario_id,
            UsuarioDepartamento.principal.is_(True),
            UsuarioDepartamento.status == "ativo",
        )
        return db.scalars(statement).first()

    def update(self, db: Session, vinculo: UsuarioDepartamento) -> UsuarioDepartamento:
        db.add(vinculo)
        db.flush()
        return vinculo

    def encerrar(self, db: Session, vinculo: UsuarioDepartamento) -> UsuarioDepartamento:
        db.add(vinculo)
