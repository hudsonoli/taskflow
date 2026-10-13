from __future__ import annotations

from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.regra_expediente import (
    RegraExpedienteDia,
    RegraExpedienteDiaEspecial,
    RegraExpedienteDiaEspecialPeriodo,
    RegraExpedientePeriodo,
)
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

    # ── períodos (Fase Expediente 1) ─────────────────────────────────────────────────────────────────────────────

    def list_periodos(self, db: Session, regra_expediente_id: str) -> dict[int, list[RegraExpedientePeriodo]]:
        """Períodos da regra agrupados por dia da semana, na ordem."""
        statement = (
            select(RegraExpedientePeriodo)
            .where(RegraExpedientePeriodo.regra_expediente_id == regra_expediente_id)
            .order_by(RegraExpedientePeriodo.dia_semana.asc(), RegraExpedientePeriodo.ordem.asc())
        )
        agrupados: dict[int, list[RegraExpedientePeriodo]] = defaultdict(list)
        for periodo in db.scalars(statement).all():
            agrupados[periodo.dia_semana].append(periodo)
        return agrupados

    def replace_periodos_do_dia(
        self, db: Session, regra_expediente_id: str, dia_semana: int, periodos: list[RegraExpedientePeriodo]
    ) -> None:
        db.execute(
            delete(RegraExpedientePeriodo).where(
                RegraExpedientePeriodo.regra_expediente_id == regra_expediente_id,
                RegraExpedientePeriodo.dia_semana == dia_semana,
            )
        )
        db.flush()
        for periodo in periodos:
            db.add(periodo)
        db.flush()

    # ── dias especiais ───────────────────────────────────────────────────────────────────────────────────────────

    def list_dias_especiais(self, db: Session, regra_expediente_id: str) -> list[RegraExpedienteDiaEspecial]:
        statement = (
            select(RegraExpedienteDiaEspecial)
            .where(RegraExpedienteDiaEspecial.regra_expediente_id == regra_expediente_id)
            .order_by(RegraExpedienteDiaEspecial.data.asc(), RegraExpedienteDiaEspecial.origem.asc())
        )
        return list(db.scalars(statement).all())

    def get_dia_especial(self, db: Session, dia_especial_id: str) -> RegraExpedienteDiaEspecial | None:
        return db.get(RegraExpedienteDiaEspecial, dia_especial_id)

    def find_dia_especial(self, db: Session, regra_expediente_id: str, data, origem: str) -> RegraExpedienteDiaEspecial | None:
        statement = select(RegraExpedienteDiaEspecial).where(
            RegraExpedienteDiaEspecial.regra_expediente_id == regra_expediente_id,
            RegraExpedienteDiaEspecial.data == data,
            RegraExpedienteDiaEspecial.origem == origem,
        )
        return db.scalars(statement).first()

    def save_dia_especial(self, db: Session, dia: RegraExpedienteDiaEspecial) -> RegraExpedienteDiaEspecial:
        db.add(dia)
        db.flush()
        return dia

    def delete_dia_especial(self, db: Session, dia: RegraExpedienteDiaEspecial) -> None:
        db.delete(dia)
        db.flush()

    def list_periodos_especiais(
        self, db: Session, dia_especial_ids: list[str]
    ) -> dict[str, list[RegraExpedienteDiaEspecialPeriodo]]:
        if not dia_especial_ids:
            return {}
        statement = (
            select(RegraExpedienteDiaEspecialPeriodo)
            .where(RegraExpedienteDiaEspecialPeriodo.dia_especial_id.in_(dia_especial_ids))
            .order_by(RegraExpedienteDiaEspecialPeriodo.dia_especial_id.asc(), RegraExpedienteDiaEspecialPeriodo.ordem.asc())
        )
        agrupados: dict[str, list[RegraExpedienteDiaEspecialPeriodo]] = defaultdict(list)
        for periodo in db.scalars(statement).all():
            agrupados[periodo.dia_especial_id].append(periodo)
        return agrupados

    def replace_periodos_especiais(
        self, db: Session, dia_especial_id: str, periodos: list[RegraExpedienteDiaEspecialPeriodo]
    ) -> None:
        db.execute(
            delete(RegraExpedienteDiaEspecialPeriodo).where(RegraExpedienteDiaEspecialPeriodo.dia_especial_id == dia_especial_id)
        )
        db.flush()
        for periodo in periodos:
            db.add(periodo)
        db.flush()
