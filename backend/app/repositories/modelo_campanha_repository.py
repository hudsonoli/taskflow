from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.modelo_campanha import ModeloCampanha, ModeloCampanhaItem

STATUS_ARQUIVADO = "arquivado"
STATUS_ATIVO = "ativo"


class ModeloCampanhaRepository:
    """Só persistência e consultas — regras de duplicidade, transição, validação de
    referências e eventos ficam no service."""

    def create(self, db: Session, modelo: ModeloCampanha) -> ModeloCampanha:
        db.add(modelo)
        db.flush()
        return modelo

    def get_by_id(self, db: Session, modelo_id: str) -> ModeloCampanha | None:
        return db.get(ModeloCampanha, modelo_id)

    def get_by_nome_normalizado(
        self, db: Session, *, empresa_id: str, nome_normalizado: str
    ) -> ModeloCampanha | None:
        """Qualquer status — a unicidade de nome vale entre ativo, inativo e arquivado."""
        statement = select(ModeloCampanha).where(
            ModeloCampanha.empresa_id == empresa_id,
            ModeloCampanha.nome_normalizado == nome_normalizado,
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
    ) -> list[ModeloCampanha]:
        statement = select(ModeloCampanha).where(ModeloCampanha.empresa_id == empresa_id)

        if status:
            statement = statement.where(ModeloCampanha.status == status)
        else:
            statement = statement.where(ModeloCampanha.status != STATUS_ARQUIVADO)
        if search:
            statement = statement.where(ModeloCampanha.nome.ilike(f"%{search.strip()}%"))

        statement = statement.order_by(ModeloCampanha.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, modelo: ModeloCampanha) -> ModeloCampanha:
        db.add(modelo)
        db.flush()
        return modelo

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[ModeloCampanha]:
        statement = (
            select(ModeloCampanha)
            .where(ModeloCampanha.empresa_id == empresa_id, ModeloCampanha.status == STATUS_ATIVO)
            .order_by(ModeloCampanha.nome.asc())
        )
        return list(db.scalars(statement).all())

    # ----------------------------------------------------------------------------------
    # Itens — sempre o agregado inteiro, nunca item avulso (ver ModeloCampanhaService)
    # ----------------------------------------------------------------------------------

    def list_itens(self, db: Session, modelo_campanha_id: str) -> list[ModeloCampanhaItem]:
        statement = (
            select(ModeloCampanhaItem)
            .where(ModeloCampanhaItem.modelo_campanha_id == modelo_campanha_id)
            .order_by(ModeloCampanhaItem.ordem.asc())
        )
        return list(db.scalars(statement).all())

    def replace_itens(
        self, db: Session, *, modelo_campanha_id: str, itens: list[ModeloCampanhaItem]
    ) -> list[ModeloCampanhaItem]:
        """Substitui o conjunto inteiro de itens — mesmo padrão de
        `WorkflowModeloRepository.replace_etapas`. Sem endpoint incremental de item; o form
        sempre edita o array inteiro."""
        db.execute(delete(ModeloCampanhaItem).where(ModeloCampanhaItem.modelo_campanha_id == modelo_campanha_id))
        db.flush()
        for item in itens:
            db.add(item)
        db.flush()
        return itens
