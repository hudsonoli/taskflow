from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario_equipe import UsuarioEquipe


class UsuarioEquipeRepository:
    def create(self, db: Session, vinculo: UsuarioEquipe) -> UsuarioEquipe:
        db.add(vinculo)
        db.flush()
        return vinculo

    def get_by_id(self, db: Session, vinculo_id: str) -> UsuarioEquipe | None:
        return db.get(UsuarioEquipe, vinculo_id)

    def list_by_empresa(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str | None = None,
        equipe_id: str | None = None,
        papel: str | None = None,
        status: str | None = None,
        principal: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UsuarioEquipe]:
        statement = select(UsuarioEquipe).where(UsuarioEquipe.empresa_id == empresa_id)

        if usuario_id:
            statement = statement.where(UsuarioEquipe.usuario_id == usuario_id)
        if equipe_id:
            statement = statement.where(UsuarioEquipe.equipe_id == equipe_id)
        if papel:
            statement = statement.where(UsuarioEquipe.papel == papel)
        if status:
            statement = statement.where(UsuarioEquipe.status == status)
        if principal is not None:
            statement = statement.where(UsuarioEquipe.principal.is_(principal))

        statement = statement.order_by(UsuarioEquipe.created_at.desc(), UsuarioEquipe.id.asc())
        statement = statement.limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    def list_by_usuario(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str,
        status: str | None = None,
    ) -> list[UsuarioEquipe]:
        statement = select(UsuarioEquipe).where(
            UsuarioEquipe.empresa_id == empresa_id,
            UsuarioEquipe.usuario_id == usuario_id,
        )
        if status:
            statement = statement.where(UsuarioEquipe.status == status)
        statement = statement.order_by(UsuarioEquipe.created_at.desc(), UsuarioEquipe.id.asc())
        return list(db.scalars(statement).all())

    def list_by_equipe(
        self,
        db: Session,
        *,
        empresa_id: str,
        equipe_id: str,
        status: str | None = None,
    ) -> list[UsuarioEquipe]:
        statement = select(UsuarioEquipe).where(
            UsuarioEquipe.empresa_id == empresa_id,
            UsuarioEquipe.equipe_id == equipe_id,
        )
        if status:
            statement = statement.where(UsuarioEquipe.status == status)
        statement = statement.order_by(UsuarioEquipe.created_at.desc(), UsuarioEquipe.id.asc())
        return list(db.scalars(statement).all())

    def get_active_by_usuario_equipe(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str,
        equipe_id: str,
    ) -> UsuarioEquipe | None:
        statement = select(UsuarioEquipe).where(
            UsuarioEquipe.empresa_id == empresa_id,
            UsuarioEquipe.usuario_id == usuario_id,
            UsuarioEquipe.equipe_id == equipe_id,
            UsuarioEquipe.status == "ativo",
        )
        return db.scalars(statement).first()

    def get_active_lider_by_equipe(
        self,
        db: Session,
        *,
        empresa_id: str,
        equipe_id: str,
    ) -> UsuarioEquipe | None:
        statement = select(UsuarioEquipe).where(
            UsuarioEquipe.empresa_id == empresa_id,
            UsuarioEquipe.equipe_id == equipe_id,
            UsuarioEquipe.papel == "lider",
            UsuarioEquipe.status == "ativo",
        )
        return db.scalars(statement).first()

    def get_active_principal_by_usuario(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str,
    ) -> UsuarioEquipe | None:
        statement = select(UsuarioEquipe).where(
            UsuarioEquipe.empresa_id == empresa_id,
            UsuarioEquipe.usuario_id == usuario_id,
            UsuarioEquipe.principal.is_(True),
            UsuarioEquipe.status == "ativo",
        )
        return db.scalars(statement).first()

    def update(self, db: Session, vinculo: UsuarioEquipe) -> UsuarioEquipe:
        db.add(vinculo)
        db.flush()
        return vinculo

    def encerrar(self, db: Session, vinculo: UsuarioEquipe) -> UsuarioEquipe:
        db.add(vinculo)
        db.flush()
        return vinculo
