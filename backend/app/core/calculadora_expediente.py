"""Cálculo puro de data-limite (Fase 2G.6C) — sem SQLAlchemy, sem Session, sem I/O.

`calcular_data_limite` soma uma quantidade (minutos/horas/dias corridos/dias úteis) a um
instante inicial, respeitando (ou não, conforme a unidade e a flag) as janelas de expediente
de `app.core.expediente.RegraExpediente` — o DTO puro já resolvido pelo caller (tipicamente via
`RegraExpedienteService.get_regra_calculo`, nunca duplicado aqui).

Genérica de propósito: não existe "calcular primeira resposta" e "calcular resolução"
separados — a Fase 2G.6D chama esta mesma função duas vezes, uma por compromisso.

## Unidades

- `dias_corridos`: `inicio + N dias de calendário`. Nunca olha expediente — nem janelas, nem
  `considerar_apenas_expediente`, nem `RegraExpediente.ativo`.
- `dias_uteis`: avança N dias cujo `RegraExpedienteDia.ativo` seja `True` (granularidade de
  dia, não de hora — preserva o horário local do `inicio`, não percorre janelas internas nem
  almoço). Sem feriados (fora da V1). Se `RegraExpediente.ativo == False` (gate mestre
  desabilitado), cai para o mesmo comportamento de `dias_corridos` — ver próximo item.
- `minutos`/`horas`: se `considerar_apenas_expediente == False` OU `RegraExpediente.ativo ==
  False`, soma tempo corrido normalmente (sem pular almoço/noite/fim de semana). Só quando
  AMBOS — flag pedindo expediente E regra mestre habilitada — o relógio avança apenas dentro
  das janelas ativas (ver `_avancar_dentro_expediente`).

`RegraExpediente.ativo == False` como "calendário corrido" é a mesma semântica já aprovada na
Fase 2G.3 para `esta_dentro_expediente` (gate desabilitado libera qualquer hora) — aqui
significa não pausar o relógio por janela/dia nenhum, incluindo pra `dias_uteis`.

## Limites de janela: início inclusivo, fim exclusivo

`09:00–12:00` inclui `09:00:00` e exclui `12:00:00` — evita contar o instante de fronteira
duas vezes quando janelas são adjacentes por hipótese (ex.: manhã terminando exatamente onde a
tarde começa). Um `inicio` recebido exatamente no fim de uma janela (ex.: `19:00:00` no fim do
expediente do dia) é tratado como FORA, avançando pro próximo instante válido.

## Timezone

Todo cálculo acontece no fuso da aplicação (`app.core.relogio.fuso_aplicacao`) — `inicio` é
normalizado via `astimezone` logo na entrada (precisa já ser aware; `naive` é erro), e todo
instante construído internamente (fins de janela, próximos inícios) usa o mesmo `tzinfo`. Não
há tratamento sofisticado de DST — não removemos timezone em nenhum passo, e o resultado é
sempre aware.

## Proteção contra loop

Antes de qualquer busca "avançar dia a dia", valida-se que existe pelo menos um dia ativo
(`dias_uteis`) ou pelo menos uma janela utilizável (`minutos`/`horas` com expediente) na
`RegraExpediente` recebida — configuração sem nenhum dia/janela levanta erro claro, nunca
entra em loop. Além disso, os laços de avanço têm um teto defensivo de iterações
(`_MAX_ITERACOES`) como segunda camada de proteção (ex.: janela de duração zero, um bug de
dado que a validação acima não cobre) — nunca deve ser atingido em uso legítimo.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.core.expediente import JanelaDia, RegraExpediente
from app.core.relogio import fuso_aplicacao

UNIDADES_VALIDAS = {"minutos", "horas", "dias_corridos", "dias_uteis"}

# ~10 anos de dias corridos — generoso o bastante pra nunca truncar um SLA longo legítimo,
# baixo o bastante pra nunca deixar um bug de configuração rodar indefinidamente.
_MAX_ITERACOES = 3660


class SlaCalculoInvalidoError(ValueError):
    """Entrada inválida para `calcular_data_limite` — quantidade <= 0, `inicio` naive, ou
    unidade fora de `UNIDADES_VALIDAS`. As CHECK constraints de `SlaRegra` já impedem isso vindo
    do banco; esta validação existe porque a função é pura e pode ser chamada com valores
    construídos à mão (testes, futura integração da Fase 2G.6D)."""


class SlaExpedienteSemJanelaUtilError(ValueError):
    """`RegraExpediente` ativa mas sem nenhum dia (`dias_uteis`) ou janela (`minutos`/`horas`
    com expediente) utilizável — calcular avançaria indefinidamente sem nunca achar um
    instante válido. Ver seção "Proteção contra loop" no docstring do módulo."""


def calcular_data_limite(
    inicio: datetime,
    quantidade: int,
    unidade: str,
    considerar_apenas_expediente: bool,
    regra_expediente: RegraExpediente,
) -> datetime:
    if quantidade <= 0:
        raise SlaCalculoInvalidoError(f"quantidade deve ser > 0, recebido {quantidade!r}")
    if unidade not in UNIDADES_VALIDAS:
        raise SlaCalculoInvalidoError(f"unidade desconhecida: {unidade!r}")
    if inicio.tzinfo is None or inicio.utcoffset() is None:
        raise SlaCalculoInvalidoError("inicio deve ser timezone-aware")

    inicio_local = inicio.astimezone(fuso_aplicacao())

    if unidade == "dias_corridos":
        return inicio_local + timedelta(days=quantidade)

    if unidade == "dias_uteis":
        if not regra_expediente.ativo:
            return inicio_local + timedelta(days=quantidade)
        _validar_existe_dia_ativo(regra_expediente)
        return _avancar_dias_uteis(inicio_local, quantidade, regra_expediente)

    minutos_totais = quantidade if unidade == "minutos" else quantidade * 60

    if not considerar_apenas_expediente or not regra_expediente.ativo:
        return inicio_local + timedelta(minutes=minutos_totais)

    _validar_existe_janela_utilizavel(regra_expediente)
    return _avancar_dentro_expediente(inicio_local, minutos_totais, regra_expediente)


# ----------------------------------------------------------------------------------------
# dias_uteis
# ----------------------------------------------------------------------------------------


def _validar_existe_dia_ativo(regra: RegraExpediente) -> None:
    if not any(dia.ativo for dia in regra.dias.values()):
        raise SlaExpedienteSemJanelaUtilError(
            "RegraExpediente não possui nenhum dia da semana ativo — cálculo de dias úteis "
            "nunca encontraria um dia válido para avançar"
        )


def _avancar_dias_uteis(inicio: datetime, quantidade: int, regra: RegraExpediente) -> datetime:
    cursor = inicio
    restante = quantidade
    for _ in range(_MAX_ITERACOES):
        if restante <= 0:
            return cursor
        cursor = cursor + timedelta(days=1)
        dia = regra.dias.get(cursor.weekday())
        if dia is not None and dia.ativo:
            restante -= 1
    raise SlaExpedienteSemJanelaUtilError(
        "Avanço de dias úteis excedeu o limite defensivo de iterações — verifique a configuração"
    )


# ----------------------------------------------------------------------------------------
# minutos/horas com expediente
# ----------------------------------------------------------------------------------------


def _hhmm_para_minutos(valor: str) -> int:
    horas, minutos = (int(parte) for parte in valor.split(":"))
    return horas * 60 + minutos


def _minuto_do_dia(momento: datetime) -> int:
    return momento.hour * 60 + momento.minute


def _janelas_do_dia(dia: JanelaDia | None) -> list[tuple[int, int]]:
    if dia is None or not dia.ativo:
        return []
    janelas: list[tuple[int, int]] = []
    if dia.manha_inicio is not None and dia.manha_fim is not None:
        janelas.append((_hhmm_para_minutos(dia.manha_inicio), _hhmm_para_minutos(dia.manha_fim)))
    if dia.tarde_inicio is not None and dia.tarde_fim is not None:
        janelas.append((_hhmm_para_minutos(dia.tarde_inicio), _hhmm_para_minutos(dia.tarde_fim)))
    return sorted(janelas)


def _combinar(dia: date, minuto_do_dia: int, tzinfo) -> datetime:
    horas, minutos = divmod(minuto_do_dia, 60)
    return datetime(dia.year, dia.month, dia.day, horas, minutos, tzinfo=tzinfo)


def _validar_existe_janela_utilizavel(regra: RegraExpediente) -> None:
    if not any(_janelas_do_dia(dia) for dia in regra.dias.values()):
        raise SlaExpedienteSemJanelaUtilError(
            "RegraExpediente não possui nenhuma janela de expediente (manhã/tarde) utilizável — "
            "cálculo com considerar_apenas_expediente=True nunca encontraria um instante válido"
        )


def _instante_dentro_de_janela(momento: datetime, regra: RegraExpediente) -> bool:
    minuto = _minuto_do_dia(momento)
    return any(inicio_j <= minuto < fim_j for inicio_j, fim_j in _janelas_do_dia(regra.dias.get(momento.weekday())))


def _proximo_instante_valido(momento: datetime, regra: RegraExpediente) -> datetime:
    """Menor instante >= `momento` que esteja dentro de uma janela ativa. Se `momento` já está
    dentro, retorna `momento` sem alterar (preserva segundos/microssegundos originais); caso
    contrário aterrissa exatamente no início (`HH:MM:00`) da próxima janela disponível, podendo
    avançar dias — inclusive pulando dias inteiros inativos (fim de semana no padrão)."""
    if _instante_dentro_de_janela(momento, regra):
        return momento

    data_cursor = momento.date()
    limite_inferior = _minuto_do_dia(momento)
    for _ in range(_MAX_ITERACOES):
        candidatos = sorted(
            inicio_j
            for inicio_j, _fim_j in _janelas_do_dia(regra.dias.get(data_cursor.weekday()))
            if inicio_j >= limite_inferior
        )
        if candidatos:
            return _combinar(data_cursor, candidatos[0], momento.tzinfo)
        data_cursor += timedelta(days=1)
        limite_inferior = 0

    raise SlaExpedienteSemJanelaUtilError(
        "Busca pelo próximo instante de expediente válido excedeu o limite defensivo de iterações"
    )


def _fim_janela_atual(momento: datetime, regra: RegraExpediente) -> datetime:
    minuto = _minuto_do_dia(momento)
    for inicio_j, fim_j in _janelas_do_dia(regra.dias.get(momento.weekday())):
        if inicio_j <= minuto < fim_j:
            return _combinar(momento.date(), fim_j, momento.tzinfo)
    raise AssertionError("_fim_janela_atual chamado com momento fora de qualquer janela — invariante violada")


def _avancar_dentro_expediente(inicio: datetime, minutos: float, regra: RegraExpediente) -> datetime:
    cursor = _proximo_instante_valido(inicio, regra)
    restante = minutos
    for _ in range(_MAX_ITERACOES):
        if restante <= 0:
            return cursor
        fim_janela = _fim_janela_atual(cursor, regra)
        disponivel = (fim_janela - cursor).total_seconds() / 60
        if restante <= disponivel:
            return cursor + timedelta(minutes=restante)
        restante -= disponivel
        cursor = _proximo_instante_valido(fim_janela, regra)

    raise SlaExpedienteSemJanelaUtilError(
        "Avanço dentro do expediente excedeu o limite defensivo de iterações — verifique a "
        "configuração (ex.: janela de duração zero)"
    )
