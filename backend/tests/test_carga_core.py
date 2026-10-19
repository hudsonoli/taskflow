"""11B.2B-B — cálculo PURO da Carga semanal: calendário, capacidade, arredondamento, janela e responsabilidade. Sem banco, sem HTTP, sem relógio.

Calendário de referência: seg–sex, 09–12 e 13–18 = 480 min/dia nominais; sábado e domingo fechados. Semana de 2026-10-19 (segunda).
"""
from __future__ import annotations

import itertools
from datetime import date, timedelta

import pytest

from app.core.carga_calculo import (
    CAPACIDADE_EXPEDIENTE_DESLIGADO,
    EtapaEntrada,
    PessoaElegivel,
    calcular_carga,
)
from app.core.carga_semanal import (
    ALOCACAO_ALOCADA,
    ALOCACAO_JANELA_VENCIDA,
    ALOCACAO_SEM_DIA_UTIL,
    alocar_janela,
    aplicar_percentual,
    dividir_igual,
    distribuir_por_pesos,
    minutos_nominais_do_dia,
    obter_capacidade_usuario,
    segunda_da_semana,
)
from app.core.expediente import DiaEspecial, RegraExpediente, janela_de_periodos

SEG = date(2026, 10, 19)
SEG2 = SEG + timedelta(days=7)
SEG3 = SEG + timedelta(days=14)
UTIL = (("09:00", "12:00"), ("13:00", "18:00"))


def regra(*, ativo: bool = True, especiais: tuple[DiaEspecial, ...] = ()) -> RegraExpediente:
    dias = {d: janela_de_periodos(UTIL) for d in range(5)}
    dias[5] = janela_de_periodos(())
    dias[6] = janela_de_periodos(())
    return RegraExpediente(ativo=ativo, tolerancia_retomada_minutos=0, dias=dias, timezone="America/Sao_Paulo", dias_especiais=especiais)


def etapa(i: int = 1, *, est=60, ini=None, fim=None, users=(), deps=()) -> EtapaEntrada:
    return EtapaEntrada(
        etapa_id=f"e{i}", demanda_id=f"d{i}", etapa_nome=f"Etapa {i}", etapa_tipo="execucao", ordem=1, estimativa_min=est,
        planejado_inicio=ini, planejado_fim=fim, usuario_ids=tuple(users), departamento_ids=tuple(deps),
    )


PESSOAS = [PessoaElegivel("a", "Ana", "dep1"), PessoaElegivel("b", "Bia", "dep1"), PessoaElegivel("c", "Caio", "dep2")]


def calcular(etapas, *, hoje=SEG, semana=SEG, r=None, pct=100, pessoas=None):
    return calcular_carga(etapas=etapas, pessoas=PESSOAS if pessoas is None else pessoas, regra=r if r is not None else regra(), percentual_alocavel=pct, hoje=hoje, semana_inicio=semana)


# ── calendário e capacidade ────────────────────────────────────────────────────────────────────────────────────────


def test_segunda_como_inicio_da_semana() -> None:
    assert segunda_da_semana(date(2026, 10, 19)) == SEG  # segunda
    assert segunda_da_semana(date(2026, 10, 25)) == SEG  # domingo ainda é a semana que começou na segunda
    assert segunda_da_semana(date(2026, 10, 26)) == SEG2


def test_minutos_nominais_dia_util_fim_de_semana_feriado_e_trabalho_excepcional() -> None:
    especiais = (
        DiaEspecial(data=date(2026, 10, 21), tipo="feriado", nome="Feriado"),
        DiaEspecial(data=date(2026, 10, 24), tipo="trabalho_excepcional", nome="Plantão", periodos=(("08:00", "12:00"),)),
        DiaEspecial(data=date(2026, 10, 22), tipo="recesso", nome="Recesso", ativo=False),  # desligado: não vale
    )
    r = regra(especiais=especiais)
    assert minutos_nominais_do_dia(r, date(2026, 10, 19)) == 480
    assert minutos_nominais_do_dia(r, date(2026, 10, 21)) == 0  # feriado ativo fecha
    assert minutos_nominais_do_dia(r, date(2026, 10, 22)) == 480  # recesso inativo é ignorado
    assert minutos_nominais_do_dia(r, date(2026, 10, 24)) == 240  # sábado com períodos próprios
    assert minutos_nominais_do_dia(r, date(2026, 10, 25)) == 0


@pytest.mark.parametrize(("pct", "esperado"), [(100, 2400), (75, 1800), (50, 1200), (1, 24)])
def test_fator_alocavel_sobre_a_capacidade_nominal(pct, esperado) -> None:
    dias = [SEG + timedelta(days=i) for i in range(7)]
    cap = obter_capacidade_usuario(None, dias, regra=regra(), percentual_alocavel=pct)
    assert cap.nominal_min == 2400 and cap.alocavel_min == esperado


