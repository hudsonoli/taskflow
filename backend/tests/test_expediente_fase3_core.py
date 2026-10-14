"""Fase Expediente 3 — núcleo PURO do corte (fim de período): quando existe um corte pendente, catch-up, armadura da flag, calendário e chave de idempotência.

Exemplo oficial: 09:00–12:00 e 13:00–18:00 (seg–sex), fuso America/Sao_Paulo. Relógio sempre injetado.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core.expediente import (
    DiaEspecial,
    RegraExpediente,
    chave_de_execucao,
    correlation_id_da_execucao,
    cutoff_pendente,
    fins_de_periodo,
    janela_de_periodos,
    ultimo_fim_de_periodo,
)

SP = ZoneInfo("America/Sao_Paulo")
SEGUNDA = date(2026, 10, 5)
UTIL = (("09:00", "12:00"), ("13:00", "18:00"))


def _em(hhmm: str, dia: date = SEGUNDA, segundos: int = 0) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(dia.year, dia.month, dia.day, h, m, segundos, tzinfo=SP)


def _regra(armada: datetime | None = None, **extra) -> RegraExpediente:
    dias = {d: janela_de_periodos(UTIL if d < 5 else []) for d in range(7)}
    base = dict(
        ativo=True,
        tolerancia_retomada_minutos=30,
        dias=dias,
        timezone="America/Sao_Paulo",
        pausar_no_fim_periodo=True,
        pausa_automatica_ativada_em=armada if armada is not None else _em("08:00"),
    )
    base.update(extra)
    return RegraExpediente(**base)


# ── a matriz de horários do exemplo oficial ──────────────────────────────────────────────────────────────────────

# (hora, segundos, corte esperado ou None)
MATRIZ = [
    ("11:59", 0, None),  # ainda não terminou o 1º período (o corte de ontem já foi dado como processado pelo registro; aqui nada é elegível: a armadura é de hoje 08:00)
    ("12:00", 0, "12:00"),
    ("12:00", 30, "12:00"),  # o tick rodou 30 s depois: o corte continua sendo 12:00
    ("12:01", 0, "12:00"),
    ("12:30", 0, "12:00"),
    ("12:59", 0, "12:00"),
    ("13:00", 0, None),  # o 2º período COMEÇOU: o corte das 12:00 não pode mais ser aplicado
    ("17:59", 0, None),
    ("18:00", 0, "18:00"),
    ("18:01", 0, "18:00"),
]


@pytest.mark.parametrize("hora, segundos, esperado", MATRIZ)
def test_matriz_do_corte_no_exemplo_oficial(hora: str, segundos: int, esperado: str | None) -> None:
    corte = cutoff_pendente(_em(hora, segundos=segundos), _regra())
    if esperado is None:
        assert corte is None
    else:
        assert corte == _em(esperado)
        assert corte.second == 0  # o corte efetivo é o horário CONFIGURADO, nunca o instante do tick


def test_flag_desligada_ou_regra_desligada_ou_nunca_armada_nao_tem_corte() -> None:
    assert cutoff_pendente(_em("12:05"), _regra(pausar_no_fim_periodo=False)) is None
    assert cutoff_pendente(_em("12:05"), _regra(ativo=False)) is None
    sem_armadura = RegraExpediente(
        ativo=True, tolerancia_retomada_minutos=0, dias={d: janela_de_periodos(UTIL) for d in range(7)}, timezone="America/Sao_Paulo", pausar_no_fim_periodo=True
    )
    assert cutoff_pendente(_em("12:05"), sem_armadura) is None  # nunca armada = nunca pausa


# ── ativação no meio do intervalo ────────────────────────────────────────────────────────────────────────────────


def test_ligar_a_flag_as_1215_nao_pausa_retroativamente_o_corte_das_1200() -> None:
    regra = _regra(armada=_em("12:15"))
    assert cutoff_pendente(_em("12:20"), regra) is None
    assert cutoff_pendente(_em("12:59"), regra) is None
    assert cutoff_pendente(_em("18:00"), regra) == _em("18:00")  # o próximo corte vale normalmente


def test_corte_exatamente_na_armadura_nao_conta() -> None:
    assert cutoff_pendente(_em("12:05"), _regra(armada=_em("12:00"))) is None
    assert cutoff_pendente(_em("12:05"), _regra(armada=_em("11:59"))) == _em("12:00")


# ── catch-up (restart) ───────────────────────────────────────────────────────────────────────────────────────────


def test_restart_antes_do_proximo_periodo_ainda_processa_mas_depois_dele_nao() -> None:
    regra = _regra()
    assert cutoff_pendente(_em("12:20"), regra) == _em("12:00")  # restart 12:20: ainda pode
    assert cutoff_pendente(_em("13:10"), regra) is None  # restart 13:10: o 2º período já começou, não retro-pausa as 12:00
    assert cutoff_pendente(_em("18:30"), regra) == _em("18:00")  # 18:30: ainda pode
    assert cutoff_pendente(_em("23:59"), regra) == _em("18:00")
    amanha = SEGUNDA + timedelta(days=1)
    assert cutoff_pendente(_em("08:00", amanha), regra) == _em("18:00")  # nenhum período novo começou ainda (o registro de conclusão impede repetir)
    assert cutoff_pendente(_em("09:00", amanha), regra) is None  # o primeiro período de amanhã começou


def test_fim_de_semana_e_feriado_nao_tem_corte_proprio() -> None:
    sabado = date(2026, 10, 10)
    regra = _regra(armada=_em("08:00", sabado - timedelta(days=3)))
    assert fins_de_periodo(regra, sabado) == []
    assert cutoff_pendente(_em("12:05", sabado), regra) == _em("18:00", date(2026, 10, 9))  # o último fim foi sexta 18:00, nenhum período novo desde então
    feriado = _regra(dias_especiais=(DiaEspecial(data=SEGUNDA, tipo="feriado", nome="X"),))
    assert fins_de_periodo(feriado, SEGUNDA) == []
    assert cutoff_pendente(_em("12:05"), feriado) != _em("12:00")  # nenhum corte artificial no dia sem período


def test_trabalho_excepcional_cria_o_corte_do_proprio_periodo() -> None:
    sabado = date(2026, 10, 10)
    regra = _regra(armada=_em("08:00", sabado), dias_especiais=(DiaEspecial(data=sabado, tipo="trabalho_excepcional", periodos=(("10:00", "14:00"),)),))
    assert fins_de_periodo(regra, sabado) == [_em("14:00", sabado)]
    assert cutoff_pendente(_em("14:10", sabado), regra) == _em("14:00", sabado)
    assert cutoff_pendente(_em("13:59", sabado), regra) is None


def test_periodos_encostados_nao_tem_corte_entre_eles() -> None:
    dias = {d: janela_de_periodos((("08:00", "12:00"), ("12:00", "16:00")) if d < 5 else []) for d in range(7)}
    regra = _regra(dias=dias)
    assert fins_de_periodo(regra, SEGUNDA) == [_em("16:00")]  # 12:00 coincide com o início do período seguinte: o trabalho continua
    assert cutoff_pendente(_em("12:10"), regra) is None


def test_varios_periodos_cada_fim_e_um_corte() -> None:
    tres = (("08:00", "10:00"), ("11:00", "13:00"), ("14:00", "18:00"))
    regra = _regra(dias={d: janela_de_periodos(tres) for d in range(7)})
    assert fins_de_periodo(regra, SEGUNDA) == [_em("10:00"), _em("13:00"), _em("18:00")]
    assert cutoff_pendente(_em("10:30"), regra) == _em("10:00")
    assert cutoff_pendente(_em("11:00"), regra) is None


def test_o_ultimo_fim_de_periodo_olha_ate_sete_dias_para_tras() -> None:
    assert ultimo_fim_de_periodo(_em("08:00"), _regra()) == _em("18:00", SEGUNDA - timedelta(days=3))  # sexta (fim de semana fechado)
    fechada = _regra(dias={d: janela_de_periodos([]) for d in range(7)})
    assert ultimo_fim_de_periodo(_em("08:00"), fechada) is None


def test_o_fuso_e_o_da_regra() -> None:
    manaus = _regra(timezone="America/Manaus")
    # 12:00 em Manaus = 13:00 em São Paulo: às 12:30 em SP ainda não é o corte de Manaus (que seria 11:00 em SP... lido no relógio LOCAL de Manaus)
    instante_sp = _em("12:30")  # = 11:30 em Manaus → antes do corte local das 12:00
    assert cutoff_pendente(instante_sp, manaus) is None
    instante_sp = _em("13:30")  # = 12:30 em Manaus
    corte = cutoff_pendente(instante_sp, _regra(timezone="America/Manaus", armada=_em("07:00")))
    assert corte is not None and corte.utcoffset() == timedelta(hours=-4) and corte.hour == 12


# ── idempotência: chave e correlation_id ─────────────────────────────────────────────────────────────────────────


def test_a_chave_de_execucao_e_deterministica_e_usa_o_dia_local() -> None:
    chave = chave_de_execucao("emp-1", _em("12:00"))
    assert chave == "expediente:emp-1:2026-10-05:12:00"
    assert chave == chave_de_execucao("emp-1", _em("12:00", segundos=0))
    assert chave != chave_de_execucao("emp-1", _em("18:00"))
    assert chave != chave_de_execucao("emp-2", _em("12:00"))
    assert chave != chave_de_execucao("emp-1", _em("12:00", SEGUNDA + timedelta(days=1)))


def test_o_correlation_id_e_um_uuid_estavel() -> None:
    chave = chave_de_execucao("emp-1", _em("12:00"))
    primeiro = correlation_id_da_execucao(chave)
    assert primeiro == correlation_id_da_execucao(chave)
    assert str(uuid.UUID(primeiro)) == primeiro and len(primeiro) == 36
    assert primeiro != correlation_id_da_execucao(chave_de_execucao("emp-1", _em("18:00")))
