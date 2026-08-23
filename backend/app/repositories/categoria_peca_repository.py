from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.categoria_peca import CategoriaPeca

STATUS_ARQUIVADO = "arquivado"
STATUS_ATIVO = "ativo"


class CategoriaPecaRepository:
    """Só persistência e consultas — regras de duplicidade, transição e eventos ficam no
    service."""

    def create(self, db: Session, categoria: CategoriaPeca) -> CategoriaPeca:
        db.add(categoria)
        db.flush()
        return categoria

    def get_by_id(self, db: Session, categoria_id: str) -> CategoriaPeca | None:
        return db.get(CategoriaPeca, categoria_id)

    def get_by_nome_normalizado(
        self, db: Session, *, empresa_id: str, nome_normalizado: str
    ) -> CategoriaPeca | None:
        """Qualquer status — a unicidade de nome vale entre ativo e arquivado."""
        statement = select(CategoriaPeca).where(
            CategoriaPeca.empresa_id == empresa_id,
            CategoriaPeca.nome_normalizado == nome_normalizado,
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
    ) -> list[CategoriaPeca]:
        statement = select(CategoriaPeca).where(CategoriaPeca.empresa_id == empresa_id)

        if status:
            statement = statement.where(CategoriaPeca.status == status)
        else:
            statement = statement.where(CategoriaPeca.status != STATUS_ARQUIVADO)
        if search:
            statement = statement.where(CategoriaPeca.nome.ilike(f"%{search.strip()}%"))

        statement = statement.order_by(CategoriaPeca.ordem.asc(), CategoriaPeca.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, categoria: CategoriaPeca) -> CategoriaPeca:
        db.add(categoria)
        db.flush()
        return categoria

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[CategoriaPeca]:
        statement = (
            select(CategoriaPeca)
            .where(CategoriaPeca.empresa_id == empresa_id, CategoriaPeca.status == STATUS_ATIVO)
            .order_by(CategoriaPeca.ordem.asc(), CategoriaPeca.nome.asc())
        )
        return list(db.scalars(statement).all())

    def list_by_ids(self, db: Session, *, ids: list[str]) -> list[CategoriaPeca]:
        """Busca em lote — usada pelo service pra resolver `categoriaNome` de uma lista de
        Peças sem N+1 (uma query por listagem, não uma por item)."""
        if not ids:
            return []
        statement = select(CategoriaPeca).where(CategoriaPeca.id.in_(ids))
        return list(db.scalars(statement).all())
