from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sequencia_operacional import SequenciaOperacional


class SequenciaOperacionalRepository:
    """Só leitura nesta fase (Fase 2G.8B) — a escrita/reserva do contador continua exclusiva
    de `app/core/sequencias_operacionais.py::reservar_proximo_operacional` (UPSERT atômico via
    SQL cru, nunca duplicado aqui). Este repository existe só para telas administrativas
    lerem o estado atual sem consumir/incrementar nada.
    """

    def get_ultimo_numero(self, db: Session, *, empresa_id: str, tipo_entidade: str) -> int | None:
        """`None` quando a linha ainda não existe (nenhuma reserva feita nem seed via CLI) —
        quem chama decide o default de apresentação (ver ConfiguracaoNumeracaoTarefaService)."""
        statement = select(SequenciaOperacional.ultimo_numero).where(
            SequenciaOperacional.empresa_id == empresa_id,
            SequenciaOperacional.tipo_entidade == tipo_entidade,
        )
        return db.scalars(statement).first()
