from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.demanda_checklist_item import DemandaChecklistItem


class DemandaChecklistRepository:
    """Só persistência e consultas — a Demanda-mãe já chega resolvida e escopada de quem
    chama (mesmo padrão de DemandaRepository); este repository nunca decide acesso."""

    def create(self, db: Session, item: DemandaChecklistItem) -> DemandaChecklistItem:
        db.add(item)
        db.flush()
        return item

    def update(self, db: Session, item: DemandaChecklistItem) -> DemandaChecklistItem:
        db.add(item)
        db.flush()
        return item

    def delete(self, db: Session, item: DemandaChecklistItem) -> None:
        db.delete(item)
        db.flush()

    def get_by_id(self, db: Session, item_id: str) -> DemandaChecklistItem | None:
        return db.get(DemandaChecklistItem, item_id)

    def list_by_demanda(self, db: Session, demanda_id: str) -> list[DemandaChecklistItem]:
        statement = (
            select(DemandaChecklistItem)
            .where(DemandaChecklistItem.demanda_id == demanda_id)
            .order_by(DemandaChecklistItem.ordem.asc())
        )
        return list(db.scalars(statement).all())

    def proxima_ordem(self, db: Session, demanda_id: str) -> int:
        """Novo item sempre entra no fim — maior `ordem` + 1, ou 0 se a lista estiver vazia."""
        maior = db.scalar(
            select(func.max(DemandaChecklistItem.ordem)).where(
                DemandaChecklistItem.demanda_id == demanda_id
            )
        )
        return (maior + 1) if maior is not None else 0
