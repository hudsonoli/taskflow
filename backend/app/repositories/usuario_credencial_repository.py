from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario_credencial import UsuarioCredencial


class UsuarioCredencialRepository:
    def create(self, db: Session, credencial: UsuarioCredencial) -> UsuarioCredencial:
        db.add(credencial)
        db.flush()
        return credencial

    def get_by_usuario_id(self, db: Session, usuario_id: str) -> UsuarioCredencial | None:
        statement = select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == usuario_id)
        return db.scalars(statement).first()

    def update(self, db: Session, credencial: UsuarioCredencial) -> UsuarioCredencial:
        db.add(credencial)
        db.flush()
        return credencial
