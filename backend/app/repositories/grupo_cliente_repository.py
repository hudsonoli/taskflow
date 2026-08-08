from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.grupo_cliente import GrupoCliente

STATUS_ARQUIVADO = "arquivado"


class GrupoClienteRepository:
    """Só persistência e consultas — nenhuma regra de negócio (duplicidade, transição de
    status, arquivamento/restauração, eventos) mora aqui, fica no service."""

    def create(self, db: Session, grupo: GrupoCliente) -> GrupoCliente:
        db.add(grupo)
        db.flush()
        return grupo

    def get_by_id(self, db: Session, grupo_id: str) -> GrupoCliente | None:
        return db.get(GrupoCliente, grupo_id)

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> GrupoCliente | None:
        statement = select(GrupoCliente).where(
            GrupoCliente.empresa_id == empresa_id,
            GrupoCliente.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_nome_normalizado(self, db: Session, *, empresa_id: str, nome_normalizado: str) -> GrupoCliente | None:
        """Qualquer status — a unicidade de nome vale entre ativos e arquivados (ver
        GrupoClienteService)."""
        statement = select(GrupoCliente).where(
            GrupoCliente.empresa_id == empresa_id,
            GrupoCliente.nome_normalizado == nome_normalizado,
        )
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GrupoCliente]:
        statement = select(GrupoCliente).where(GrupoCliente.empresa_id == empresa_id)

        if status:
            statement = statement.where(GrupoCliente.status == status)
        else:
            # Sem status explícito, arquivado fica oculto por padrão — filtro SQL, antes da
            # paginação (mesmo contrato de UsuarioRepository.list).
            statement = statement.where(GrupoCliente.status != STATUS_ARQUIVADO)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    GrupoCliente.nome.ilike(term),
                    GrupoCliente.codigo_interno.ilike(term),
                )
            )

        statement = statement.order_by(GrupoCliente.created_at.desc(), GrupoCliente.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[GrupoCliente]:
        """Inclui ativos E arquivados de propósito — resolução histórica de
        `Cliente.tagIds` antigos. A UI decide o que oferecer como opção nova (só ativo)."""
        statement = select(GrupoCliente).where(GrupoCliente.empresa_id == empresa_id)
        statement = statement.order_by(GrupoCliente.nome.asc())
        return list(db.scalars(statement).all())

    def update(self, db: Session, grupo: GrupoCliente) -> GrupoCliente:
        db.add(grupo)
        db.flush()
        return grupo
