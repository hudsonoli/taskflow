from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.peca import Peca

STATUS_ARQUIVADO = "arquivado"
STATUS_ATIVO = "ativo"


class PecaRepository:
    """Só persistência e consultas — regras de negócio (categoria válida, ciclo de vida,
    eventos) ficam no service."""

    def create(self, db: Session, peca: Peca) -> Peca:
        db.add(peca)
        db.flush()
        return peca

    def get_by_id(self, db: Session, peca_id: str) -> Peca | None:
        return db.get(Peca, peca_id)

    def get_by_codigo_legado(self, db: Session, *, empresa_id: str, codigo_legado: str) -> Peca | None:
        """Identidade do import (Fase 2G.4) — ver docstring de app/cli/importar_pecas.py.
        Nunca usar nome como chave de idempotência."""
        statement = select(Peca).where(
            Peca.empresa_id == empresa_id,
            Peca.codigo_legado == codigo_legado,
        )
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        categoria_id: str | None = None,
        search: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Peca]:
        statement = select(Peca).where(Peca.empresa_id == empresa_id)

        if status:
            statement = statement.where(Peca.status == status)
        else:
            statement = statement.where(Peca.status != STATUS_ARQUIVADO)
        if categoria_id:
            statement = statement.where(Peca.categoria_id == categoria_id)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(or_(Peca.nome.ilike(term), Peca.briefing_padrao.ilike(term)))

        statement = statement.order_by(Peca.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, peca: Peca) -> Peca:
        db.add(peca)
        db.flush()
        return peca

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Peca]:
        statement = (
            select(Peca)
            .where(Peca.empresa_id == empresa_id, Peca.status == STATUS_ATIVO)
            .order_by(Peca.nome.asc())
        )
        return list(db.scalars(statement).all())
