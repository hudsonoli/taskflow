from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario_cargo import UsuarioCargo


class UsuarioCargoRepository:
    def create(self, db: Session, vinculo: UsuarioCargo) -> UsuarioCargo:
        db.add(vinculo)
        db.flush()
        return vinculo

    def get_by_id(self, db: Session, vinculo_id: str) -> UsuarioCargo | None:
        return db.get(UsuarioCargo, vinculo_id)

    def list_by_empresa(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str | None = None,
        cargo_id: str | None = None,
        status: str | None = None,
        principal: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UsuarioCargo]:
        statement = select(UsuarioCargo).where(UsuarioCargo.empresa_id == empresa_id)

        if usuario_id:
            statement = statement.where(UsuarioCargo.usuario_id == usuario_id)
        if cargo_id:
            statement = statement.where(UsuarioCargo.cargo_id == cargo_id)
        if status:
            statement = statement.where(UsuarioCargo.status == status)
        if principal is not None:
            statement = statement.where(UsuarioCargo.principal.is_(principal))

        statement = statement.order_by(UsuarioCargo.created_at.desc(), UsuarioCargo.id.asc())
        statement = statement.limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    def list_by_usuario(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str,
        status: str | None = None,
    ) -> list[UsuarioCargo]:
        statement = select(UsuarioCargo).where(
            UsuarioCargo.empresa_id == empresa_id,
            UsuarioCargo.usuario_id == usuario_id,
        )
        if status:
            statement = statement.where(UsuarioCargo.status == status)
        statement = statement.order_by(UsuarioCargo.created_at.desc(), UsuarioCargo.id.asc())
        return list(db.scalars(statement).all())

    def list_by_cargo(
        self,
        db: Session,
        *,
        empresa_id: str,
        cargo_id: str,
        status: str | None = None,
    ) -> list[UsuarioCargo]:
        statement = select(UsuarioCargo).where(
            UsuarioCargo.empresa_id == empresa_id,
            UsuarioCargo.cargo_id == cargo_id,
        )
        if status:
            statement = statement.where(UsuarioCargo.status == status)
        statement = statement.order_by(UsuarioCargo.created_at.desc(), UsuarioCargo.id.asc())
        return list(db.scalars(statement).all())

    def get_active_by_usuario_cargo(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str,
        cargo_id: str,
    ) -> UsuarioCargo | None:
        statement = select(UsuarioCargo).where(
            UsuarioCargo.empresa_id == empresa_id,
            UsuarioCargo.usuario_id == usuario_id,
            UsuarioCargo.cargo_id == cargo_id,
            UsuarioCargo.status == "ativo",
        )
        return db.scalars(statement).first()

    def get_active_principal_by_usuario(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str,
    ) -> UsuarioCargo | None:
        statement = select(UsuarioCargo).where(
            UsuarioCargo.empresa_id == empresa_id,
            UsuarioCargo.usuario_id == usuario_id,
            UsuarioCargo.principal.is_(True),
            UsuarioCargo.status == "ativo",
        )
        return db.scalars(statement).first()

    def update(self, db: Session, vinculo: UsuarioCargo) -> UsuarioCargo:
        db.add(vinculo)
        db.flush()
        return vinculo

    def encerrar(self, db: Session, vinculo: UsuarioCargo) -> UsuarioCargo:
        db.add(vinculo)
        db.flush()
        return vinculo
