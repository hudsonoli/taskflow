from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.sla_regra import SlaRegra

STATUS_ATIVO = "ativo"


class SlaResolverRepository:
    """Query candidata pro `resolver_sla` (Fase 2G.6C) — deliberadamente separado de
    `SlaRegraRepository` (CRUD), que documenta explicitamente não ter nenhuma query de
    resolução (ver docstring de app/repositories/sla_regra_repository.py). Só filtra os
    candidatos possíveis; a ordenação de precedência (que depende de especificidade, calculada
    em Python) é responsabilidade de `app/core/sla_resolver.py`, não daqui.
    """

    def list_candidatas(
        self,
        db: Session,
        *,
        empresa_id: str,
        prioridade: str | None,
        departamento_id: str | None,
        cliente_id: str | None,
    ) -> list[SlaRegra]:
        """Só `status == ativo` da própria Empresa (nunca cross-tenant — `empresa_id` é
        obrigatório e vem sempre do caller, nunca do resultado da query).

        Cada critério casa se a regra tiver `NULL` (curinga) OU o valor exato recebido. Quando
        `departamento_id`/`cliente_id` do chamador é `None`, só regras com aquele campo `NULL`
        continuam candidatas — não existe "combinar com nenhum" tornando uma regra específica
        elegível.
        """
        statement = select(SlaRegra).where(
            SlaRegra.empresa_id == empresa_id,
            SlaRegra.status == STATUS_ATIVO,
            or_(SlaRegra.prioridade_alvo.is_(None), SlaRegra.prioridade_alvo == prioridade),
            or_(SlaRegra.departamento_id.is_(None), SlaRegra.departamento_id == departamento_id),
            or_(SlaRegra.cliente_id.is_(None), SlaRegra.cliente_id == cliente_id),
        )
        return list(db.scalars(statement).all())
