"""Fase Expediente 2 — núcleo PURO: janelas de acesso/trabalho, quem está sujeito e o corte do logout automático. Relógio injetado (nunca o do sistema).

Exemplo oficial: 09:00–12:00 e 13:00–18:00, antecedência de acesso 30 min, logout automático 18:10, tolerância legada 30 (que NÃO vale mais para trabalho).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core.expediente import (
    DiaEspecial,
    JanelaDia,
    RegraExpediente,
    avaliar_expediente,
    esta_dentro_janela_acesso,
    esta_dentro_janela_trabalho,
    janela_de_periodos,
    proximo_periodo_trabalho,
    sessao_encerrada_por_logout_automatico,
    ultimo_corte_logout,
    usuario_sujeito_ao_expediente,
)

SP = ZoneInfo("America/Sao_Paulo")
SEGUNDA = date(2026, 10, 5)  # segunda-feira
UTIL = (("09:00", "12:00"), ("13:00", "18:00"))


def _regra(**extra) -> RegraExpediente:
    dias = {d: janela_de_periodos(UTIL if d < 5 else []) for d in range(7)}
    base = dict(
        ativo=True,
        tolerancia_retomada_minutos=30,
        dias=dias,
        antecedencia_acesso_minutos=30,
        timezone="America/Sao_Paulo",
        bloquear_fora_expediente=True,
        logout_automatico_ativo=True,
        logout_horario="18:10",
    )
    base.update(extra)
    return RegraExpediente(**base)


def _em(hhmm: str, dia: date = SEGUNDA) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(dia.year, dia.month, dia.day, h, m, tzinfo=SP)


# ── acesso × trabalho (exemplo oficial) ──────────────────────────────────────────────────────────────────────────

# (hora, acesso, trabalho)
MATRIZ = [
    ("08:29", False, False),
    ("08:30", True, False),
    ("08:59", True, False),
    ("09:00", True, True),
    ("11:59", True, True),
    ("12:00", False, False),
    ("12:29", False, False),
    ("12:30", True, False),
    ("12:59", True, False),
    ("13:00", True, True),
    ("17:59", True, True),
    ("18:00", False, False),
    ("18:09", False, False),
    ("18:10", False, False),
    ("18:11", False, False),
]


@pytest.mark.parametrize("hora, acesso, trabalho", MATRIZ)
def test_matriz_de_acesso_e_trabalho_do_exemplo_oficial(hora: str, acesso: bool, trabalho: bool) -> None:
    regra = _regra()
    assert esta_dentro_janela_acesso(_em(hora), regra=regra) is acesso
    assert esta_dentro_janela_trabalho(_em(hora), regra=regra) is trabalho


@pytest.mark.parametrize("hora, acesso, trabalho", MATRIZ)
def test_avaliacao_do_operador_sujeito_segue_a_matriz(hora: str, acesso: bool, trabalho: bool) -> None:
    av = avaliar_expediente(_em(hora), regra=_regra(), sujeito=True)
    assert av.acesso_permitido is acesso
    assert av.trabalho_permitido is trabalho


def test_a_tolerancia_legada_nao_e_mais_autoridade_de_trabalho() -> None:
    """Às 12:30 o gate ANTIGO (com tolerância 30) aceitava a entrada; a janela de trabalho NÃO. Ele continua existindo só como função legada."""
    from app.core.expediente import esta_dentro_expediente

    regra = _regra()
    assert esta_dentro_expediente(_em("12:30"), regra=regra) is True  # legado, preservado e deprecated
    assert esta_dentro_janela_trabalho(_em("12:30"), regra=regra) is False
    assert avaliar_expediente(_em("12:30"), regra=regra, sujeito=True).trabalho_permitido is False
    assert avaliar_expediente(_em("13:00"), regra=regra, sujeito=True).trabalho_permitido is True


def test_bloqueio_desligado_nunca_nega_acesso_mas_o_trabalho_segue_a_janela() -> None:
    regra = _regra(bloquear_fora_expediente=False)
    av = avaliar_expediente(_em("03:00"), regra=regra, sujeito=True)
    assert av.acesso_permitido is True and av.bloqueio_ativo is False
    assert av.trabalho_permitido is False  # o gate de TRABALHO é independente do bloqueio de acesso


def test_regra_desligada_libera_tudo() -> None:
    regra = _regra(ativo=False)
    av = avaliar_expediente(_em("03:00"), regra=regra, sujeito=True)
    assert av.acesso_permitido and av.trabalho_permitido and not av.bloqueio_ativo
    assert ultimo_corte_logout(_em("19:00"), regra=regra) is None  # logout também depende da chave-mestra


def test_isento_nunca_e_bloqueado() -> None:
    av = avaliar_expediente(_em("03:00"), regra=_regra(), sujeito=False)
    assert av.acesso_permitido and av.trabalho_permitido
    assert av.proximo_acesso is None and av.proximo_trabalho is None


def test_proximos_horarios_no_fuso_da_empresa() -> None:
    regra = _regra()
    antes = avaliar_expediente(_em("12:10"), regra=regra, sujeito=True)
    assert antes.proximo_acesso == _em("12:30")
    assert antes.proximo_trabalho == _em("13:00") and antes.proximo_trabalho_fim == _em("18:00")
    assert antes.timezone == "America/Sao_Paulo"
    # sexta 18:30 → segunda 08:30 / 09:00–12:00
    sexta = date(2026, 10, 9)
    noite = avaliar_expediente(_em("18:30", sexta), regra=regra, sujeito=True)
    assert noite.proximo_acesso == _em("08:30", date(2026, 10, 12))
    assert (noite.proximo_trabalho, noite.proximo_trabalho_fim) == (_em("09:00", date(2026, 10, 12)), _em("12:00", date(2026, 10, 12)))


def test_no_intervalo_de_acesso_o_proximo_periodo_de_trabalho_e_o_que_vai_comecar() -> None:
    inicio, fim = proximo_periodo_trabalho(_em("12:45"), regra=_regra())  # type: ignore[misc]
    assert (inicio, fim) == (_em("13:00"), _em("18:00"))


def test_relogio_e_decidido_no_fuso_da_regra_nao_no_do_instante_recebido() -> None:
    regra = _regra()
    utc = _em("08:29").astimezone(ZoneInfo("UTC"))
    assert esta_dentro_janela_acesso(utc, regra=regra) is False
    assert esta_dentro_janela_acesso(_em("08:30").astimezone(ZoneInfo("UTC")), regra=regra) is True
    outro_fuso = _regra(timezone="America/Manaus")  # UTC-4: o mesmo instante é uma hora MAIS CEDO no relógio local
    assert esta_dentro_janela_trabalho(_em("09:00"), regra=outro_fuso) is False


# ── dias especiais ───────────────────────────────────────────────────────────────────────────────────────────────


def test_feriado_ativo_fecha_acesso_e_trabalho() -> None:
    regra = _regra(dias_especiais=(DiaEspecial(data=SEGUNDA, tipo="feriado", nome="X"),))
    assert esta_dentro_janela_acesso(_em("10:00"), regra=regra) is False
    assert esta_dentro_janela_trabalho(_em("10:00"), regra=regra) is False


def test_trabalho_excepcional_usa_periodos_proprios_no_sabado() -> None:
    sabado = date(2026, 10, 10)
    regra = _regra(dias_especiais=(DiaEspecial(data=sabado, tipo="trabalho_excepcional", periodos=(("10:00", "14:00"),)),))
    assert esta_dentro_janela_acesso(_em("09:30", sabado), regra=regra) is True
    assert esta_dentro_janela_trabalho(_em("09:30", sabado), regra=regra) is False
    assert esta_dentro_janela_trabalho(_em("10:00", sabado), regra=regra) is True


def test_dia_especial_ignorado_neutraliza_o_feriado_automatico() -> None:
    regra = _regra(
        dias_especiais=(
            DiaEspecial(data=SEGUNDA, tipo="feriado", origem="automatico"),
            DiaEspecial(data=SEGUNDA, tipo="ignorado", origem="manual"),
        )
    )
    assert esta_dentro_janela_trabalho(_em("10:00"), regra=regra) is True


def test_feriado_inativo_nao_conta() -> None:
    regra = _regra(dias_especiais=(DiaEspecial(data=SEGUNDA, tipo="feriado", ativo=False),))
    assert esta_dentro_janela_trabalho(_em("10:00"), regra=regra) is True


# ── quem está sujeito ────────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "perfil, sistema, override, esperado",
    [
        ("operador", False, False, True),
        ("operador", False, True, False),
        ("operador", True, False, False),
        ("gestor", False, False, False),
        ("admin", False, False, False),
        ("admin", True, False, False),
    ],
)
def test_quem_esta_sujeito(perfil: str, sistema: bool, override: bool, esperado: bool) -> None:
    assert usuario_sujeito_ao_expediente(perfil_base=perfil, is_system_account=sistema, acesso_fora_expediente=override) is esperado


# ── logout automático ────────────────────────────────────────────────────────────────────────────────────────────


def test_corte_do_logout_e_o_mais_recente_que_ja_passou() -> None:
    regra = _regra()
    assert ultimo_corte_logout(_em("18:09"), regra=regra) == _em("18:10", SEGUNDA - timedelta(days=1))
    assert ultimo_corte_logout(_em("18:10"), regra=regra) == _em("18:10")
    assert ultimo_corte_logout(_em("23:59"), regra=regra) == _em("18:10")
    assert ultimo_corte_logout(_em("03:00"), regra=regra) == _em("18:10", SEGUNDA - timedelta(days=1))


def test_logout_desligado_ou_sem_horario_nao_tem_corte() -> None:
    assert ultimo_corte_logout(_em("19:00"), regra=_regra(logout_automatico_ativo=False)) is None
    assert ultimo_corte_logout(_em("19:00"), regra=_regra(logout_horario=None)) is None


def test_logout_nao_deriva_do_fim_do_ultimo_periodo() -> None:
    """O horário é PRÓPRIO: às 18:00 (fim do último período) ninguém é deslogado; só a partir de 18:10."""
    regra = _regra()
    assert sessao_encerrada_por_logout_automatico(_em("15:00"), _em("18:00"), regra=regra) is False
    assert sessao_encerrada_por_logout_automatico(_em("15:00"), _em("18:09"), regra=regra) is False
    assert sessao_encerrada_por_logout_automatico(_em("15:00"), _em("18:10"), regra=regra) is True
    assert sessao_encerrada_por_logout_automatico(_em("15:00"), _em("18:11"), regra=regra) is True


def test_token_emitido_no_corte_ou_depois_segue_valendo() -> None:
    regra = _regra()
    assert sessao_encerrada_por_logout_automatico(_em("18:10"), _em("18:11"), regra=regra) is False
    assert sessao_encerrada_por_logout_automatico(_em("18:11"), _em("20:00"), regra=regra) is False
    # a resolução do `iat` é de segundos: emitido às 18:09:59 já cai antes do corte
    assert sessao_encerrada_por_logout_automatico(_em("18:09") + timedelta(seconds=59), _em("18:10"), regra=regra) is True


def test_token_de_ontem_nao_sobrevive_ao_corte_de_ontem() -> None:
    regra = _regra()
    ontem = SEGUNDA - timedelta(days=1)
    assert sessao_encerrada_por_logout_automatico(_em("15:00", ontem), _em("08:00"), regra=regra) is True
    assert sessao_encerrada_por_logout_automatico(_em("18:11", ontem), _em("08:00"), regra=regra) is False


def test_iat_epoch_do_jwt_e_aceito() -> None:
    regra = _regra()
    assert sessao_encerrada_por_logout_automatico(int(_em("15:00").timestamp()), _em("18:10"), regra=regra) is True


def test_logout_usa_o_fuso_da_regra() -> None:
    regra = _regra(timezone="America/Manaus")  # 18:10 em Manaus = 19:10 em São Paulo
    manaus = ZoneInfo("America/Manaus")
    agora = datetime(2026, 10, 5, 18, 10, tzinfo=manaus)
    assert sessao_encerrada_por_logout_automatico(datetime(2026, 10, 5, 15, 0, tzinfo=manaus), agora, regra=regra) is True
    assert sessao_encerrada_por_logout_automatico(datetime(2026, 10, 5, 15, 0, tzinfo=manaus), _em("18:10"), regra=regra) is False


def test_dto_sem_logout_mantem_o_comportamento_antigo() -> None:
    legado = RegraExpediente(ativo=True, tolerancia_retomada_minutos=0, dias={d: JanelaDia(ativo=False) for d in range(7)})
    assert legado.logout_automatico_ativo is False and legado.logout_horario is None
    assert ultimo_corte_logout(_em("20:00"), regra=legado) is None
