from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc

from app.models.sequencia_operacional import SequenciaOperacional


class SequenciaOperacionalRepository:
    """A RESERVA do número continua exclusiva de `app/core/sequencias_operacionais.py` (UPSERT atômico via SQL cru, nunca duplicado
    aqui). Este repository serve às telas administrativas: lê o estado e (Fase 7D.1) trava a linha do contador para alterar o
    formato / o próximo número sem correr contra uma emissão.
    """

    def get_linha(self, db: Session, *, empresa_id: str, tipo_entidade: str) -> SequenciaOperacional | None:
        return db.scalars(
            select(SequenciaOperacional).where(
                SequenciaOperacional.empresa_id == empresa_id, SequenciaOperacional.tipo_entidade == tipo_entidade
            )
        ).first()

    def travar_linha(self, db: Session, *, empresa_id: str, tipo_entidade: str) -> SequenciaOperacional:
        """Garante a linha (contador 0 se ainda não houve emissão) e a devolve com `SELECT ... FOR UPDATE`.

        É O MESMO lock que `reservar_proximo_*` toma ao incrementar: quem chega depois espera o commit/rollback de quem chegou
        antes. Assim o PATCH enxerga o maior número emitido já definitivo e uma emissão concorrente não grava por cima.
        """
        agora = agora_utc()
        db.execute(
            text(
                """
                INSERT INTO sequencias_operacionais (id, empresa_id, tipo_entidade, ultimo_numero, created_at, updated_at)
                VALUES (:id, :empresa_id, :tipo_entidade, 0, :agora, :agora)
                ON CONFLICT (empresa_id, tipo_entidade) DO NOTHING
                """
            ),
            {"id": str(uuid4()), "empresa_id": empresa_id, "tipo_entidade": tipo_entidade, "agora": agora},
        )
        return db.scalars(
            select(SequenciaOperacional)
            .where(SequenciaOperacional.empresa_id == empresa_id, SequenciaOperacional.tipo_entidade == tipo_entidade)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one()

    def get_ultimo_numero(self, db: Session, *, empresa_id: str, tipo_entidade: str) -> int | None:
        """`None` quando a linha ainda não existe (nenhuma reserva feita nem seed via CLI) —
        quem chama decide o default de apresentação (ver ConfiguracaoNumeracaoTarefaService)."""
        statement = select(SequenciaOperacional.ultimo_numero).where(
            SequenciaOperacional.empresa_id == empresa_id,
            SequenciaOperacional.tipo_entidade == tipo_entidade,
        )
        return db.scalars(statement).first()
