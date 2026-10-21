"""11B.2D-A — capacidade INDIVIDUAL (jornada própria + ausências): cálculo PURO. Sem banco.

Prova a hierarquia: empresa (fallback) → jornada individual (substitui a semana, dia vazio = 0) → ausência (dia inteiro, deduplicada por data) → dias especiais (feriado fecha; trabalho excepcional
nunca EXPANDE a jornada: interseção) → percentual alocável por último. E que a matemática de PLANEJAMENTO (rateio, distribuição por semana) não muda: só o denominador de capacidade por pessoa.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.core.capacidade_individual import (
    SEM_CONFIGURACAO,
    ConfiguracaoCapacidade,
    JornadaIndividual,
    dias_ausentes_da_semana,
    intersecao_periodos,
    minutos_do_usuario_no_dia,
    periodos_do_usuario_no_dia,
    unir_periodos,
)
from app.core.carga_calculo import EtapaEntrada, PessoaElegivel, calcular_carga
from app.core.carga_semanal import dias_da_semana, minutos_nominais_do_dia, obter_capacidade_usuario
from app.core.expediente import DiaEspecial, RegraExpediente, janela_de_periodos

SEG = date(2026, 10, 19)
SEG2 = SEG + timedelta(days=7)
UTIL = (("09:00", "12:00"), ("13:00", "18:00"))  # 8h


def regra(*, ativo: bool = True, especiais: tuple[DiaEspecial, ...] = ()) -> RegraExpediente:
    dias = {d: janela_de_periodos(UTIL) for d in range(5)}
    dias[5] = janela_de_periodos(())
    dias[6] = janela_de_periodos(())
    return RegraExpediente(ativo=ativo, tolerancia_retomada_minutos=0, dias=dias, timezone="America/Sao_Paulo", dias_especiais=especiais)


def jornada(horas_por_dia: dict[int, tuple[tuple[str, str], ...]]) -> JornadaIndividual:
    return JornadaIndividual(horas_por_dia)


def seg_a_sex(periodos: tuple[tuple[str, str], ...]) -> JornadaIndividual:
    return jornada({d: periodos for d in range(5)})


SEIS_HORAS = (("09:00", "15:00"),)
QUATRO_HORAS = (("09:00", "13:00"),)


def semana(inicio: date = SEG) -> list[date]:
    return dias_da_semana(inicio)


# ── primitivas de períodos ───────────────────────────────────────────────────────────────────────────────────────


def test_intersecao_com_multiplos_periodos() -> None:
    assert intersecao_periodos((("09:00", "12:00"), ("13:00", "17:00")), (("10:00", "14:00"),)) == (("10:00", "12:00"), ("13:00", "14:00"))


def test_intersecao_nunca_expande_nem_duplica_minutos() -> None:
    assert intersecao_periodos((("09:00", "15:00"),), (("09:00", "18:00"),)) == (("09:00", "15:00"),)  # jornada 09–15, especial 09–18 → 09–15
    assert intersecao_periodos((("09:00", "12:00"),), (("13:00", "18:00"),)) == ()
    # entradas sobrepostas não contam o mesmo minuto duas vezes
    assert intersecao_periodos((("09:00", "12:00"), ("11:00", "14:00")), (("10:00", "13:00"),)) == (("10:00", "13:00"),)
    assert intersecao_periodos((), (("09:00", "12:00"),)) == ()


def test_unir_periodos_funde_sobreposicao_e_encosto() -> None:
    assert unir_periodos((("13:00", "17:00"), ("09:00", "12:00"), ("12:00", "13:00"))) == (("09:00", "17:00"),)
    assert unir_periodos((("09:00", "12:00"), ("11:00", "14:00"))) == (("09:00", "14:00"),)


# ── fallback ─────────────────────────────────────────────────────────────────────────────────────────────────────


def test_sem_jornada_nem_ausencia_e_exatamente_o_expediente_da_empresa() -> None:
    especiais = (
        DiaEspecial(data=date(2026, 10, 21), tipo="feriado", nome="F"),
        DiaEspecial(data=date(2026, 10, 24), tipo="trabalho_excepcional", nome="P", periodos=(("08:00", "12:00"),)),
    )
    r = regra(especiais=especiais)
    for dia in semana():
        assert minutos_do_usuario_no_dia(r, dia, SEM_CONFIGURACAO) == minutos_nominais_do_dia(r, dia)
    cap = obter_capacidade_usuario("x", semana(), regra=r, percentual_alocavel=100)
    assert (cap.nominal_min, cap.origem, cap.dias_ausentes) == (sum(minutos_nominais_do_dia(r, d) for d in semana()), "empresa", 0)
    assert cap.nominal_min == 4 * 480 + 240  # feriado na quarta, sábado de plantão


# ── jornada individual ───────────────────────────────────────────────────────────────────────────────────────────


def test_jornada_substitui_a_semana_da_empresa() -> None:
    r = regra()
    seis = ConfiguracaoCapacidade(jornada=seg_a_sex(SEIS_HORAS))
    quatro = ConfiguracaoCapacidade(jornada=jornada({0: QUATRO_HORAS, 2: QUATRO_HORAS, 4: QUATRO_HORAS}))
    assert obter_capacidade_usuario("a", semana(), regra=r, percentual_alocavel=100).nominal_min == 2400  # 8h × 5
    assert obter_capacidade_usuario("b", semana(), regra=r, percentual_alocavel=100, configuracao=seis).nominal_min == 1800  # 6h × 5
    assert obter_capacidade_usuario("c", semana(), regra=r, percentual_alocavel=100, configuracao=quatro).nominal_min == 720  # 4h × 3
    assert obter_capacidade_usuario("b", semana(), regra=r, percentual_alocavel=100, configuracao=seis).origem == "individual"


def test_dia_sem_periodo_na_jornada_e_zero_sem_fallback_dia_a_dia() -> None:
    r = regra()  # empresa abre seg–sex
    so_segunda = ConfiguracaoCapacidade(jornada=jornada({0: SEIS_HORAS}))
    assert minutos_do_usuario_no_dia(r, SEG, so_segunda) == 360
    assert minutos_do_usuario_no_dia(r, SEG + timedelta(days=1), so_segunda) == 0  # terça: empresa abre, a jornada não
    # sábado "configurado" na jornada vale mesmo com a empresa fechada
    sabado = ConfiguracaoCapacidade(jornada=jornada({5: QUATRO_HORAS}))
    assert minutos_do_usuario_no_dia(r, date(2026, 10, 24), sabado) == 240


def test_jornada_sem_nenhum_periodo_e_capacidade_zero_explicita() -> None:
    cap = obter_capacidade_usuario("a", semana(), regra=regra(), percentual_alocavel=100, configuracao=ConfiguracaoCapacidade(jornada=jornada({})))
    assert (cap.nominal_min, cap.origem) == (0, "individual")


def test_jornada_com_multiplos_periodos_no_dia() -> None:
    cfg = ConfiguracaoCapacidade(jornada=jornada({0: (("09:00", "12:00"), ("13:00", "17:00"))}))
    assert minutos_do_usuario_no_dia(regra(), SEG, cfg) == 7 * 60


# ── ausências ────────────────────────────────────────────────────────────────────────────────────────────────────


def test_ausencia_zera_o_dia_e_ferias_seg_a_sex_zera_a_semana() -> None:
    r = regra()
    folga = ConfiguracaoCapacidade(dias_ausentes=frozenset({SEG + timedelta(days=2)}))
    assert minutos_do_usuario_no_dia(r, SEG + timedelta(days=2), folga) == 0
    assert obter_capacidade_usuario("a", semana(), regra=r, percentual_alocavel=100, configuracao=folga).nominal_min == 1920  # 4 dias
    ferias = ConfiguracaoCapacidade(dias_ausentes=dias_ausentes_da_semana([(SEG, SEG + timedelta(days=4))], semana()))
    cap = obter_capacidade_usuario("a", semana(), regra=r, percentual_alocavel=100, configuracao=ferias)
    assert (cap.nominal_min, cap.dias_ausentes, cap.origem) == (0, 5, "empresa")  # ausência não muda a origem


def test_ausencia_atravessando_duas_semanas_e_parcialmente_fora() -> None:
    intervalo = [(SEG + timedelta(days=3), SEG2 + timedelta(days=1))]  # quinta da 1ª → terça da 2ª
    s1 = dias_ausentes_da_semana(intervalo, semana(SEG))
    s2 = dias_ausentes_da_semana(intervalo, semana(SEG2))
    assert sorted(d.weekday() for d in s1) == [3, 4, 5, 6]
    assert sorted(d.weekday() for d in s2) == [0, 1]
    c1 = obter_capacidade_usuario("a", semana(SEG), regra=regra(), percentual_alocavel=100, configuracao=ConfiguracaoCapacidade(dias_ausentes=s1))
    c2 = obter_capacidade_usuario("a", semana(SEG2), regra=regra(), percentual_alocavel=100, configuracao=ConfiguracaoCapacidade(dias_ausentes=s2))
    assert (c1.nominal_min, c1.dias_ausentes) == (3 * 480, 4)  # seg, ter, qua sobram; qui/sex descontam, sáb/dom contam como dias ausentes mas já eram fechados
    assert (c2.nominal_min, c2.dias_ausentes) == (3 * 480, 2)


def test_ausencias_sobrepostas_nunca_descontam_duas_vezes() -> None:
    dias = dias_ausentes_da_semana([(SEG, SEG + timedelta(days=2)), (SEG + timedelta(days=1), SEG + timedelta(days=3))], semana())
    assert sorted(d.weekday() for d in dias) == [0, 1, 2, 3]  # 4 dias distintos, não 6
    cap = obter_capacidade_usuario("a", semana(), regra=regra(), percentual_alocavel=100, configuracao=ConfiguracaoCapacidade(dias_ausentes=dias))
    assert cap.nominal_min == 480 and cap.dias_ausentes == 4


def test_ausencia_em_fim_de_semana_e_em_dia_ja_fechado_nao_reduz_nada() -> None:
    fds = ConfiguracaoCapacidade(dias_ausentes=dias_ausentes_da_semana([(date(2026, 10, 24), date(2026, 10, 25))], semana()))
    assert obter_capacidade_usuario("a", semana(), regra=regra(), percentual_alocavel=100, configuracao=fds).nominal_min == 2400
    feriado = regra(especiais=(DiaEspecial(data=date(2026, 10, 21), tipo="feriado", nome="F"),))
    quarta = ConfiguracaoCapacidade(dias_ausentes=frozenset({date(2026, 10, 21)}))
    com = obter_capacidade_usuario("a", semana(), regra=feriado, percentual_alocavel=100, configuracao=quarta).nominal_min
    sem = obter_capacidade_usuario("a", semana(), regra=feriado, percentual_alocavel=100).nominal_min
    assert com == sem == 4 * 480  # o feriado já fechava o dia: a ausência não desconta de novo


# ── dias especiais ───────────────────────────────────────────────────────────────────────────────────────────────


def test_feriado_da_empresa_fecha_para_todos_inclusive_jornada_individual() -> None:
    r = regra(especiais=(DiaEspecial(data=SEG, tipo="feriado", nome="F"),))
    assert minutos_do_usuario_no_dia(r, SEG, SEM_CONFIGURACAO) == 0
    assert minutos_do_usuario_no_dia(r, SEG, ConfiguracaoCapacidade(jornada=seg_a_sex(SEIS_HORAS))) == 0


def test_trabalho_excepcional_sem_jornada_individual_usa_o_especial() -> None:
    sabado = date(2026, 10, 24)
    r = regra(especiais=(DiaEspecial(data=sabado, tipo="trabalho_excepcional", nome="P", periodos=(("08:00", "12:00"),)),))
    assert minutos_do_usuario_no_dia(r, sabado, SEM_CONFIGURACAO) == 240


def test_trabalho_excepcional_com_jornada_individual_e_interseccao_nunca_expande() -> None:
    quarta = date(2026, 10, 21)
    r = regra(especiais=(DiaEspecial(data=quarta, tipo="trabalho_excepcional", nome="Extra", periodos=(("09:00", "18:00"),)),))
    cfg = ConfiguracaoCapacidade(jornada=seg_a_sex((("09:00", "15:00"),)))
    assert periodos_do_usuario_no_dia(r, quarta, cfg) == (("09:00", "15:00"),)  # não vai a 18h
    assert minutos_do_usuario_no_dia(r, quarta, cfg) == 360
    # jornada sem período naquele dia da semana → 0, mesmo com trabalho excepcional
    so_segunda = ConfiguracaoCapacidade(jornada=jornada({0: SEIS_HORAS}))
    assert minutos_do_usuario_no_dia(r, quarta, so_segunda) == 0
    # sábado excepcional e jornada com sábado fechado → 0 (a jornada é o limite)
    sabado = date(2026, 10, 24)
    r2 = regra(especiais=(DiaEspecial(data=sabado, tipo="trabalho_excepcional", nome="P", periodos=(("08:00", "12:00"),)),))
    assert minutos_do_usuario_no_dia(r2, sabado, ConfiguracaoCapacidade(jornada=seg_a_sex(SEIS_HORAS))) == 0


def test_ausencia_vence_o_trabalho_excepcional() -> None:
    sabado = date(2026, 10, 24)
    r = regra(especiais=(DiaEspecial(data=sabado, tipo="trabalho_excepcional", nome="P", periodos=(("08:00", "12:00"),)),))
    assert minutos_do_usuario_no_dia(r, sabado, ConfiguracaoCapacidade(dias_ausentes=frozenset({sabado}))) == 0


def test_dia_especial_ignorado_ou_inativo_nao_interfere() -> None:
    r = regra(
        especiais=(
            DiaEspecial(data=SEG, tipo="ignorado", nome="x"),
            DiaEspecial(data=SEG + timedelta(days=1), tipo="feriado", nome="inativo", ativo=False),
        )
    )
    cfg = ConfiguracaoCapacidade(jornada=seg_a_sex(SEIS_HORAS))
    assert minutos_do_usuario_no_dia(r, SEG, cfg) == 360
    assert minutos_do_usuario_no_dia(r, SEG + timedelta(days=1), cfg) == 360


# ── percentual alocável ──────────────────────────────────────────────────────────────────────────────────────────


def test_percentual_se_aplica_por_ultimo_sobre_o_nominal_individual() -> None:
    cfg = ConfiguracaoCapacidade(jornada=seg_a_sex(SEIS_HORAS))  # 6h × 5 = 30h
    cap = obter_capacidade_usuario("a", semana(), regra=regra(), percentual_alocavel=75, configuracao=cfg)
    assert cap.nominal_min == 1800 and cap.alocavel_min == 1350  # 22h30
    # arredondamento idêntico ao atual (meio para cima, inteiros)
    um_minuto = ConfiguracaoCapacidade(jornada=jornada({0: (("09:00", "09:01"),)}))
    assert obter_capacidade_usuario("a", semana(), regra=regra(), percentual_alocavel=50, configuracao=um_minuto).alocavel_min == 1


# ── Carga: só o denominador muda ─────────────────────────────────────────────────────────────────────────────────


def _etapa(i: int, est: int, ini: date, fim: date, users: tuple[str, ...]) -> EtapaEntrada:
    return EtapaEntrada(
        etapa_id=f"e{i}", demanda_id=f"d{i}", etapa_nome=f"Etapa {i}", etapa_tipo="execucao", ordem=1, estimativa_min=est,
        planejado_inicio=ini, planejado_fim=fim, usuario_ids=users, departamento_ids=(),
    )


PESSOAS = [PessoaElegivel("a", "Ana", "dep1"), PessoaElegivel("b", "Bia", "dep1"), PessoaElegivel("c", "Caio", "dep1")]


def test_carga_capacidades_diferentes_e_planejamento_identico() -> None:
    # A = 40h (padrão), B = 30h (jornada 6h), C = 40h mas com 5 dias de férias (0h)
    configs = {
        "b": ConfiguracaoCapacidade(jornada=seg_a_sex(SEIS_HORAS)),
        "c": ConfiguracaoCapacidade(dias_ausentes=dias_ausentes_da_semana([(SEG, SEG + timedelta(days=4))], semana())),
    }
    etapas = [
        _etapa(1, 241, SEG, SEG2 + timedelta(days=4), ("a", "b")),
        _etapa(2, 600, SEG, SEG + timedelta(days=4), ("c",)),
    ]
    base = calcular_carga(etapas=etapas, pessoas=PESSOAS, regra=regra(), percentual_alocavel=100, hoje=SEG, semana_inicio=SEG)
    com = calcular_carga(etapas=etapas, pessoas=PESSOAS, regra=regra(), percentual_alocavel=100, hoje=SEG, semana_inicio=SEG, configuracoes=configs)
    assert {i: c.nominal_min for i, c in com.capacidades.items()} == {"a": 2400, "b": 1800, "c": 0}
    assert {i: c.nominal_min for i, c in base.capacidades.items()} == {"a": 2400, "b": 2400, "c": 2400}
    # o PLANEJAMENTO é idêntico: mesma divisão entre responsáveis, mesma distribuição por semana, mesmos agregados
    assert {i: a.planejado_min for i, a in com.pessoas.items()} == {i: a.planejado_min for i, a in base.pessoas.items()}
    assert [(e.entrada.etapa_id, e.planejado_semana_min, e.divisao_semana, e.alocacao_estado) for e in com.etapas] == [
        (e.entrada.etapa_id, e.planejado_semana_min, e.divisao_semana, e.alocacao_estado) for e in base.etapas
    ]
    # departamento = soma real das pessoas (40h + 30h + 0h = 70h), não "3 × capacidade padrão"
    assert sum(c.alocavel_min for c in com.capacidades.values()) == 2400 + 1800 + 0


def test_carga_semana_atual_recortada_ignora_ausencia_em_dia_anterior_a_hoje() -> None:
    quarta = SEG + timedelta(days=2)
    ausente_seg_ter = ConfiguracaoCapacidade(dias_ausentes=dias_ausentes_da_semana([(SEG, SEG + timedelta(days=1))], semana()))
    r = calcular_carga(etapas=[], pessoas=PESSOAS[:1], regra=regra(), percentual_alocavel=100, hoje=quarta, semana_inicio=SEG, configuracoes={"a": ausente_seg_ter})
    assert r.capacidades["a"].nominal_min == 3 * 480  # qua, qui, sex — a ausência de seg/ter já passou
    assert r.capacidades["a"].dias_ausentes == 0
    ausente_qui = ConfiguracaoCapacidade(dias_ausentes=frozenset({SEG + timedelta(days=3)}))
    r2 = calcular_carga(etapas=[], pessoas=PESSOAS[:1], regra=regra(), percentual_alocavel=100, hoje=quarta, semana_inicio=SEG, configuracoes={"a": ausente_qui})
    assert r2.capacidades["a"].nominal_min == 2 * 480 and r2.capacidades["a"].dias_ausentes == 1


def test_expediente_da_empresa_desligado_ignora_jornada_individual() -> None:
    cfg = {"a": ConfiguracaoCapacidade(jornada=seg_a_sex(SEIS_HORAS))}
    r = calcular_carga(etapas=[], pessoas=PESSOAS, regra=regra(ativo=False), percentual_alocavel=100, hoje=SEG, semana_inicio=SEG, configuracoes=cfg)
    assert r.capacidade_indisponivel == "expediente_desligado" and r.capacidades == {}


@pytest.mark.parametrize("pct", [100, 75, 50])
def test_sem_configuracoes_o_resultado_e_o_da_v1(pct: int) -> None:
    etapas = [_etapa(1, 300, SEG, SEG2, ("a", "b"))]
    antigo = calcular_carga(etapas=etapas, pessoas=PESSOAS, regra=regra(), percentual_alocavel=pct, hoje=SEG, semana_inicio=SEG)
    vazio = calcular_carga(etapas=etapas, pessoas=PESSOAS, regra=regra(), percentual_alocavel=pct, hoje=SEG, semana_inicio=SEG, configuracoes={})
    assert antigo.capacidades == vazio.capacidades
    assert all(c.origem == "empresa" and c.dias_ausentes == 0 for c in antigo.capacidades.values())
