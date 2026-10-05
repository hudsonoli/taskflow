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

    def get_by_reset_token_hash(self, db: Session, token_hash: str) -> UsuarioCredencial | None:
        """Lookup do confirm da recuperação de senha, pelo SHA-256 do token (coluna UNIQUE).

        `FOR UPDATE`: duas confirmações simultâneas do MESMO token se serializam — a segunda só
        lê depois do commit da primeira, que já limpou o token, e falha (uso único de verdade)."""
        statement = (
            select(UsuarioCredencial)
            .where(UsuarioCredencial.reset_senha_token_hash == token_hash)
            .with_for_update()
        )
        return db.scalars(statement).first()

    def update(self, db: Session, credencial: UsuarioCredencial) -> UsuarioCredencial:
        db.add(credencial)
        db.flush()
        return credencial
