"""Persistência da capacidade individual (11B.2D-A): jornada semanal própria e ausências. Só consultas e gravações — regras, eventos e autoridade ficam no service."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.usuario_capacidade import UsuarioAusencia, UsuarioJornada, UsuarioJornadaPeriodo


class UsuarioCapacidadeRepository:
    # ── jornada ──────────────────────────────────────────────────────────────────────────────────────────────

    def get_jornada(self, db: Session, usuario_id: str) -> UsuarioJornada | None:
        return db.scalars(select(UsuarioJornada).where(UsuarioJornada.usuario_id == usuario_id)).first()

    def list_periodos(self, db: Session, jornada_id: str) -> dict[int, list[UsuarioJornadaPeriodo]]:
        linhas = db.scalars(
            select(UsuarioJornadaPeriodo)
            .where(UsuarioJornadaPeriodo.jornada_id == jornada_id)
            .order_by(UsuarioJornadaPeriodo.dia_semana.asc(), UsuarioJornadaPeriodo.ordem.asc())
        ).all()
        por_dia: dict[int, list[UsuarioJornadaPeriodo]] = defaultdict(list)
        for linha in linhas:
            por_dia[linha.dia_semana].append(linha)
        return por_dia

    def add_jornada(self, db: Session, jornada: UsuarioJornada) -> UsuarioJornada:
        db.add(jornada)
        db.flush()
        return jornada

    def replace_periodos(self, db: Session, jornada_id: str, periodos: list[UsuarioJornadaPeriodo]) -> None:
        db.execute(delete(UsuarioJornadaPeriodo).where(UsuarioJornadaPeriodo.jornada_id == jornada_id))
        for periodo in periodos:
            db.add(periodo)
        db.flush()

    def delete_jornada(self, db: Session, jornada: UsuarioJornada) -> None:
        db.execute(delete(UsuarioJornadaPeriodo).where(UsuarioJornadaPeriodo.jornada_id == jornada.id))
        db.delete(jornada)
        db.flush()

    # ── ausências ────────────────────────────────────────────────────────────────────────────────────────────

    def list_ausencias(self, db: Session, *, empresa_id: str, usuario_id: str, desde: date | None = None, ate: date | None = None) -> list[UsuarioAusencia]:
        """Ausências do usuário que TOCAM o intervalo [desde, ate] (qualquer ponta aberta = sem limite), da mais recente para a mais antiga."""
        consulta = select(UsuarioAusencia).where(UsuarioAusencia.empresa_id == empresa_id, UsuarioAusencia.usuario_id == usuario_id)
        if desde is not None:
            consulta = consulta.where(UsuarioAusencia.fim >= desde)
        if ate is not None:
            consulta = consulta.where(UsuarioAusencia.inicio <= ate)
        return list(db.scalars(consulta.order_by(UsuarioAusencia.inicio.desc(), UsuarioAusencia.id.asc())).all())

    def get_ausencia(self, db: Session, *, empresa_id: str, usuario_id: str, ausencia_id: str) -> UsuarioAusencia | None:
        return db.scalars(
            select(UsuarioAusencia).where(
                UsuarioAusencia.id == ausencia_id, UsuarioAusencia.usuario_id == usuario_id, UsuarioAusencia.empresa_id == empresa_id
            )
        ).first()

    def add_ausencia(self, db: Session, ausencia: UsuarioAusencia) -> UsuarioAusencia:
        db.add(ausencia)
        db.flush()
        return ausencia

    def delete_ausencia(self, db: Session, ausencia: UsuarioAusencia) -> None:
        db.delete(ausencia)
        db.flush()
