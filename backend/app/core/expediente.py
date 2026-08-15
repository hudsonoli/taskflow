"""Regra de expediente — agora aplicada no servidor.

## Por que este módulo existe

Até a Fase 2E a regra vivia só em `frontend/src/lib/regra-expediente-mock.ts` e era
verificada em `DemandasKanban.tsx`. O próprio `escopo-operacional.ts` avisava que isso *"não
é segurança"*: qualquer `curl` iniciava uma tarefa fora do horário. Com Demanda persistida de
verdade, uma regra que só existe na interface é decorativa.

## Estado transitório da configuração

`RegraExpediente` **ainda não é domínio migrado** — não há tabela `regras_expediente`. Os
valores abaixo reproduzem exatamente o mock que a operação usa hoje, e ficam aqui como
constante até o domínio ganhar tabela própria.

Isso é deliberado e tem custo conhecido: **a regra não é editável pela interface enquanto
estiver aqui**. A alternativa seria criar a tabela agora, o que arrastaria um domínio inteiro
para dentro da Fase 2E sem mandato.

A troca depois é barata porque a assinatura já recebe a regra como argumento: quando existir
tabela, muda quem produz `REGRA_PADRAO`, não quem a consome.
"""

from dataclasses import dataclass
from datetime import datetime

from app.core.relogio import agora_local


@dataclass(frozen=True)
class RegraExpediente:
    ativo: bool
    manha_inicio: str
    manha_fim: str
    tarde_inicio: str
    tarde_fim: str
    # Minutos antes de `tarde_inicio` em que a retomada já é permitida.
    tolerancia_retomada_minutos: int


# Espelha `regraExpedienteMock` do frontend. Ao migrar RegraExpediente, isto vira leitura de
# tabela e a constante some.
REGRA_PADRAO = RegraExpediente(
    ativo=True,
    manha_inicio="09:00",
    manha_fim="12:00",
    tarde_inicio="14:00",
    tarde_fim="19:00",
    tolerancia_retomada_minutos=30,
)


def _para_minutos(hora_minuto: str) -> int:
    horas, minutos = (int(parte) for parte in hora_minuto.split(":"))
    return horas * 60 + minutos


def esta_dentro_expediente(
    agora: datetime | None = None, regra: RegraExpediente = REGRA_PADRAO
) -> bool:
    """Mesma lógica de `isDentroExpediente` no frontend, incluindo a tolerância de retomada.

    `agora` sem valor usa o **fuso da aplicação**, não UTC: expediente é decisão de
    calendário local, e às 22h em São Paulo já é o dia seguinte em UTC.
    """
    if not regra.ativo:
        return True

    momento = agora or agora_local()
    minutos = momento.hour * 60 + momento.minute

    dentro_manha = _para_minutos(regra.manha_inicio) <= minutos < _para_minutos(regra.manha_fim)
    inicio_tarde = _para_minutos(regra.tarde_inicio) - regra.tolerancia_retomada_minutos
    dentro_tarde = inicio_tarde <= minutos < _para_minutos(regra.tarde_fim)

    return dentro_manha or dentro_tarde
