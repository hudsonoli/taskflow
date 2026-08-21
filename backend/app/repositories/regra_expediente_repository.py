from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.regra_expediente import RegraExpedienteDia
from app.models.regra_expediente import RegraExpediente as RegraExpedienteModel


class RegraExpedienteRepository:
    """Só persistência e consultas — inicialização, conversão pro DTO de cálculo e eventos
    ficam no service."""

    def get_by_empresa(self, db: Session, empresa_id: str) -> RegraExpedienteModel | None:
        statement = select(RegraExpedienteModel).where(RegraExpedienteModel.empresa_id == empresa_id)
        return db.scalars(statement).first()

    def create(self, db: Session, regra: RegraExpedienteModel) -> RegraExpedienteModel:
        db.add(regra)
        db.flush()
        return regra

    def update(self, db: Session, regra: RegraExpedienteModel) -> RegraExpedienteModel:
        db.add(regra)
        db.flush()
        return regra

    def list_dias(self, db: Session, regra_expediente_id: str) -> list[RegraExpedienteDia]:
        statement = (
            select(RegraExpedienteDia)
            .where(RegraExpedienteDia.regra_expediente_id == regra_expediente_id)
            .order_by(RegraExpedienteDia.dia_semana.asc())
        )
        return list(db.scalars(statement).all())

    def create_dias(self, db: Session, dias: list[RegraExpedienteDia]) -> None:
        for dia in dias:
            db.add(dia)
        db.flush()

    def update_dia(self, db: Session, dia: RegraExpedienteDia) -> RegraExpedienteDia:
        db.add(dia)
        db.flush()
        return dia
