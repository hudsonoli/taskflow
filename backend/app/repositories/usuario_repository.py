from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


class UsuarioRepository:
    def create(self, db: Session, usuario: Usuario) -> Usuario:
        db.add(usuario)
        db.flush()
        return usuario

    def get_by_id(self, db: Session, usuario_id: str) -> Usuario | None:
        return db.get(Usuario, usuario_id)

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> Usuario | None:
        statement = select(Usuario).where(
            Usuario.empresa_id == empresa_id,
            Usuario.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_email(self, db: Session, *, empresa_id: str, email: str) -> Usuario | None:
        statement = select(Usuario).where(
            Usuario.empresa_id == empresa_id,
            Usuario.email == email,
        )
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        perfil_base: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Usuario]:
        statement = select(Usuario).where(Usuario.empresa_id == empresa_id)

        if status:
            statement = statement.where(Usuario.status == status)
        if perfil_base:
            statement = statement.where(Usuario.perfil_base == perfil_base)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Usuario.nome.ilike(term),
                    Usuario.email.ilike(term),
                    Usuario.codigo_interno.ilike(term),
                )
            )

        statement = statement.order_by(Usuario.created_at.desc(), Usuario.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, usuario: Usuario) -> Usuario:
        db.add(usuario)
        db.flush()
        return usuario
