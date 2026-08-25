from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.projeto_modelo_campanha import ProjetoModeloCampanha, ProjetoModeloCampanhaItem


class ProjetoModeloCampanhaRepository:
    """Só persistência e consultas do snapshot — regras de negócio (validação de
    referências, atomicidade, eventos) ficam no service. Não duplica nada de
    `ProjetoRepository`: só conhece as duas tabelas do snapshot."""

    def get_by_projeto_id(self, db: Session, projeto_id: str) -> ProjetoModeloCampanha | None:
        statement = select(ProjetoModeloCampanha).where(ProjetoModeloCampanha.projeto_id == projeto_id)
        return db.scalars(statement).first()

    def create(self, db: Session, cabecalho: ProjetoModeloCampanha) -> ProjetoModeloCampanha:
        db.add(cabecalho)
        db.flush()
        return cabecalho

    def update(self, db: Session, cabecalho: ProjetoModeloCampanha) -> ProjetoModeloCampanha:
        db.add(cabecalho)
        db.flush()
        return cabecalho

    # ----------------------------------------------------------------------------------
    # Itens — sempre o agregado inteiro, nunca item avulso (ver ProjetoModeloCampanhaService)
    # ----------------------------------------------------------------------------------

    def list_itens(self, db: Session, projeto_modelo_campanha_id: str) -> list[ProjetoModeloCampanhaItem]:
        statement = (
            select(ProjetoModeloCampanhaItem)
            .where(ProjetoModeloCampanhaItem.projeto_modelo_campanha_id == projeto_modelo_campanha_id)
            .order_by(ProjetoModeloCampanhaItem.ordem.asc())
        )
        return list(db.scalars(statement).all())

    def replace_itens(
        self, db: Session, *, projeto_modelo_campanha_id: str, itens: list[ProjetoModeloCampanhaItem]
    ) -> list[ProjetoModeloCampanhaItem]:
        """Substitui o conjunto inteiro de itens — mesmo padrão de
        `ModeloCampanhaRepository.replace_itens`/`WorkflowModeloRepository.replace_etapas`.
        Usado tanto por aplicar/reaplicar (materialização) quanto por PATCH (edição)."""
        db.execute(
            delete(ProjetoModeloCampanhaItem).where(
                ProjetoModeloCampanhaItem.projeto_modelo_campanha_id == projeto_modelo_campanha_id
            )
        )
        db.flush()
        for item in itens:
            db.add(item)
        db.flush()
        return itens
