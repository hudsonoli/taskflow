from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demanda_status_intervalo import DemandaStatusIntervalo


class DemandaStatusIntervaloRepository:
    def get_aberto(self, db: Session, demanda_id: str) -> DemandaStatusIntervalo | None:
        """O intervalo ABERTO da Demanda (no máximo um — índice único parcial), travado (`FOR UPDATE`) e relido do banco."""
        return db.scalar(
            select(DemandaStatusIntervalo)
            .where(DemandaStatusIntervalo.demanda_id == demanda_id, DemandaStatusIntervalo.fim_em.is_(None))
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def create(self, db: Session, intervalo: DemandaStatusIntervalo) -> DemandaStatusIntervalo:
        db.add(intervalo)
        db.flush()
        return intervalo

    def listar_da_demanda(self, db: Session, demanda_id: str) -> list[DemandaStatusIntervalo]:
        """A linha do tempo da Demanda em ordem cronológica (para consulta/testes; os endpoints de métricas vêm numa fase futura)."""
        return list(
            db.scalars(
                select(DemandaStatusIntervalo)
                .where(DemandaStatusIntervalo.demanda_id == demanda_id)
                .order_by(DemandaStatusIntervalo.inicio_em.asc(), DemandaStatusIntervalo.created_at.asc(), DemandaStatusIntervalo.id.asc())
                .execution_options(populate_existing=True)
            ).all()
        )