def test_percentual_arredonda_meio_para_cima_em_inteiros() -> None:
    assert aplicar_percentual(1, 50) == 1  # 0,5 → 1
    assert aplicar_percentual(3, 50) == 2  # 1,5 → 2
    assert aplicar_percentual(10, 75) == 8  # 7,5 → 8
    assert aplicar_percentual(0, 75) == 0


def test_capacidade_nao_depende_do_usuario_na_v1_mas_aceita_o_argumento() -> None:
    dias = [SEG]
    assert obter_capacidade_usuario("qualquer", dias, regra=regra(), percentual_alocavel=100) == obter_capacidade_usuario(None, dias, regra=regra(), percentual_alocavel=100)


# ── divisão inteira ────────────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(("total", "n", "esperado"), [(1, 2, [1, 0]), (241, 2, [121, 120]), (100, 3, [34, 33, 33]), (0, 3, [0, 0, 0]), (7, 1, [7]), (5, 5, [1, 1, 1, 1, 1])])
def test_divisao_igual_conserva_e_e_deterministica(total, n, esperado) -> None:
    assert dividir_igual(total, n) == esperado
    assert dividir_igual(total, n) == esperado  # mesma entrada, mesma saída


def test_distribuicao_por_pesos_conserva_o_total_em_milhares_de_casos() -> None:
    for total, pesos in itertools.product(range(0, 40), [(1, 1), (3, 5), (480, 480, 480, 240), (0, 7, 0), (1, 2, 3, 4, 5), (13, 17, 19)]):
        partes = distribuir_por_pesos(total, pesos)
        assert sum(partes) == (total if sum(pesos) else 0), (total, pesos)
        assert all(parte >= 0 for parte in partes)
        assert all(parte == 0 for parte, peso in zip(partes, pesos) if peso == 0), "peso zero nunca recebe minutos"


def test_distribuicao_proporcional_com_pesos_diferentes() -> None:
    assert distribuir_por_pesos(600, [2400, 1200, 600]) == [343, 171, 86]  # 342,86/171,43/85,71 → maior resto
    assert sum(distribuir_por_pesos(600, [2400, 1200, 600])) == 600


# ── janela planejada ───────────────────────────────────────────────────────────────────────────────────────────────


def minutos(r=None):
    r = r or regra()
    return lambda dia: minutos_nominais_do_dia(r, dia)


def test_janela_na_mesma_semana_vai_toda_para_ela() -> None:
    res = alocar_janela(300, date(2026, 10, 20), date(2026, 10, 22), SEG, minutos())
    assert res.estado == ALOCACAO_ALOCADA and res.por_semana == {SEG: 300}


def test_janela_atravessando_duas_semanas_e_tres_semanas_conservam() -> None:
    duas = alocar_janela(601, date(2026, 10, 22), date(2026, 10, 28), SEG, minutos())  # qui, sex | seg, ter, qua → 2×480 e 3×480
    assert set(duas.por_semana) == {SEG, SEG2} and sum(duas.por_semana.values()) == 601
    tres = alocar_janela(600, date(2026, 10, 19), date(2026, 11, 6), SEG, minutos())  # 3 semanas completas
    assert set(tres.por_semana) == {SEG, SEG2, SEG3} and tres.por_semana == {SEG: 200, SEG2: 200, SEG3: 200}


def test_janela_iniciada_no_passado_e_vigente_so_distribui_de_hoje_em_diante() -> None:
    hoje = date(2026, 10, 21)  # quarta
    res = alocar_janela(900, date(2026, 10, 12), date(2026, 10, 30), hoje, minutos())  # restantes: qua..sex (3) + 2ª semana (5) = 8 dias
    assert res.estado == ALOCACAO_ALOCADA
    assert sum(res.por_semana.values()) == 900
    assert set(res.por_semana) == {SEG, SEG2}
    assert res.por_semana[SEG] == 338 and res.por_semana[SEG2] == 562  # 900×3/8 = 337,5 → 338 (maior resto); 900×5/8 = 562,5 → 562


def test_janela_vencida_nao_distribui_nem_move() -> None:
    res = alocar_janela(300, date(2026, 10, 1), date(2026, 10, 16), SEG, minutos())
    assert res.estado == ALOCACAO_JANELA_VENCIDA and res.por_semana == {}


def test_fim_igual_a_hoje_ainda_esta_vigente() -> None:
    res = alocar_janela(100, date(2026, 10, 10), SEG, SEG, minutos())
    assert res.estado == ALOCACAO_ALOCADA and res.por_semana == {SEG: 100}


def test_janela_so_em_dias_fechados_e_sem_dia_util_e_nao_vai_para_segunda() -> None:
    res = alocar_janela(300, date(2026, 10, 24), date(2026, 10, 25), SEG, minutos())  # sábado → domingo
    assert res.estado == ALOCACAO_SEM_DIA_UTIL and res.por_semana == {}


