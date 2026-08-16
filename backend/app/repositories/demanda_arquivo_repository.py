from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demanda_arquivo import DemandaArquivo


class DemandaArquivoRepository:
    """Só persistência e consultas de metadado. O conteúdo físico é responsabilidade do
    service (`DemandaArquivoService`), que é quem decide o caminho em disco."""

    def create(self, db: Session, arquivo: DemandaArquivo) -> DemandaArquivo:
        db.add(arquivo)
        db.flush()
        return arquivo

    def delete(self, db: Session, arquivo: DemandaArquivo) -> None:
        db.delete(arquivo)
        db.flush()

    def get_by_id(self, db: Session, arquivo_id: str) -> DemandaArquivo | None:
        return db.get(DemandaArquivo, arquivo_id)

    def list_by_demanda(self, db: Session, demanda_id: str) -> list[DemandaArquivo]:
        statement = (
            select(DemandaArquivo)
            .where(DemandaArquivo.demanda_id == demanda_id)
            .order_by(DemandaArquivo.created_at.desc())
        )
        return list(db.scalars(statement).all())
