from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.sla_regra import SlaRegra

STATUS_ARQUIVADO = "arquivado"


class SlaRegraRepository:
    """Só persistência e consultas do CRUD — regras de duplicidade, transição, arquivamento e
    eventos ficam no service. Nenhuma query de resolução (por prioridade/departamento/cliente
    combinados) aqui: isso é `SlaResolver`, Fase 2G.6C — ver docstring de app/models/sla_regra.py."""

    def create(self, db: Session, sla_regra: SlaRegra) -> SlaRegra:
        db.add(sla_regra)
        db.flush()
        return sla_regra

    def get_by_id(self, db: Session, sla_regra_id: str) -> SlaRegra | None:
        return db.get(SlaRegra, sla_regra_id)

    def get_by_nome_normalizado(self, db: Session, *, empresa_id: str, nome_normalizado: str) -> SlaRegra | None:
        """Qualquer status — a unicidade de nome vale entre ativo, inativo e arquivado."""
        statement = select(SlaRegra).where(
            SlaRegra.empresa_id == empresa_id,
            SlaRegra.nome_normalizado == nome_normalizado,
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
    ) -> list[SlaRegra]:
        statement = select(SlaRegra).where(SlaRegra.empresa_id == empresa_id)

        if status:
            statement = statement.where(SlaRegra.status == status)
        else:
            # Sem status explícito, arquivado fica oculto — filtro em SQL, antes da paginação.
            statement = statement.where(SlaRegra.status != STATUS_ARQUIVADO)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(or_(SlaRegra.nome.ilike(term), SlaRegra.descricao.ilike(term)))

        statement = statement.order_by(SlaRegra.prioridade_regra.asc(), SlaRegra.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, sla_regra: SlaRegra) -> SlaRegra:
        db.add(sla_regra)
        db.flush()
        return sla_regra