def test_janela_so_com_feriado_e_sem_dia_util() -> None:
    r = regra(especiais=(DiaEspecial(data=date(2026, 10, 21), tipo="feriado", nome="F"),))
    res = alocar_janela(300, date(2026, 10, 21), date(2026, 10, 21), SEG, minutos(r))
    assert res.estado == ALOCACAO_SEM_DIA_UTIL


def test_sem_estimativa_classifica_sem_distribuir() -> None:
    res = alocar_janela(None, date(2026, 10, 20), date(2026, 10, 22), SEG, minutos())
    assert res.estado == ALOCACAO_ALOCADA and res.por_semana == {}


# ── cálculo completo ───────────────────────────────────────────────────────────────────────────────────────────────


def test_semana_atual_recorta_em_hoje_e_semana_futura_e_completa() -> None:
    quarta = date(2026, 10, 21)
    atual = calcular([], hoje=quarta, semana=SEG)
    assert atual.recorte_hoje is True
    assert [(d.isoformat(), ok) for d, _m, ok in atual.dias][:4] == [("2026-10-19", False), ("2026-10-20", False), ("2026-10-21", True), ("2026-10-22", True)]
    assert atual.capacidade_nominal_pessoa_min == 3 * 480  # qua, qui, sex (hoje conta inteiro)
    futura = calcular([], hoje=quarta, semana=SEG2)
    assert futura.recorte_hoje is False and all(ok for _d, _m, ok in futura.dias) and futura.capacidade_nominal_pessoa_min == 2400


def test_hoje_conta_como_dia_completo_mesmo_no_fim_da_tarde() -> None:
    assert calcular([], hoje=SEG, semana=SEG).capacidade_nominal_pessoa_min == 2400


def test_fator_75_na_capacidade_da_semana() -> None:
    r = calcular([], pct=75)
    assert (r.capacidade_nominal_pessoa_min, r.capacidade_alocavel_pessoa_min) == (2400, 1800)


def test_expediente_desligado_nao_inventa_capacidade_nem_distribui() -> None:
    e = etapa(1, est=300, ini=date(2026, 10, 20), fim=date(2026, 10, 22), users=["a"])
    r = calcular([e], r=regra(ativo=False))
    assert r.capacidade_indisponivel == CAPACIDADE_EXPEDIENTE_DESLIGADO
    assert r.capacidade_nominal_pessoa_min is None and r.capacidade_alocavel_pessoa_min is None
    assert r.pessoas["a"].planejado_min == 0 and r.etapas[0].planejado_semana_min is None and r.etapas[0].alocacao_estado is None
    assert all(m is None for _d, m, _ok in r.dias)


def test_sem_regra_equivale_a_expediente_desligado() -> None:
    assert calcular([], r=None) is not None  # r=None cai no default `regra()` do helper; o caso real é testado abaixo
    direto = calcular_carga(etapas=[], pessoas=PESSOAS, regra=None, percentual_alocavel=100, hoje=SEG, semana_inicio=SEG)
    assert direto.capacidade_indisponivel == CAPACIDADE_EXPEDIENTE_DESLIGADO


def test_janela_vencida_aparece_mesmo_com_expediente_desligado() -> None:
    e = etapa(1, est=300, ini=date(2026, 10, 1), fim=date(2026, 10, 10), users=["a"])
    assert calcular([e], r=regra(ativo=False)).etapas[0].alocacao_estado == ALOCACAO_JANELA_VENCIDA


def test_sem_janela_e_janela_incompleta_ficam_fora_da_ocupacao_mas_com_minutos_conhecidos() -> None:
    r = calcular([etapa(1, est=90, users=["a"]), etapa(2, est=60, ini=date(2026, 10, 20), users=["a"]), etapa(3, est=None, users=["a"])])
    a = r.pessoas["a"]
    assert a.planejado_min == 0
    assert a.nao_planejado_min == 150  # 90 + 60; a sem estimativa não soma zero fictício
    assert a.sem_estimativa == {"e3"}
    motivos = {e.entrada.etapa_id: e.motivo_nao_planejado for e in r.etapas}
    assert motivos == {"e1": "sem_janela", "e2": "janela_incompleta", "e3": "sem_janela"}


def test_estimativa_zero_e_diferente_de_sem_estimativa() -> None:
    r = calcular([etapa(1, est=0, ini=date(2026, 10, 20), fim=date(2026, 10, 22), users=["a"])])
    assert r.pessoas["a"].sem_estimativa == set() and r.etapas[0].planejado_semana_min == 0


