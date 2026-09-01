"""Resolução determinística de Regra de SLA (Fase 2G.6C).

Decide, dados os critérios de uma Demanda (prioridade/departamento/cliente), qual `SlaRegra`
ativa se aplica. Não calcula nenhum prazo — isso é `app/core/calculadora_expediente.py` — e
não integra com Demanda — isso é a Fase 2G.6D. Ver relatório da Fase 2G.6A e o kickoff da
2G.6C para as decisões abaixo, já aprovadas antes desta implementação.

## Precedência (determinística, nunca depende da ordem do banco)

1. `prioridade_regra` ASC — menor valor vence;
2. empate → especificidade DESC — mais critérios preenchidos vence;
3. empate total → `created_at` ASC — regra mais antiga vence;
4. empate total → `id` ASC — desempate final, sempre determinístico.

Especificidade é a contagem de quantos dentre {`prioridade_alvo`, `departamento_id`,
`cliente_id`} estão preenchidos (cada um preenchido soma 1; `NULL` não soma nada). A regra
"default" da Empresa (os três `NULL`) tem especificidade 0 — só vence quando nenhuma outra
regra ativa combina, e mesmo assim só se `prioridade_regra` favorecer (nada impede uma Empresa
configurar o default com `prioridade_regra` alto, perdendo de outra regra também genérica).

## Sem regra combinando

Retorna `None`. Nunca cria uma regra default automaticamente, nunca lança erro — o que a
Demanda faz sem SLA resolvido é decisão da Fase 2G.6D, não daqui.

## Lifecycle

Só `status == ativo` participa (ver `SlaResolverRepository`). `inativo`/`arquivado` nunca são
candidatos, mesmo que combinem por critério.

## Tenant

`empresa_id` é parâmetro obrigatório, sempre vindo do caller (nunca inferido) — a query
candidata nunca busca fora da Empresa informada.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sla_regra import SlaRegra
from app.repositories.sla_resolver_repository import SlaResolverRepository


def _especificidade(regra: SlaRegra) -> int:
    return (
        (1 if regra.prioridade_alvo is not None else 0)
        + (1 if regra.departamento_id is not None else 0)
        + (1 if regra.cliente_id is not None else 0)
    )


def _chave_precedencia(regra: SlaRegra) -> tuple[int, int, object, str]:
    return (regra.prioridade_regra, -_especificidade(regra), regra.created_at, regra.id)


def resolver_sla(
    db: Session,
    *,
    empresa_id: str,
    prioridade: str | None,
    departamento_id: str | None = None,
    cliente_id: str | None = None,
) -> SlaRegra | None:
    candidatas = SlaResolverRepository().list_candidatas(
        db,
        empresa_id=empresa_id,
        prioridade=prioridade,
        departamento_id=departamento_id,
        cliente_id=cliente_id,
    )
    if not candidatas:
        return None
    return min(candidatas, key=_chave_precedencia)
