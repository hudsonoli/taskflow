from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario

STATUS_ARQUIVADO = "arquivado"


class UsuarioRepository:
    def create(self, db: Session, usuario: Usuario) -> Usuario:
        db.add(usuario)
        db.flush()
        return usuario

    def get_by_id(self, db: Session, usuario_id: str) -> Usuario | None:
        """Busca irrestrita — usada internamente por login/`/auth/me`/`/usuarios/me`, onde a
        conta de sistema também precisa conseguir se autenticar e ver o próprio perfil."""
        return db.get(Usuario, usuario_id)

    def get_by_id_visible(self, db: Session, usuario_id: str) -> Usuario | None:
        """Busca administrativa (GET /usuarios/{id}) — nunca devolve a conta de sistema,
        mesmo que o chamador saiba o ID exatamente."""
        usuario = db.get(Usuario, usuario_id)
        if usuario is not None and usuario.is_system_account:
            return None
        return usuario

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
        # A conta de sistema nunca aparece aqui — incondicional, sem parâmetro pra religar.
        statement = select(Usuario).where(Usuario.empresa_id == empresa_id, Usuario.is_system_account.is_(False))

        if status:
            statement = statement.where(Usuario.status == status)
        else:
            # Sem status explícito, arquivado fica oculto por padrão — filtro SQL, antes da
            # paginação (ver docs/padrao-arquivamento.md). `status="arquivado"` explícito
            # continua consultando normalmente.
            statement = statement.where(Usuario.status != STATUS_ARQUIVADO)
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

    def list_diretorio(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        departamento_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Usuario]:
        # Projeção mínima pra seletores de responsável/membro — mesma exclusão incondicional
        # da conta de sistema que list().
        statement = select(Usuario).where(Usuario.empresa_id == empresa_id, Usuario.is_system_account.is_(False))

        if status:
            statement = statement.where(Usuario.status == status)
        else:
            # Sem status explícito: exclui só arquivado (não força "ativo") — referências
            # históricas a usuários inativos/bloqueados ainda precisam resolver nome/avatar
            # (ver docs/padrao-arquivamento.md). Quem quer só ativos filtra no cliente.
            statement = statement.where(Usuario.status != STATUS_ARQUIVADO)
        if departamento_id:
            statement = statement.where(Usuario.departamento_id == departamento_id)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(Usuario.nome.ilike(term))

        statement = statement.order_by(Usuario.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, usuario: Usuario) -> Usuario:
        db.add(usuario)
        db.flush()
        return usuario
