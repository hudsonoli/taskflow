"""Carga semanal (11B.2B-B) — PRIMITIVAS PURAS: calendário nominal, capacidade por usuário, divisão inteira e distribuição de uma janela planejada por semana.

Sem SQLAlchemy e sem relógio: tudo recebe os dados prontos. O que entra aqui NUNCA lê `sessoes_trabalho` (tempo pessoal) nem `demanda_status_intervalos` (tempo operacional): capacidade vem do expediente da
empresa e carga vem da estimativa + janela planejada da etapa.

## Capacidade (ponto de extensão)
`obter_capacidade_usuario(usuario, periodo, ...)` é o ÚNICO lugar que decide quantos minutos uma pessoa pode receber por dia. Na v1 todos os usuários elegíveis usam a `RegraExpediente` da empresa
(períodos do dia + dias especiais) e o `percentual_capacidade_alocavel`. O argumento `usuario` existe para que jornada individual e ausências/férias possam entrar no futuro SEM mudar quem a chama;
hoje ele não é lido. Não há hierarquia de classes nem tabela de apoio.

## Inteiros e conservação
Toda divisão de minutos é inteira, por MAIOR RESTO com desempate pela posição (determinístico): a soma das partes é SEMPRE o total — nenhum minuto some por arredondamento.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.core.expediente import RegraExpediente, periodos_do_dia

DIAS_DA_SEMANA = 7

ALOCACAO_ALOCADA = "alocada"
ALOCACAO_JANELA_VENCIDA = "janela_vencida"
ALOCACAO_SEM_DIA_UTIL = "sem_dia_util"


def segunda_da_semana(dia: date) -> date:
    """Segunda-feira da semana de `dia` (`weekday()`: 0 = segunda — a mesma convenção do expediente)."""
    return dia - timedelta(days=dia.weekday())


def dias_da_semana(segunda: date) -> list[date]:
    return [segunda + timedelta(days=i) for i in range(DIAS_DA_SEMANA)]


def _para_minutos(hora_minuto: str) -> int:
    horas, minutos = (int(parte) for parte in hora_minuto.split(":")[:2])
    return horas * 60 + minutos


def minutos_nominais_do_dia(regra: RegraExpediente, dia: date) -> int:
    """Soma dos períodos NOMINAIS do dia (já com dia especial: feriado/recesso = 0; trabalho excepcional = períodos próprios). Não usa antecedência de acesso, bloqueio nem pausa automática."""
    return sum(_para_minutos(fim) - _para_minutos(inicio) for inicio, fim in periodos_do_dia(regra, dia))


@dataclass(frozen=True)
class CapacidadeUsuario:
    """Capacidade de UMA pessoa em um período: minutos nominais por dia, total nominal e total alocável (nominal × percentual)."""

    minutos_por_dia: dict[date, int]
    nominal_min: int
    alocavel_min: int


def aplicar_percentual(nominal_min: int, percentual: int) -> int:
    """`round(nominal × percentual / 100)` com meio para cima, em inteiros (determinístico, sem float)."""
    return (nominal_min * percentual + 50) // 100


def obter_capacidade_usuario(
    usuario: Any,
    periodo: Sequence[date],
    *,
    regra: RegraExpediente,
    percentual_alocavel: int,
) -> CapacidadeUsuario:
    """Capacidade do `usuario` nos dias de `periodo`.

    v1: independe do usuário — todos usam o expediente da empresa. FUTURO: override individual de jornada e ausências/férias entram AQUI, olhando `usuario` e `periodo`, sem alterar os chamadores.
    """
    minutos = {dia: minutos_nominais_do_dia(regra, dia) for dia in periodo}
    nominal = sum(minutos.values())
    return CapacidadeUsuario(minutos_por_dia=minutos, nominal_min=nominal, alocavel_min=aplicar_percentual(nominal, percentual_alocavel))


def distribuir_por_pesos(total: int, pesos: Sequence[int]) -> list[int]:
    """Reparte `total` (inteiro ≥ 0) proporcionalmente a `pesos` (inteiros ≥ 0) pelo MAIOR RESTO. A soma do resultado é exatamente `total`. Empate de resto: menor índice primeiro.
    Soma de pesos = 0 → tudo zero (quem chama decide o que isso significa; aqui nunca se inventa destino)."""
    soma = sum(pesos)
    if total < 0 or any(p < 0 for p in pesos):
        raise ValueError("total e pesos devem ser não negativos")
    if soma == 0 or not pesos:
        return [0] * len(pesos)
    base = [total * p // soma for p in pesos]
    restos = [total * p % soma for p in pesos]
    faltam = total - sum(base)
    ordem = sorted(range(len(pesos)), key=lambda i: (-restos[i], i))
    for indice in ordem[:faltam]:
        base[indice] += 1
    return base


def dividir_igual(total: int, quantidade: int) -> list[int]:
    """Divisão igual em minutos inteiros: 241 entre 2 → [121, 120]. O resto vai para as primeiras posições (a ordem estável é de quem chama: ids ordenados)."""
    if quantidade <= 0:
        return []
    return distribuir_por_pesos(total, [1] * quantidade)


@dataclass(frozen=True)
class AlocacaoJanela:
    """Resultado de distribuir UMA janela completa. `estado`: alocada | janela_vencida | sem_dia_util. `por_semana`: segunda-feira → minutos (vazio fora de `alocada` ou sem restante conhecido)."""

    estado: str
    por_semana: dict[date, int] = field(default_factory=dict)
    peso_total: int = 0


def alocar_janela(
    restante_min: int | None,
    inicio: date,
    fim: date,
    hoje: date,
    minutos_do_dia: Callable[[date], int],
) -> AlocacaoJanela:
    """Distribui `restante_min` pelos dias RESTANTES da janela (de `max(inicio, hoje)` até `fim`), proporcional aos minutos nominais de cada dia, e agrega por semana.

    - `fim < hoje` → `janela_vencida`: NADA é distribuído e nada é movido para a semana atual (precisa replanejar).
    - soma dos minutos nominais dos dias restantes = 0 (ex.: sábado→domingo num expediente seg–sex) → `sem_dia_util`: nada é distribuído nem movido; a janela continua válida.
    - Caso contrário `alocada`. Conserva o restante: Σ semanas == `restante_min` (maior resto entre as semanas). `restante_min=None` (sem estimativa) classifica sem distribuir.
    """
    if fim < hoje:
        return AlocacaoJanela(ALOCACAO_JANELA_VENCIDA)
    primeiro = max(inicio, hoje)
    semanas: dict[date, int] = {}
    dia = primeiro
    while dia <= fim:
        peso = minutos_do_dia(dia)
        semana = segunda_da_semana(dia)
        semanas[semana] = semanas.get(semana, 0) + peso
        dia += timedelta(days=1)
    peso_total = sum(semanas.values())
    if peso_total == 0:
        return AlocacaoJanela(ALOCACAO_SEM_DIA_UTIL)
    if restante_min is None:
        return AlocacaoJanela(ALOCACAO_ALOCADA, {}, peso_total)
    chaves = sorted(semanas)
    partes = distribuir_por_pesos(restante_min, [semanas[c] for c in chaves])
    return AlocacaoJanela(ALOCACAO_ALOCADA, {semana: minutos for semana, minutos in zip(chaves, partes)}, peso_total)
