"""Composição resolver + calculadora (Fase 2G.6C) — helper interno, não uma feature nova.

Existe só pra a futura Fase 2G.6D não precisar repetir "chamar resolver_sla, carregar
RegraExpediente, calcular os dois prazos" em cada lugar que precisar. Não persiste nada, não
publica Evento de domínio, não expõe rota — `SlaResolvido` nunca é serializado numa API nem
vira model SQLAlchemy. Se uma fase futura decidir gravar (snapshot em Demanda), é ela quem
escreve; este módulo é somente leitura/cálculo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.calculadora_expediente import calcular_data_limite
from app.core.relogio import agora_local
from app.core.sla_resolver import resolver_sla
from app.models.sla_regra import SlaRegra
from app.services.regra_expediente_service import RegraExpedienteService


@dataclass(frozen=True)
class SlaResolvido:
    """Resultado de `resolver_e_calcular_sla` — estrutura puramente interna."""

    regra: SlaRegra
    prazo_primeira_resposta_em: datetime
    prazo_resolucao_em: datetime


def resolver_e_calcular_sla(
    db: Session,
    *,
    empresa_id: str,
    prioridade: str | None,
    departamento_id: str | None = None,
    cliente_id: str | None = None,
    inicio: datetime | None = None,
    regra_expediente_service: RegraExpedienteService | None = None,
) -> SlaResolvido | None:
    """`inicio` default é `agora_local()` — quem quiser recalcular a partir de outro instante
    (ex.: reprocessamento) pode informar explicitamente. Retorna `None` sem calcular nada
    quando `resolver_sla` não encontra regra combinando — nunca inventa prazo pra ausência de
    SLA (essa decisão é da Demanda, Fase 2G.6D)."""
    regra = resolver_sla(
        db,
        empresa_id=empresa_id,
        prioridade=prioridade,
        departamento_id=departamento_id,
        cliente_id=cliente_id,
    )
    if regra is None:
        return None

    momento_inicio = inicio or agora_local()
    regra_calculo = (regra_expediente_service or RegraExpedienteService()).get_regra_calculo(
        db, empresa_id=empresa_id
    )

    prazo_primeira_resposta_em = calcular_data_limite(
        momento_inicio,
        regra.prazo_primeira_resposta_quantidade,
        regra.prazo_primeira_resposta_unidade,
        regra.considerar_apenas_expediente,
        regra_calculo,
    )
    prazo_resolucao_em = calcular_data_limite(
        momento_inicio,
        regra.prazo_resolucao_quantidade,
        regra.prazo_resolucao_unidade,
        regra.considerar_apenas_expediente,
        regra_calculo,
    )

    return SlaResolvido(
        regra=regra,
        prazo_primeira_resposta_em=prazo_primeira_resposta_em,
        prazo_resolucao_em=prazo_resolucao_em,
    )
