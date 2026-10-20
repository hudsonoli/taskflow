"""Carga semanal (11B.2B-B) — CÁLCULO PURO sobre dados já carregados (sem SQL, sem relógio, sem I/O).

Entradas: etapas abertas das Demandas operacionais (estimativa + janela planejada + responsáveis), pessoas ELEGÍVEIS, expediente da empresa, fator alocável, "hoje" e a segunda-feira da semana.
Saída: a ALOCAÇÃO COMPLETA da semana (por etapa, por pessoa, por departamento, pools, não planejado e pendências). FILTROS são aplicados DEPOIS, sobre este resultado — nunca recalculam a divisão.

## Regras (ver docs/carga-semanal.md)
- **Restante**: etapa aberta = `esforco_estimado_minutos`; sem estimativa = desconhecido (NÃO vira zero: conta em `sem_estimativa`). Sessões e intervalos operacionais nunca reduzem o restante.
- **Janela**: só início+fim ≥ início alocam. Sem janela → `sem_janela`; só início → `janela_incompleta` (ambos fora da ocupação, mas com minutos conhecidos em `nao_planejado`).
  Janela vencida e janela só em dias sem capacidade viram PENDÊNCIAS (nada é movido de semana). Ver `alocar_janela`.
- **Responsáveis**: usuários elegíveis da etapa recebem a carga em divisão igual (ordem estável por id; maior resto). Sem usuário elegível: departamentos da etapa viram POOLS (divisão igual entre eles);
  sem departamento: POOL_SEM_DEPARTAMENTO. A carga NUNCA desaparece. Departamento com usuários NÃO recebe carga extra.
- **Divisão entre responsáveis e semanas**: a parcela GLOBAL de cada responsável/pool vem da divisão igual da estimativa (241 → 121 e 120) e a janela é rateada em matriz responsável × semana
  (`ratear_por_linhas_e_colunas`): Σ da linha = parcela global do responsável e Σ da coluna = planejado da etapa na semana, exatamente. Sem viés acumulado de arredondamento entre semanas.
- **Expediente desligado/ausente**: sem denominador confiável → `capacidade_indisponivel`; nenhuma distribuição semanal é feita (planejado e saldo ficam nulos), mas não planejado, sem estimativa e janela vencida
  (que dependem só de datas) continuam informados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.core.carga_semanal import (
    ALOCACAO_ALOCADA,
    ALOCACAO_JANELA_VENCIDA,
    ALOCACAO_SEM_DIA_UTIL,
    alocar_janela,
    dias_da_semana,
    dividir_igual,
    minutos_nominais_do_dia,
    obter_capacidade_usuario,
    ratear_por_linhas_e_colunas,
)
from app.core.expediente import RegraExpediente

MOTIVO_SEM_JANELA = "sem_janela"
MOTIVO_JANELA_INCOMPLETA = "janela_incompleta"

ORIGEM_RESPONSAVEL = "responsavel"
ORIGEM_POOL_DEPARTAMENTO = "pool_departamento"
ORIGEM_POOL_SEM_DEPARTAMENTO = "pool_sem_departamento"

CAPACIDADE_EXPEDIENTE_DESLIGADO = "expediente_desligado"


@dataclass(frozen=True)
class Ref:
    id: str
    nome: str


@dataclass(frozen=True)
class EtapaEntrada:
    etapa_id: str
    demanda_id: str
    etapa_nome: str
    etapa_tipo: str
    ordem: int
    estimativa_min: int | None
    planejado_inicio: date | None
    planejado_fim: date | None
    usuario_ids: tuple[str, ...]
    departamento_ids: tuple[str, ...]
    demanda_identificador: str = ""
    demanda_nome: str = ""
    demanda_status: str = ""
    cliente: Ref | None = None
    projeto: Ref | None = None


@dataclass(frozen=True)
class PessoaElegivel:
    usuario_id: str
    nome: str
    departamento_id: str | None


# Alvo de carga: ("usuario", id) | ("pool_departamento", id) | ("pool_sem_departamento", "")
Alvo = tuple[str, str]


@dataclass
class EtapaCalculada:
    entrada: EtapaEntrada
    estado_planejamento: str  # nao_planejado | incompleto | planejado
    motivo_nao_planejado: str | None  # sem_janela | janela_incompleta
    alocacao_estado: str | None  # alocada | janela_vencida | sem_dia_util | None (nao se aplica / indeterminado)
    restante_min: int | None
    planejado_semana_min: int | None  # None quando nao ha distribuicao (sem janela completa, sem estimativa, pendencia, capacidade indisponivel)
    origem: str
    alvos: list[Alvo]
    divisao_semana: list[int]  # minutos da semana por alvo (alinhado a `alvos`); [] quando nao ha distribuicao
    divisao_estimativa: list[int]  # estimativa inteira dividida por alvo (para nao planejado/pendencias); [] sem estimativa

    @property
    def sem_estimativa(self) -> bool:
        return self.entrada.estimativa_min is None

    @property
    def pendencia(self) -> str | None:
        return self.alocacao_estado if self.alocacao_estado in (ALOCACAO_JANELA_VENCIDA, ALOCACAO_SEM_DIA_UTIL) else None


@dataclass
class Agregado:
    planejado_min: int = 0
    nao_planejado_min: int = 0
    pendencia_min: int = 0
    sem_estimativa: set[str] = field(default_factory=set)
    etapas: dict[str, EtapaCalculada] = field(default_factory=dict)


@dataclass
class ResultadoCarga:
    semana_inicio: date
    semana_fim: date
    recorte_hoje: bool
    dias: list[tuple[date, int | None, bool]]  # (data, minutos nominais | None se indisponivel, considerado)
    capacidade_indisponivel: str | None
    percentual: int
    capacidade_nominal_pessoa_min: int | None
    capacidade_alocavel_pessoa_min: int | None
    etapas: list[EtapaCalculada]
    pessoas: dict[str, Agregado]
    pessoas_info: dict[str, PessoaElegivel]
    pools_departamento: dict[str, Agregado]
    pool_sem_departamento: Agregado


def _alvos_da_etapa(entrada: EtapaEntrada, elegiveis: dict[str, PessoaElegivel]) -> tuple[list[Alvo], str]:
    usuarios = sorted({u for u in entrada.usuario_ids if u in elegiveis})
    if usuarios:
        return [("usuario", u) for u in usuarios], ORIGEM_RESPONSAVEL
    departamentos = sorted(set(entrada.departamento_ids))
    if departamentos:
        return [("pool_departamento", d) for d in departamentos], ORIGEM_POOL_DEPARTAMENTO
    return [("pool_sem_departamento", "")], ORIGEM_POOL_SEM_DEPARTAMENTO


def _parte_da_semana(estimativa: int, quantidade_alvos: int, por_semana: dict[date, int], semana_inicio: date) -> list[int]:
    """Parte de CADA alvo na semana consultada, sem viés acumulado entre semanas.

    1. a estimativa inteira é dividida entre os alvos (parcela GLOBAL: 241 entre 2 → 121 e 120);
    2. a janela inteira é rateada em matriz alvo × semana: cada linha soma a parcela global do alvo e cada coluna soma o planejado da semana da etapa;
    3. devolve a coluna da semana consultada.
    A matriz usa SEMPRE todas as semanas da janela, então o resultado de uma semana é o mesmo qualquer que seja a semana pedida. Um único alvo não precisa de rateio.
    """
    semana = por_semana.get(semana_inicio, 0)
    if quantidade_alvos == 1:
        return [semana]
    if semana_inicio not in por_semana:
        return [0] * quantidade_alvos
    semanas = sorted(por_semana)
    matriz = ratear_por_linhas_e_colunas(dividir_igual(estimativa, quantidade_alvos), [por_semana[s] for s in semanas])
    coluna = semanas.index(semana_inicio)
    return [linha[coluna] for linha in matriz]


def calcular_carga(
    *,
    etapas: list[EtapaEntrada],
    pessoas: list[PessoaElegivel],
    regra: RegraExpediente | None,
    percentual_alocavel: int,
    hoje: date,
    semana_inicio: date,
) -> ResultadoCarga:
    semana_fim = semana_inicio + timedelta(days=6)
    recorte_hoje = semana_inicio <= hoje <= semana_fim
    calendario_ok = regra is not None and regra.ativo
    capacidade_indisponivel = None if calendario_ok else CAPACIDADE_EXPEDIENTE_DESLIGADO

    cache_minutos: dict[date, int] = {}

    def minutos_do_dia(dia: date) -> int:
        if dia not in cache_minutos:
            cache_minutos[dia] = minutos_nominais_do_dia(regra, dia) if calendario_ok and regra is not None else 0
        return cache_minutos[dia]

    todos_os_dias = dias_da_semana(semana_inicio)
    dias = [(d, (minutos_do_dia(d) if calendario_ok else None), (d >= hoje if recorte_hoje else True)) for d in todos_os_dias]
    considerados = [d for d, _m, ok in dias if ok]

    nominal_pessoa: int | None = None
    alocavel_pessoa: int | None = None
    if calendario_ok and regra is not None:
        capacidade = obter_capacidade_usuario(None, considerados, regra=regra, percentual_alocavel=percentual_alocavel)
        nominal_pessoa, alocavel_pessoa = capacidade.nominal_min, capacidade.alocavel_min

    elegiveis = {p.usuario_id: p for p in sorted(pessoas, key=lambda p: p.usuario_id)}
    calculadas: list[EtapaCalculada] = []

    for entrada in etapas:
        alvos, origem = _alvos_da_etapa(entrada, elegiveis)
        estimativa = entrada.estimativa_min
        motivo = None
        alocacao_estado = None
        planejado_semana: int | None = None
        divisao_semana: list[int] = []

        if entrada.planejado_inicio is None:
            estado_plan, motivo = "nao_planejado", MOTIVO_SEM_JANELA
        elif entrada.planejado_fim is None:
            estado_plan, motivo = "incompleto", MOTIVO_JANELA_INCOMPLETA
        else:
            estado_plan = "planejado"
            if calendario_ok:
                resultado = alocar_janela(estimativa, entrada.planejado_inicio, entrada.planejado_fim, hoje, minutos_do_dia)
                alocacao_estado = resultado.estado
                if resultado.estado == ALOCACAO_ALOCADA and estimativa is not None:
                    planejado_semana = resultado.por_semana.get(semana_inicio, 0)
                    divisao_semana = _parte_da_semana(estimativa, len(alvos), resultado.por_semana, semana_inicio)
            elif entrada.planejado_fim < hoje:
                alocacao_estado = ALOCACAO_JANELA_VENCIDA  # só depende de datas; o calendário não é necessário para saber que venceu

        divisao_estimativa = dividir_igual(estimativa, len(alvos)) if estimativa is not None else []
        calculadas.append(
            EtapaCalculada(
                entrada=entrada,
                estado_planejamento=estado_plan,
                motivo_nao_planejado=motivo,
                alocacao_estado=alocacao_estado,
                restante_min=estimativa,
                planejado_semana_min=planejado_semana,
                origem=origem,
                alvos=alvos,
                divisao_semana=divisao_semana,
                divisao_estimativa=divisao_estimativa,
            )
        )

    pessoas_agregadas: dict[str, Agregado] = {p: Agregado() for p in elegiveis}
    pools: dict[str, Agregado] = {}
    pool_sem = Agregado()

    def agregado_do(alvo: Alvo) -> Agregado:
        tipo, chave = alvo
        if tipo == "usuario":
            return pessoas_agregadas[chave]
        if tipo == "pool_departamento":
            return pools.setdefault(chave, Agregado())
        return pool_sem

    for etapa in calculadas:
        for indice, alvo in enumerate(etapa.alvos):
            agregado = agregado_do(alvo)
            agregado.etapas[etapa.entrada.etapa_id] = etapa
            if etapa.sem_estimativa:
                agregado.sem_estimativa.add(etapa.entrada.etapa_id)
            if etapa.divisao_semana:
                agregado.planejado_min += etapa.divisao_semana[indice]
            if etapa.motivo_nao_planejado and etapa.divisao_estimativa:
                agregado.nao_planejado_min += etapa.divisao_estimativa[indice]
            if etapa.pendencia and etapa.divisao_estimativa:
                agregado.pendencia_min += etapa.divisao_estimativa[indice]

    return ResultadoCarga(
        semana_inicio=semana_inicio,
        semana_fim=semana_fim,
        recorte_hoje=recorte_hoje,
        dias=dias,
        capacidade_indisponivel=capacidade_indisponivel,
        percentual=percentual_alocavel,
        capacidade_nominal_pessoa_min=nominal_pessoa,
        capacidade_alocavel_pessoa_min=alocavel_pessoa,
        etapas=calculadas,
        pessoas=pessoas_agregadas,
        pessoas_info=elegiveis,
        pools_departamento=pools,
        pool_sem_departamento=pool_sem,
    )
