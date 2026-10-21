"""Capacidade INDIVIDUAL (11B.2D-A) — jornada semanal opcional + ausências por data. FUNÇÕES PURAS: sem SQLAlchemy, sem relógio, sem I/O.

## Hierarquia (de quem manda para quem é mandado)
1. `RegraExpediente` da EMPRESA: continua a autoridade global (fuso, ativo/desligado, dias especiais, `percentual_capacidade_alocavel`). Desligada → `capacidadeIndisponivel`, e nenhuma jornada
   individual a reativa (quem chama não chega aqui).
2. Jornada individual OPCIONAL: se existe, SUBSTITUI a semana recorrente da empresa inteira. Dia sem período = 0 minutos — não há fallback dia a dia.
3. Ausências (DATE, dia inteiro): zeram a capacidade do dia. Sobreposição nunca desconta duas vezes (o dia é um conjunto de datas).
4. Dias especiais da empresa continuam valendo: feriado/recesso fecham para todos; `trabalho_excepcional` usa os períodos do dia especial — para quem tem jornada individual, a INTERSEÇÃO com o
   que a jornada tem naquele dia da semana (a jornada é o limite da pessoa: o dia especial nunca a expande).
5. O percentual alocável da empresa é aplicado por último, no total (ver `carga_semanal.aplicar_percentual`).

## Precedência diária (`periodos_do_usuario_no_dia`)
ausente → 0 · dia especial fechado → 0 · dia especial `trabalho_excepcional` → períodos do especial (sem jornada) ou interseção (com jornada) · dia normal → jornada, ou semana da empresa.
Sem jornada e sem ausência o resultado é EXATAMENTE `periodos_do_dia(regra, dia)` — o comportamento anterior à 11B.2D-A.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date

from app.core.expediente import (
    TIPO_TRABALHO_EXCEPCIONAL,
    Periodo,
    RegraExpediente,
    periodos_do_dia,
    resolver_dia_especial,
)

ORIGEM_EMPRESA = "empresa"
ORIGEM_INDIVIDUAL = "individual"


@dataclass(frozen=True)
class JornadaIndividual:
    """Semana recorrente PRÓPRIA da pessoa. `dias`: 0 (segunda) .. 6 (domingo) → períodos ("HH:MM", "HH:MM"). Dia ausente do mapa = FECHADO (nunca cai no expediente da empresa)."""

    dias: Mapping[int, tuple[Periodo, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfiguracaoCapacidade:
    """O que a empresa não sabe sobre UMA pessoa: jornada própria (ou `None` = usa o expediente da empresa) e as datas em que está ausente (dia inteiro)."""

    jornada: JornadaIndividual | None = None
    dias_ausentes: frozenset[date] = frozenset()

    @property
    def origem(self) -> str:
        return ORIGEM_INDIVIDUAL if self.jornada is not None else ORIGEM_EMPRESA


SEM_CONFIGURACAO = ConfiguracaoCapacidade()


def _minutos(hora_minuto: str) -> int:
    horas, minutos = (int(parte) for parte in hora_minuto.split(":")[:2])
    return horas * 60 + minutos


def _texto(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def unir_periodos(periodos: Iterable[Periodo]) -> tuple[Periodo, ...]:
    """Ordena e funde períodos que se sobrepõem ou apenas se tocam: o resultado nunca conta o mesmo minuto duas vezes."""
    faixas = sorted((_minutos(inicio), _minutos(fim)) for inicio, fim in periodos)
    unidas: list[list[int]] = []
    for inicio, fim in faixas:
        if fim <= inicio:
            continue
        if unidas and inicio <= unidas[-1][1]:
            unidas[-1][1] = max(unidas[-1][1], fim)
        else:
            unidas.append([inicio, fim])
    return tuple((_texto(inicio), _texto(fim)) for inicio, fim in unidas)


def intersecao_periodos(a: Iterable[Periodo], b: Iterable[Periodo]) -> tuple[Periodo, ...]:
    """Interseção de duas listas de períodos (cada uma pode ter vários). Ex.: [09–12, 13–17] ∩ [10–14] = [10–12, 13–14]. Sem minutos duplicados, ordenada."""
    esquerda = [(_minutos(i), _minutos(f)) for i, f in unir_periodos(a)]
    direita = [(_minutos(i), _minutos(f)) for i, f in unir_periodos(b)]
    comuns: list[Periodo] = []
    for inicio_a, fim_a in esquerda:
        for inicio_b, fim_b in direita:
            inicio, fim = max(inicio_a, inicio_b), min(fim_a, fim_b)
            if inicio < fim:
                comuns.append((_texto(inicio), _texto(fim)))
    return unir_periodos(comuns)


def periodos_do_usuario_no_dia(regra: RegraExpediente, dia: date, configuracao: ConfiguracaoCapacidade = SEM_CONFIGURACAO) -> tuple[Periodo, ...]:
    """Períodos NOMINAIS de trabalho da PESSOA no dia (0 = sem capacidade). Pressupõe a regra da empresa ATIVA — com ela desligada não existe capacidade, e quem decide isso é quem chama."""
    if dia in configuracao.dias_ausentes:
        return ()
    jornada = configuracao.jornada
    if jornada is None:
        return periodos_do_dia(regra, dia)
    propria = tuple(jornada.dias.get(dia.weekday(), ()))
    especial = resolver_dia_especial(regra, dia)
    if especial is None:
        return unir_periodos(propria)
    if especial.tipo == TIPO_TRABALHO_EXCEPCIONAL:
        return intersecao_periodos(propria, especial.periodos)
    return ()  # feriado / recesso fecham para todos


def minutos_do_usuario_no_dia(regra: RegraExpediente, dia: date, configuracao: ConfiguracaoCapacidade = SEM_CONFIGURACAO) -> int:
    return sum(_minutos(fim) - _minutos(inicio) for inicio, fim in periodos_do_usuario_no_dia(regra, dia, configuracao))


def dias_ausentes_da_semana(intervalos: Iterable[tuple[date, date]], dias: Iterable[date]) -> frozenset[date]:
    """Datas de `dias` cobertas por pelo menos uma ausência (intervalos inclusivos). Duas ausências no mesmo dia contam UMA vez: o resultado é um conjunto."""
    alvo = list(dias)
    return frozenset(dia for dia in alvo if any(inicio <= dia <= fim for inicio, fim in intervalos))
