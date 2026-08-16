from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demanda_comentario import DemandaComentario


class DemandaComentarioRepository:
    """Só persistência e consultas — a Demanda-mãe já chega resolvida e escopada de quem
    chama (mesmo padrão de DemandaChecklistRepository); este repository nunca decide acesso.
    """

    def create(self, db: Session, comentario: DemandaComentario) -> DemandaComentario:
        db.add(comentario)
        db.flush()
        return comentario

    def update(self, db: Session, comentario: DemandaComentario) -> DemandaComentario:
        db.add(comentario)
        db.flush()
        return comentario

    def delete(self, db: Session, comentario: DemandaComentario) -> None:
        db.delete(comentario)
        db.flush()

    def get_by_id(self, db: Session, comentario_id: str) -> DemandaComentario | None:
        return db.get(DemandaComentario, comentario_id)

    def list_by_demanda(self, db: Session, demanda_id: str) -> list[DemandaComentario]:
        # Mais recente primeiro — mesmo comportamento visual que a versão local/mock já
        # tinha (prepend do comentário novo no topo da lista).
        statement = (
            select(DemandaComentario)
            .where(DemandaComentario.demanda_id == demanda_id)
            .order_by(DemandaComentario.created_at.desc())
        )
        return list(db.scalars(statement).all())
