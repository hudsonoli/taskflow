"""Fase Expediente 1 — cálculo PURO: janela de TRABALHO × janela de ACESSO, próximos instantes, dias especiais, fuso/DST e equivalência com o modelo antigo.

Nada aqui toca banco nem relógio real: tudo recebe `agora` explícito. 2026-10-12 é uma SEGUNDA-feira (12/10 é o feriado do exemplo do produto).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.core.calculadora_expediente import calcular_data_limite
from app.core.expediente import (
    DiaEspecial,
    JanelaDia,
    RegraExpediente,
    dia_aberto,
    duracao_horas_dia,
    esta_dentro_expediente,
    esta_dentro_janela_acesso,
    esta_dentro_janela_trabalho,
    janela_de_periodos,
    janela_do_dia,
    periodos_do_dia,
    proximo_acesso,
    proximo_inicio_trabalho,
    resolver_dia_especial,
)

SP = "America/Sao_Paulo"
SEG, TER, SEX, SAB, DOM = date(2026, 10, 12), date(2026, 10, 13), date(2026, 10, 16), date(2026, 10, 17), date(2026, 10, 18)
UTIL = (("08:00", "12:00"), ("13:00", "18:00"))


def regra(por_dia=None, *, antecedencia=30, tz=SP, especiais=(), ativo=True, tolerancia=0) -> RegraExpediente:
    por_dia = {dia: UTIL for dia in range(5)} if por_dia is None else por_dia
    return RegraExpediente(
        ativo=ativo,
        tolerancia_retomada_minutos=tolerancia,
        dias={dia: janela_de_periodos(por_dia.get(dia, ())) for dia in range(7)},
        antecedencia_acesso_minutos=antecedencia,
        timezone=tz,
        dias_especiais=tuple(especiais),
    )


def em(dia: date, hora: str, segundos: int = 0) -> datetime:
    """Relógio local da empresa (naive = parede local)."""
    h, m = (int(p) for p in hora.split(":"))
    return datetime(dia.year, dia.month, dia.day, h, m, segundos)


# ── bordas do exemplo do produto ─────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("hora", "trabalho", "acesso"),
    [
        ("07:29", False, False),
        ("07:30", False, True),  # antecedência: entra, mas NÃO é trabalho
        ("07:59", False, True),
        ("08:00", True, True),
        ("11:59", True, True),
        ("12:00", False, False),  # fim exclusivo do 1º período
        ("12:29", False, False),
        ("12:30", False, True),
        ("12:59", False, True),
        ("13:00", True, True),
        ("17:59", True, True),
        ("18:00", False, False),
        ("23:59", False, False),
    ],
)
def test_bordas_da_segunda_trabalho_e_acesso(hora, trabalho, acesso) -> None:
    r = regra()
    assert esta_dentro_janela_trabalho(em(SEG, hora), regra=r) is trabalho
    assert esta_dentro_janela_acesso(em(SEG, hora), regra=r) is acesso


def test_segundos_respeitam_fim_exclusivo() -> None:
    r = regra()
    assert esta_dentro_janela_trabalho(em(SEG, "11:59", 59), regra=r) is True
    assert esta_dentro_janela_trabalho(em(SEG, "12:00", 0), regra=r) is False
    assert esta_dentro_janela_acesso(em(SEG, "07:29", 59), regra=r) is False
    assert esta_dentro_janela_acesso(em(SEG, "07:30", 0), regra=r) is True


def test_antecedencia_nao_conta_como_trabalho() -> None:
    r = regra(antecedencia=30)
    for hora in ("07:30", "07:45", "07:59", "12:30", "12:59"):
        assert esta_dentro_janela_acesso(em(SEG, hora), regra=r) is True
        assert esta_dentro_janela_trabalho(em(SEG, hora), regra=r) is False


def test_antecedencia_zero_acesso_igual_trabalho() -> None:
    r = regra(antecedencia=0)
    for hora in ("07:59", "08:00", "11:59", "12:00", "12:59", "13:00", "17:59", "18:00"):
        assert esta_dentro_janela_acesso(em(SEG, hora), regra=r) is esta_dentro_janela_trabalho(em(SEG, hora), regra=r)


@pytest.mark.parametrize("dia", [SAB, DOM])
def test_fim_de_semana_fechado_no_padrao(dia) -> None:
    r = regra()
    for hora in ("07:30", "08:00", "10:00", "13:00"):
        assert esta_dentro_janela_trabalho(em(dia, hora), regra=r) is False
        assert esta_dentro_janela_acesso(em(dia, hora), regra=r) is False


def test_sexta_igual_a_segunda_e_dia_fechado_no_meio_da_semana() -> None:
    r = regra({0: UTIL, 1: UTIL, 2: UTIL, 3: (), 4: UTIL})  # quinta fechada
    assert esta_dentro_janela_trabalho(em(SEX, "09:00"), regra=r) is True
    quinta = date(2026, 10, 15)
    assert esta_dentro_janela_trabalho(em(quinta, "09:00"), regra=r) is False
    assert esta_dentro_janela_acesso(em(quinta, "09:00"), regra=r) is False


def test_regra_desligada_libera_tudo() -> None:
    r = regra(ativo=False)
    assert esta_dentro_janela_trabalho(em(DOM, "03:00"), regra=r) is True
    assert esta_dentro_janela_acesso(em(DOM, "03:00"), regra=r) is True
    assert esta_dentro_expediente(em(DOM, "03:00"), regra=r) is True


# ── 1, 2 e 3 períodos; sábado aberto ─────────────────────────────────────────────────────────────────────────────


def test_um_periodo_no_sabado_e_domingo_fechado() -> None:
    r = regra({**{d: UTIL for d in range(5)}, 5: (("08:00", "12:00"),)})
    assert esta_dentro_janela_trabalho(em(SAB, "08:00"), regra=r) is True
    assert esta_dentro_janela_trabalho(em(SAB, "11:59"), regra=r) is True
    assert esta_dentro_janela_trabalho(em(SAB, "12:00"), regra=r) is False
    assert esta_dentro_janela_trabalho(em(SAB, "14:00"), regra=r) is False
    assert esta_dentro_janela_acesso(em(SAB, "07:30"), regra=r) is True
    assert esta_dentro_janela_acesso(em(DOM, "09:00"), regra=r) is False
    assert duracao_horas_dia(r.dias[5]) == 4.0
    assert duracao_horas_dia(r.dias[6]) == 0.0


def test_tres_periodos_no_mesmo_dia() -> None:
    tres = (("08:00", "10:00"), ("11:00", "13:00"), ("14:00", "18:00"))
    r = regra({0: tres})
    dentro = ["08:00", "09:59", "11:00", "12:59", "14:00", "17:59"]
    fora = ["07:59", "10:00", "10:59", "13:00", "13:59", "18:00"]
    assert all(esta_dentro_janela_trabalho(em(SEG, h), regra=r) for h in dentro)
    assert not any(esta_dentro_janela_trabalho(em(SEG, h), regra=r) for h in fora)
    # acesso: 07:30–10:00, 10:30–13:00, 13:30–18:00
    assert esta_dentro_janela_acesso(em(SEG, "10:29"), regra=r) is False
    assert esta_dentro_janela_acesso(em(SEG, "10:30"), regra=r) is True
    assert esta_dentro_janela_acesso(em(SEG, "13:29"), regra=r) is False
    assert esta_dentro_janela_acesso(em(SEG, "13:30"), regra=r) is True
    assert duracao_horas_dia(r.dias[0]) == 8.0


def test_periodos_sao_ordenados_independente_da_entrada() -> None:
    janela = janela_de_periodos([("13:00", "18:00"), ("08:00", "12:00")])
    assert janela.lista_periodos() == (("08:00", "12:00"), ("13:00", "18:00"))
    assert janela.ativo is True
    assert janela_de_periodos([]).ativo is False


# ── próximos instantes ───────────────────────────────────────────────────────────────────────────────────────────


def test_proximo_acesso() -> None:
    r = regra()
    assert proximo_acesso(em(SEG, "07:00"), regra=r) == em(SEG, "07:30").replace(tzinfo=ZoneInfo(SP))
    assert proximo_acesso(em(SEG, "12:10"), regra=r) == em(SEG, "12:30").replace(tzinfo=ZoneInfo(SP))
    assert proximo_acesso(em(SEG, "09:00"), regra=r) == em(SEG, "09:00").replace(tzinfo=ZoneInfo(SP))  # já pode: devolve agora
    assert proximo_acesso(em(SEG, "18:00"), regra=r) == em(TER, "07:30").replace(tzinfo=ZoneInfo(SP))
    assert proximo_acesso(em(SEX, "18:00"), regra=r) == em(date(2026, 10, 19), "07:30").replace(tzinfo=ZoneInfo(SP))  # pula o fim de semana
    assert proximo_acesso(em(SAB, "10:00"), regra=r) == em(date(2026, 10, 19), "07:30").replace(tzinfo=ZoneInfo(SP))


def test_proximo_inicio_trabalho() -> None:
    r = regra()
    tz = ZoneInfo(SP)
    assert proximo_inicio_trabalho(em(SEG, "07:59"), regra=r) == em(SEG, "08:00").replace(tzinfo=tz)
    assert proximo_inicio_trabalho(em(SEG, "12:00"), regra=r) == em(SEG, "13:00").replace(tzinfo=tz)
    assert proximo_inicio_trabalho(em(SEG, "13:30"), regra=r) == em(SEG, "13:30").replace(tzinfo=tz)  # já está trabalhando
    assert proximo_inicio_trabalho(em(SEX, "19:00"), regra=r) == em(date(2026, 10, 19), "08:00").replace(tzinfo=tz)


def test_sem_nenhum_dia_aberto_nao_ha_proximo_e_nao_laca() -> None:
    r = regra({})
    assert proximo_acesso(em(SEG, "10:00"), regra=r) is None
    assert proximo_inicio_trabalho(em(SEG, "10:00"), regra=r) is None


def test_regra_desligada_proximo_e_agora() -> None:
    r = regra(ativo=False)
    assert proximo_acesso(em(DOM, "03:00"), regra=r) == em(DOM, "03:00").replace(tzinfo=ZoneInfo(SP))


def test_antecedencia_que_cruza_a_meia_noite() -> None:
    r = regra({1: (("00:10", "06:00"),)}, antecedencia=30)  # terça 00:10; acesso a partir de segunda 23:40
    assert esta_dentro_janela_acesso(em(SEG, "23:39"), regra=r) is False
    assert esta_dentro_janela_acesso(em(SEG, "23:40"), regra=r) is True
    assert esta_dentro_janela_trabalho(em(SEG, "23:50"), regra=r) is False
    assert proximo_acesso(em(SEG, "20:00"), regra=r) == em(SEG, "23:40").replace(tzinfo=ZoneInfo(SP))


# ── dias especiais e precedência ─────────────────────────────────────────────────────────────────────────────────


def especial(data, tipo, *, origem="manual", ativo=True, periodos=()):
    return DiaEspecial(data=data, tipo=tipo, origem=origem, ativo=ativo, nome=tipo, periodos=tuple(periodos))


def test_feriado_ativo_fecha_o_dia_inclusive_o_exemplo_12_10() -> None:
    r = regra(especiais=[especial(SEG, "feriado")])  # segunda 12/10 normal 08–18, mas feriado
    for hora in ("07:30", "08:00", "10:00", "13:00"):
        assert esta_dentro_janela_trabalho(em(SEG, hora), regra=r) is False
        assert esta_dentro_janela_acesso(em(SEG, hora), regra=r) is False
        assert esta_dentro_expediente(em(SEG, hora), regra=r) is False
    assert esta_dentro_janela_trabalho(em(TER, "09:00"), regra=r) is True  # só aquela data
    assert dia_aberto(r, SEG) is False and dia_aberto(r, TER) is True
    assert proximo_inicio_trabalho(em(SEG, "07:00"), regra=r) == em(TER, "08:00").replace(tzinfo=ZoneInfo(SP))


def test_recesso_ativo_fecha_o_dia() -> None:
    r = regra(especiais=[especial(SEG, "recesso")])
    assert esta_dentro_janela_trabalho(em(SEG, "09:00"), regra=r) is False


def test_dia_especial_inativo_nao_conta() -> None:
    r = regra(especiais=[especial(SEG, "feriado", ativo=False)])
    assert esta_dentro_janela_trabalho(em(SEG, "09:00"), regra=r) is True


def test_trabalho_excepcional_abre_dia_fechado_com_periodos_proprios() -> None:
    r = regra(especiais=[especial(SAB, "trabalho_excepcional", periodos=[("09:00", "13:00")])])
    assert esta_dentro_janela_trabalho(em(SAB, "08:59"), regra=r) is False
    assert esta_dentro_janela_trabalho(em(SAB, "09:00"), regra=r) is True
    assert esta_dentro_janela_trabalho(em(SAB, "12:59"), regra=r) is True
    assert esta_dentro_janela_trabalho(em(SAB, "13:00"), regra=r) is False
    assert esta_dentro_janela_acesso(em(SAB, "08:30"), regra=r) is True
    assert esta_dentro_janela_acesso(em(SAB, "08:29"), regra=r) is False
    assert periodos_do_dia(r, SAB) == (("09:00", "13:00"),)
    assert periodos_do_dia(r, DOM) == ()


def test_trabalho_excepcional_substitui_os_periodos_da_semana() -> None:
    r = regra(especiais=[especial(SEG, "trabalho_excepcional", periodos=[("10:00", "14:00")])])
    assert esta_dentro_janela_trabalho(em(SEG, "08:30"), regra=r) is False  # no dia normal seria trabalho
    assert esta_dentro_janela_trabalho(em(SEG, "10:00"), regra=r) is True
    assert esta_dentro_janela_trabalho(em(SEG, "16:00"), regra=r) is False


def test_ignorado_neutraliza_feriado_automatico() -> None:
    auto = especial(SEG, "feriado", origem="automatico")
    ignorar = especial(SEG, "ignorado", origem="manual")
    assert esta_dentro_janela_trabalho(em(SEG, "09:00"), regra=regra(especiais=[auto])) is False
    sem_efeito = regra(especiais=[auto, ignorar])
    assert resolver_dia_especial(sem_efeito, SEG) is None
    assert esta_dentro_janela_trabalho(em(SEG, "09:00"), regra=sem_efeito) is True  # a decisão explícita da empresa vence


def test_ignorado_sozinho_nao_tem_efeito_proprio() -> None:
    r = regra(especiais=[especial(SEG, "ignorado")])
    assert esta_dentro_janela_trabalho(em(SEG, "09:00"), regra=r) is True
    assert esta_dentro_janela_trabalho(em(SAB, "09:00"), regra=regra(especiais=[especial(SAB, "ignorado")])) is False


def test_manual_ativo_vence_automatico_na_mesma_data() -> None:
    auto = especial(SEG, "feriado", origem="automatico")
    manual = especial(SEG, "trabalho_excepcional", origem="manual", periodos=[("09:00", "12:00")])
    r = regra(especiais=[auto, manual])
    assert esta_dentro_janela_trabalho(em(SEG, "10:00"), regra=r) is True
    assert esta_dentro_janela_trabalho(em(SEG, "15:00"), regra=r) is False


def test_manual_inativo_nao_anula_o_automatico() -> None:
    auto = especial(SEG, "feriado", origem="automatico")
    manual_desligado = especial(SEG, "ignorado", origem="manual", ativo=False)
    assert esta_dentro_janela_trabalho(em(SEG, "10:00"), regra=regra(especiais=[auto, manual_desligado])) is False


def test_automatico_desativado_pela_empresa_nao_fecha() -> None:
    assert esta_dentro_janela_trabalho(em(SEG, "10:00"), regra=regra(especiais=[especial(SEG, "feriado", origem="automatico", ativo=False)])) is True


def test_janela_do_dia_reflete_o_dia_especial() -> None:
    r = regra(especiais=[especial(SEG, "feriado")])
    assert janela_do_dia(r, SEG).ativo is False
    assert janela_do_dia(r, TER).lista_periodos() == UTIL


# ── fuso e horário de verão ──────────────────────────────────────────────────────────────────────────────────────


def test_o_fuso_da_regra_decide_o_relogio_nao_o_utc() -> None:
    r = regra()
    instante = datetime(2026, 10, 12, 10, 29, tzinfo=timezone.utc)  # 07:29 em São Paulo (UTC-3)
    assert esta_dentro_janela_acesso(instante, regra=r) is False
    assert esta_dentro_janela_acesso(instante + timedelta(minutes=1), regra=r) is True
    assert esta_dentro_janela_trabalho(datetime(2026, 10, 12, 11, 0, tzinfo=timezone.utc), regra=r) is True  # 08:00 SP


def test_regras_com_fusos_diferentes_decidem_diferente_para_o_mesmo_instante() -> None:
    instante = datetime(2026, 10, 12, 11, 0, tzinfo=timezone.utc)  # 08:00 SP, 07:00 Manaus (UTC-4)
    assert esta_dentro_janela_trabalho(instante, regra=regra(tz="America/Sao_Paulo")) is True
    assert esta_dentro_janela_trabalho(instante, regra=regra(tz="America/Manaus")) is False


def test_horario_de_verao_nao_desloca_a_regra() -> None:
    """Fuso com DST (America/New_York): 08:00 local é SEMPRE trabalho, antes e depois da virada de 08/03/2026."""
    r = regra({d: (("08:00", "17:00"),) for d in range(5)}, tz="America/New_York")
    sexta_inverno = datetime(2026, 3, 6, 12, 30, tzinfo=timezone.utc)  # 07:30 EST (UTC-5)
    assert esta_dentro_janela_acesso(sexta_inverno - timedelta(minutes=1), regra=r) is False
    assert esta_dentro_janela_acesso(sexta_inverno, regra=r) is True
    segunda_verao = datetime(2026, 3, 9, 11, 30, tzinfo=timezone.utc)  # 07:30 EDT (UTC-4), um dia útil depois da virada
    assert esta_dentro_janela_acesso(segunda_verao - timedelta(minutes=1), regra=r) is False
    assert esta_dentro_janela_acesso(segunda_verao, regra=r) is True
    assert esta_dentro_janela_trabalho(segunda_verao + timedelta(minutes=30), regra=r) is True  # 08:00 EDT
    assert esta_dentro_janela_trabalho(segunda_verao + timedelta(minutes=29), regra=r) is False
    proximo = proximo_acesso(datetime(2026, 3, 6, 23, 0, tzinfo=timezone.utc), regra=r)  # sexta à noite
    assert proximo.astimezone(timezone.utc) == segunda_verao


# ── equivalência com o modelo ANTIGO (manhã/tarde + tolerância) ──────────────────────────────────────────────────


def _antigo_dentro(momento: datetime, dias: dict[int, JanelaDia], tolerancia: int, ativo: bool = True) -> bool:
    """Cópia FIEL do algoritmo anterior à Fase Expediente 1 (`esta_dentro_expediente` da 2G.3) — o oráculo da equivalência."""
    if not ativo:
        return True
    dia = dias.get(momento.weekday())
    if dia is None or not dia.ativo:
        return False

    def minutos(texto):
        h, m = (int(p) for p in texto.split(":"))
        return h * 60 + m

    atual = momento.hour * 60 + momento.minute
    dentro_manha = dia.manha_inicio is not None and dia.manha_fim is not None and minutos(dia.manha_inicio) <= atual < minutos(dia.manha_fim)
    inicio_tarde = minutos(dia.tarde_inicio) - tolerancia if dia.tarde_inicio is not None else None
    dentro_tarde = inicio_tarde is not None and dia.tarde_fim is not None and inicio_tarde <= atual < minutos(dia.tarde_fim)
    return dentro_manha or dentro_tarde


CONFIGS = {
    "producao_boxcom": ({d: ("09:00", "12:00", "13:00", "18:00") for d in range(5)}, 30),
    "sem_tolerancia": ({d: ("08:00", "12:00", "13:00", "18:00") for d in range(5)}, 0),
    "padrao_do_codigo": ({d: ("09:00", "12:00", "14:00", "19:00") for d in range(5)}, 30),
    "sabado_aberto": ({**{d: ("08:00", "12:00", "13:30", "17:30") for d in range(5)}, 5: ("08:00", "12:00", "12:00", "16:00")}, 15),
}


@pytest.mark.parametrize("nome", list(CONFIGS))
def test_equivalencia_do_gate_de_entrada_em_todos_os_minutos_da_semana(nome) -> None:
    """Migração: manhã/tarde antigos → períodos 1 e 2 NOMINAIS + a mesma tolerância legada. O gate de entrada em execução responde IGUAL, minuto a minuto."""
    horarios, tolerancia = CONFIGS[nome]
    antigos = {d: JanelaDia(ativo=True, manha_inicio=h[0], manha_fim=h[1], tarde_inicio=h[2], tarde_fim=h[3]) for d, h in horarios.items()}
    for d in range(7):
        antigos.setdefault(d, JanelaDia(ativo=False))
    novos = {d: janela_de_periodos([(horarios[d][0], horarios[d][1]), (horarios[d][2], horarios[d][3])] if d in horarios else []) for d in range(7)}
    nova = RegraExpediente(ativo=True, tolerancia_retomada_minutos=tolerancia, dias=novos, timezone=SP)
    segunda = datetime(2026, 10, 12)
    for minuto in range(7 * 24 * 60):
        momento = segunda + timedelta(minutes=minuto)
        assert esta_dentro_expediente(momento, regra=nova) is _antigo_dentro(momento, antigos, tolerancia), momento


def test_legado_e_novo_dao_o_mesmo_sla() -> None:
    """A calculadora de SLA enxerga os períodos NOMINAIS (sem tolerância legada): forma antiga (manhã/tarde) e forma nova (períodos) produzem datas idênticas."""
    horarios, tolerancia = CONFIGS["producao_boxcom"]
    antigos = {d: JanelaDia(ativo=True, manha_inicio=h[0], manha_fim=h[1], tarde_inicio=h[2], tarde_fim=h[3]) for d, h in horarios.items()}
    for d in range(7):
        antigos.setdefault(d, JanelaDia(ativo=False))
    novos = {d: janela_de_periodos([(horarios[d][0], horarios[d][1]), (horarios[d][2], horarios[d][3])] if d in horarios else []) for d in range(7)}
    r_antiga = RegraExpediente(ativo=True, tolerancia_retomada_minutos=tolerancia, dias=antigos)
    r_nova = RegraExpediente(ativo=True, tolerancia_retomada_minutos=tolerancia, dias=novos, timezone=SP)
    tz = ZoneInfo(SP)
    inicios = [datetime(2026, 10, 12, h, m, tzinfo=tz) for h in (6, 9, 11, 12, 13, 17, 18, 22) for m in (0, 30)]
    inicios += [datetime(2026, 10, 16, 17, 45, tzinfo=tz), datetime(2026, 10, 17, 10, 0, tzinfo=tz)]
    for inicio in inicios:
        for quantidade, unidade, so_expediente in [(30, "minutos", True), (4, "horas", True), (10, "horas", True), (3, "dias_uteis", True), (5, "horas", False), (2, "dias_corridos", True)]:
            esperado = calcular_data_limite(inicio, quantidade, unidade, so_expediente, r_antiga)
            assert calcular_data_limite(inicio, quantidade, unidade, so_expediente, r_nova) == esperado, (inicio, quantidade, unidade)


def test_sla_pula_feriado_e_usa_dia_excepcional() -> None:
    tz = ZoneInfo(SP)
    r = regra(especiais=[especial(TER, "feriado")])
    inicio = datetime(2026, 10, 12, 17, 0, tzinfo=tz)  # segunda 17:00
    # 2 horas úteis: 1 h na segunda (17–18) e 1 h na QUARTA (terça é feriado) às 08:00–09:00
    assert calcular_data_limite(inicio, 2, "horas", True, r) == datetime(2026, 10, 14, 9, 0, tzinfo=tz)
    # 1 dia útil a partir da segunda pula a terça
    assert calcular_data_limite(inicio, 1, "dias_uteis", True, r).date() == date(2026, 10, 14)
    excepcional = regra(especiais=[especial(SAB, "trabalho_excepcional", periodos=[("09:00", "12:00")])])
    sexta_tarde = datetime(2026, 10, 16, 17, 30, tzinfo=tz)
    assert calcular_data_limite(sexta_tarde, 1, "horas", True, excepcional) == datetime(2026, 10, 17, 9, 30, tzinfo=tz)
