from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.departamento import Departamento

STATUS_ARQUIVADO = "arquivado"


class DepartamentoRepository:
    """Só persistência e consultas — regras de duplicidade, transição, arquivamento e
    eventos ficam no service."""

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

    def get_by_nome_normalizado(self, db: Session, *, empresa_id: str, nome_normalizado: str) -> Departamento | None:
        """Qualquer status — a unicidade de nome vale entre ativos, inativos e arquivados."""
        statement = select(Departamento).where(
            Departamento.empresa_id == empresa_id,
            Departamento.nome_normalizado == nome_normalizado,
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
    ) -> list[Departamento]:
        statement = select(Departamento).where(Departamento.empresa_id == empresa_id)

        if status:
            statement = statement.where(Departamento.status == status)
        else:
            # Sem status explícito, arquivado fica oculto — filtro em SQL, antes da paginação.
            statement = statement.where(Departamento.status != STATUS_ARQUIVADO)
        if search:
            term = f"%{search.strip()}%"
            # ILIKE cobre a busca case-insensitive por código (d26000001 = D26000001).
            statement = statement.where(
                or_(
                    Departamento.nome.ilike(term),
                    Departamento.codigo_referencia.ilike(term),
                    Departamento.codigo_interno.ilike(term),
                )
            )

        statement = statement.order_by(Departamento.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Departamento]:
        """Inclui arquivados — referências antigas precisam continuar resolvendo o nome."""
        statement = (
            select(Departamento)
            .where(Departamento.empresa_id == empresa_id)
            .order_by(Departamento.nome.asc())
        )
        return list(db.scalars(statement).all())

    def update(self, db: Session, departamento: Departamento) -> Departamento:
        db.add(departamento)
        db.flush()
        return departamento
