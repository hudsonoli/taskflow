from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sessao_trabalho import SessaoTrabalho


class SessaoTrabalhoRepository:
    def create(self, db: Session, sessao: SessaoTrabalho) -> SessaoTrabalho:
        db.add(sessao)
        db.flush()
        return sessao

    def flush(self, db: Session) -> None:
        db.flush()

    def get_by_id(self, db: Session, sessao_id: str) -> SessaoTrabalho | None:
        return db.get(SessaoTrabalho, sessao_id)

    def get_by_evento_inicio_id(self, db: Session, evento_inicio_id: str) -> SessaoTrabalho | None:
        statement = select(SessaoTrabalho).where(SessaoTrabalho.evento_inicio_id == evento_inicio_id)
        return db.scalar(statement)

    def get_by_evento_fim_id(self, db: Session, evento_fim_id: str) -> SessaoTrabalho | None:
        statement = select(SessaoTrabalho).where(SessaoTrabalho.evento_fim_id == evento_fim_id)
        return db.scalar(statement)

    def get_active_equivalent(
        self,
        db: Session,
        *,
        demanda_id: str,
        usuario_id: str | None,
        departamento_id: str | None,
    ) -> SessaoTrabalho | None:
        statement = select(SessaoTrabalho).where(
            SessaoTrabalho.demanda_id == demanda_id,
            SessaoTrabalho.status == "ativa",
        )
        if usuario_id:
            statement = statement.where(SessaoTrabalho.usuario_id == usuario_id)
        else:
            statement = statement.where(
                SessaoTrabalho.usuario_id.is_(None),
                SessaoTrabalho.departamento_id == departamento_id,
            )
        return db.scalar(statement)



    def list_active(
        self,
        db: Session,
        *,
        empresa_id: str | None = None,
        demanda_id: str | None = None,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        workflow_etapa_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SessaoTrabalho]:
        statement = select(SessaoTrabalho).where(SessaoTrabalho.status == "ativa")

        if empresa_id:
            statement = statement.where(SessaoTrabalho.empresa_id == empresa_id)
        if demanda_id:
            statement = statement.where(SessaoTrabalho.demanda_id == demanda_id)
        if usuario_id:
            statement = statement.where(SessaoTrabalho.usuario_id == usuario_id)
        if departamento_id:
            statement = statement.where(SessaoTrabalho.departamento_id == departamento_id)
        if workflow_etapa_id:
            statement = statement.where(SessaoTrabalho.workflow_etapa_id == workflow_etapa_id)

        statement = statement.order_by(SessaoTrabalho.inicio_em.asc(), SessaoTrabalho.created_at.asc())
        statement = statement.limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    def list_overlapping_period(
        self,
        db: Session,
        *,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        demanda_id: str | None = None,
    ) -> list[SessaoTrabalho]:
        statement = select(SessaoTrabalho).where(
            SessaoTrabalho.empresa_id == empresa_id,
            SessaoTrabalho.inicio_em <= data_fim,
            (SessaoTrabalho.fim_em.is_(None)) | (SessaoTrabalho.fim_em >= data_inicio),
        )

        if usuario_id:
            statement = statement.where(SessaoTrabalho.usuario_id == usuario_id)
        if departamento_id:
            statement = statement.where(SessaoTrabalho.departamento_id == departamento_id)
        if demanda_id:
            statement = statement.where(SessaoTrabalho.demanda_id == demanda_id)

        statement = statement.order_by(SessaoTrabalho.inicio_em.asc(), SessaoTrabalho.created_at.asc())
        return list(db.scalars(statement).all())

    def list(
        self,
        db: Session,
        *,
        empresa_id: str | None = None,
        demanda_id: str | None = None,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        workflow_etapa_id: str | None = None,
        status: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SessaoTrabalho]:
        statement = select(SessaoTrabalho)

        if empresa_id:
            statement = statement.where(SessaoTrabalho.empresa_id == empresa_id)
        if demanda_id:
            statement = statement.where(SessaoTrabalho.demanda_id == demanda_id)
        if usuario_id:
            statement = statement.where(SessaoTrabalho.usuario_id == usuario_id)
        if departamento_id:
            statement = statement.where(SessaoTrabalho.departamento_id == departamento_id)
        if workflow_etapa_id:
            statement = statement.where(SessaoTrabalho.workflow_etapa_id == workflow_etapa_id)
        if status:
            statement = statement.where(SessaoTrabalho.status == status)
        if data_inicio:
            statement = statement.where(SessaoTrabalho.inicio_em >= data_inicio)
        if data_fim:
            statement = statement.where(SessaoTrabalho.inicio_em <= data_fim)

        statement = statement.order_by(SessaoTrabalho.inicio_em.desc(), SessaoTrabalho.created_at.desc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())