def test_semana_consultada_recebe_so_a_sua_parte_e_a_soma_das_semanas_e_o_restante() -> None:
    e = etapa(1, est=600, ini=date(2026, 10, 19), fim=date(2026, 11, 6), users=["a"])  # 3 semanas
    partes = [calcular([e], semana=s).pessoas["a"].planejado_min for s in (SEG, SEG2, SEG3)]
    assert partes == [200, 200, 200] and sum(partes) == 600


def test_multiplos_responsaveis_dividem_igual_e_conservam() -> None:
    e = etapa(1, est=241, ini=date(2026, 10, 19), fim=date(2026, 10, 23), users=["b", "a"])  # ordem de entrada não importa
    r = calcular([e])
    assert (r.pessoas["a"].planejado_min, r.pessoas["b"].planejado_min) == (121, 120)  # resto para o menor id
    assert r.etapas[0].planejado_semana_min == 241 and r.etapas[0].origem == "responsavel"


def test_usuario_mais_departamento_a_carga_vai_so_para_o_usuario() -> None:
    r = calcular([etapa(1, est=120, ini=date(2026, 10, 19), fim=date(2026, 10, 19), users=["a"], deps=["dep1", "dep2"])])
    assert r.pessoas["a"].planejado_min == 120 and r.pools_departamento == {} and r.pool_sem_departamento.planejado_min == 0


def test_sem_usuario_um_departamento_vira_pool_integral() -> None:
    r = calcular([etapa(1, est=120, ini=date(2026, 10, 19), fim=date(2026, 10, 19), deps=["dep1"])])
    assert r.pools_departamento["dep1"].planejado_min == 120 and r.etapas[0].origem == "pool_departamento"


def test_sem_usuario_dois_departamentos_dividem_o_pool_igualmente() -> None:
    r = calcular([etapa(1, est=241, ini=date(2026, 10, 19), fim=date(2026, 10, 19), deps=["dep2", "dep1"])])
    assert (r.pools_departamento["dep1"].planejado_min, r.pools_departamento["dep2"].planejado_min) == (121, 120)


def test_sem_usuario_e_sem_departamento_vai_para_o_pool_sem_departamento_e_nunca_some() -> None:
    r = calcular([etapa(1, est=90, ini=date(2026, 10, 19), fim=date(2026, 10, 19))])
    assert r.pool_sem_departamento.planejado_min == 90 and r.etapas[0].origem == "pool_sem_departamento"
    total = sum(a.planejado_min for a in r.pessoas.values()) + sum(a.planejado_min for a in r.pools_departamento.values()) + r.pool_sem_departamento.planejado_min
    assert total == 90


def test_responsavel_inelegivel_cai_no_pool_em_vez_de_sumir() -> None:
    # "x" é conta de sistema/inativo: não está em PESSOAS. A carga vai para o departamento da etapa.
    r = calcular([etapa(1, est=100, ini=date(2026, 10, 19), fim=date(2026, 10, 19), users=["x"], deps=["dep2"])])
    assert r.pools_departamento["dep2"].planejado_min == 100 and all(a.planejado_min == 0 for a in r.pessoas.values())


def test_so_um_dos_responsaveis_e_elegivel_a_carga_fica_com_ele() -> None:
    r = calcular([etapa(1, est=100, ini=date(2026, 10, 19), fim=date(2026, 10, 19), users=["a", "x"])])
    assert r.pessoas["a"].planejado_min == 100 and r.etapas[0].alvos == [("usuario", "a")]


def test_janela_vencida_e_sem_dia_util_viram_pendencias_e_nao_ocupam() -> None:
    vencida = etapa(1, est=120, ini=date(2026, 10, 1), fim=date(2026, 10, 9), users=["a"])
    fechada = etapa(2, est=60, ini=date(2026, 10, 24), fim=date(2026, 10, 25), users=["a"])
    r = calcular([vencida, fechada])
    estados = {e.entrada.etapa_id: e.alocacao_estado for e in r.etapas}
    assert estados == {"e1": ALOCACAO_JANELA_VENCIDA, "e2": ALOCACAO_SEM_DIA_UTIL}
    assert r.pessoas["a"].planejado_min == 0 and r.pessoas["a"].pendencia_min == 180
    assert all(e.estado_planejamento == "planejado" for e in r.etapas)  # continuam "planejado": o conflito é de ALOCAÇÃO, não da janela


def test_resultado_e_deterministico_independente_da_ordem_de_entrada() -> None:
    etapas = [etapa(i, est=100 + i, ini=date(2026, 10, 19), fim=date(2026, 10, 30), users=["a", "b", "c"][: (i % 3) + 1]) for i in range(1, 8)]
    um = calcular(etapas)
    dois = calcular(list(reversed(etapas)))
    assert {k: v.planejado_min for k, v in um.pessoas.items()} == {k: v.planejado_min for k, v in dois.pessoas.items()}
