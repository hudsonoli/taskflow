from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.tipo_tarefa import TipoTarefa

STATUS_ARQUIVADO = "arquivado"
STATUS_ATIVO = "ativo"


class TipoTarefaRepository:
    """Só persistência e consultas — regras de duplicidade, transição, arquivamento e
    eventos ficam no service."""

    def create(self, db: Session, tipo_tarefa: TipoTarefa) -> TipoTarefa:
        db.add(tipo_tarefa)
        db.flush()
        return tipo_tarefa

    def get_by_id(self, db: Session, tipo_tarefa_id: str) -> TipoTarefa | None:
        return db.get(TipoTarefa, tipo_tarefa_id)

    def get_by_nome_normalizado(
        self, db: Session, *, empresa_id: str, nome_normalizado: str
    ) -> TipoTarefa | None:
        """Qualquer status — a unicidade de nome vale entre ativo, inativo e arquivado."""
        statement = select(TipoTarefa).where(
            TipoTarefa.empresa_id == empresa_id,
            TipoTarefa.nome_normalizado == nome_normalizado,
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
    ) -> list[TipoTarefa]:
        statement = select(TipoTarefa).where(TipoTarefa.empresa_id == empresa_id)

        if status:
            statement = statement.where(TipoTarefa.status == status)
        else:
            # Sem status explícito, arquivado fica oculto — filtro em SQL, antes da paginação.
            statement = statement.where(TipoTarefa.status != STATUS_ARQUIVADO)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(TipoTarefa.nome.ilike(term), TipoTarefa.descricao.ilike(term))
            )

        statement = statement.order_by(TipoTarefa.ordem.asc(), TipoTarefa.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, tipo_tarefa: TipoTarefa) -> TipoTarefa:
        db.add(tipo_tarefa)
        db.flush()
        return tipo_tarefa

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[TipoTarefa]:
        """Só `ativo` — sem referência histórica a resolver aqui (mesmo padrão de
        WorkflowModeloRepository.list_diretorio, ver docstring do schema)."""
        statement = (
            select(TipoTarefa)
            .where(TipoTarefa.empresa_id == empresa_id, TipoTarefa.status == STATUS_ATIVO)
            .order_by(TipoTarefa.ordem.asc(), TipoTarefa.nome.asc())
        )
        return list(db.scalars(statement).all())
