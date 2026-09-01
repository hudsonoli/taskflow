"""Testes de app/core/calculadora_expediente.py (Fase 2G.6C) — cálculo puro, sem DB.

Datas fixas (confirmadas via `datetime.weekday()`):
sexta=2026-08-28, sábado=2026-08-29, domingo=2026-08-30, segunda=2026-08-31, terça=2026-09-01.

`REGRA_ATIVA` é `REGRA_PADRAO` (app/core/expediente.py): segunda-sexta 09-12/14-19,
sábado/domingo inativos — mesmos horários usados nos exemplos do kickoff da 2G.6C."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.calculadora_expediente import (
    SlaCalculoInvalidoError,
    SlaExpedienteSemJanelaUtilError,
    calcular_data_limite,
)
from app.core.expediente import REGRA_PADRAO, JanelaDia, RegraExpediente
from app.core.relogio import fuso_aplicacao

REGRA_ATIVA = REGRA_PADRAO


def _dt(ano: int, mes: int, dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(ano, mes, dia, hora, minuto, tzinfo=fuso_aplicacao())


def _regra_gate_desabilitado() -> RegraExpediente:
    return RegraExpediente(ativo=False, tolerancia_retomada_minutos=30, dias=REGRA_ATIVA.dias)


# --------------------------------------------------------------------------------------
# dias_corridos (item 17, 33) — nunca olha expediente
# --------------------------------------------------------------------------------------


def test_dias_corridos_soma_calendario_ignorando_fim_de_semana() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 28, 18, 30), 2, "dias_corridos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 30, 18, 30)  # domingo


def test_dias_corridos_ignora_flag_e_gate_desabilitado() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 28, 18, 30), 2, "dias_corridos", False, _regra_gate_desabilitado())
    assert resultado == _dt(2026, 8, 30, 18, 30)


# --------------------------------------------------------------------------------------
# minutos/horas sem expediente (item 11) e com gate desabilitado (item 16, 32)
# --------------------------------------------------------------------------------------


def test_minutos_horas_sem_expediente_soma_corrido_sem_pular_nada() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 28, 18, 30), 2, "horas", False, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 28, 20, 30)


def test_gate_desabilitado_soma_corrido_mesmo_pedindo_expediente() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 28, 18, 30), 2, "horas", True, _regra_gate_desabilitado())
    assert resultado == _dt(2026, 8, 28, 20, 30)


# --------------------------------------------------------------------------------------
# minutos/horas com expediente (item 12, 31)
# --------------------------------------------------------------------------------------


def test_dentro_da_manha() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 31, 9, 30), 1, "horas", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 10, 30)


def test_atravessa_fim_da_manha_pula_almoco_para_tarde() -> None:
    # item 36 do kickoff: segunda 11:30 + 2h úteis -> 15:30
    resultado = calcular_data_limite(_dt(2026, 8, 31, 11, 30), 2, "horas", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 15, 30)


def test_dentro_da_tarde() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 31, 15, 0), 1, "horas", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 16, 0)


def test_atravessa_fim_do_dia_sexta_para_segunda() -> None:
    # item 12 do kickoff: sexta 18:30, expediente termina 19:00, prazo 2h -> segunda 10:30
    resultado = calcular_data_limite(_dt(2026, 8, 28, 18, 30), 2, "horas", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 10, 30)


def test_comeca_antes_do_expediente_avanca_para_abertura() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 31, 8, 0), 30, "minutos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 9, 30)


def test_comeca_no_almoco_avanca_para_tarde() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 31, 12, 30), 30, "minutos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 14, 30)


def test_comeca_depois_do_expediente_avanca_proximo_dia() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 31, 20, 0), 30, "minutos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 9, 1, 9, 30)  # terça


def test_comeca_sabado_avanca_para_segunda() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 29, 10, 0), 30, "minutos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 9, 30)


def test_comeca_domingo_avanca_para_segunda() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 30, 10, 0), 30, "minutos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 9, 30)


def test_multiplos_dias() -> None:
    # segunda 09:00 + 16h úteis: consome os 8h úteis de segunda (3h manhã + 5h tarde) e mais
    # 8h de terça, terminando exatamente às 19:00 de terça.
    resultado = calcular_data_limite(_dt(2026, 8, 31, 9, 0), 16, "horas", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 9, 1, 19, 0)


# --------------------------------------------------------------------------------------
# dias_uteis (item 18, 34)
# --------------------------------------------------------------------------------------


def test_dias_uteis_sexta_mais_1_vai_para_segunda() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 28, 10, 0), 1, "dias_uteis", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 10, 0)


def test_dias_uteis_sexta_mais_2_vai_para_terca() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 28, 10, 0), 2, "dias_uteis", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 9, 1, 10, 0)


def test_dias_uteis_pula_dia_semanal_customizado_desativado() -> None:
    dias = dict(REGRA_ATIVA.dias)
    dias[1] = JanelaDia(ativo=False)  # terça desativada nesta Empresa
    regra_custom = RegraExpediente(ativo=True, tolerancia_retomada_minutos=30, dias=dias)
    resultado = calcular_data_limite(_dt(2026, 8, 31, 10, 0), 1, "dias_uteis", True, regra_custom)  # segunda
    assert resultado == _dt(2026, 9, 2, 10, 0)  # pula terça, cai na quarta


def test_dias_uteis_gate_desabilitado_vira_dias_corridos() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 28, 10, 0), 1, "dias_uteis", True, _regra_gate_desabilitado())
    assert resultado == _dt(2026, 8, 29, 10, 0)  # sábado, sem pular (corrido)


# --------------------------------------------------------------------------------------
# timezone (item 20, 21, 35)
# --------------------------------------------------------------------------------------


def test_resultado_e_aware_no_fuso_da_aplicacao() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 28, 18, 30), 2, "horas", True, REGRA_ATIVA)
    assert resultado.tzinfo is not None
    assert resultado.utcoffset() is not None
    assert resultado.tzinfo.key == fuso_aplicacao().key


def test_aceita_inicio_em_outro_timezone_normaliza_para_app() -> None:
    inicio_utc = _dt(2026, 8, 28, 18, 30).astimezone(timezone.utc)
    resultado = calcular_data_limite(inicio_utc, 2, "horas", True, REGRA_ATIVA)
    esperado = calcular_data_limite(_dt(2026, 8, 28, 18, 30), 2, "horas", True, REGRA_ATIVA)
    assert resultado == esperado


def test_recusa_inicio_naive() -> None:
    with pytest.raises(SlaCalculoInvalidoError):
        calcular_data_limite(datetime(2026, 8, 28, 18, 30), 2, "horas", True, REGRA_ATIVA)


# --------------------------------------------------------------------------------------
# limites de janela — início inclusivo, fim exclusivo (item 37)
# --------------------------------------------------------------------------------------


def test_inicio_exatamente_09h00_e_inclusivo() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 31, 9, 0), 30, "minutos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 9, 30)


def test_inicio_exatamente_12h00_e_fora_pula_para_tarde() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 31, 12, 0), 30, "minutos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 14, 30)


def test_inicio_exatamente_14h00_e_inclusivo() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 31, 14, 0), 30, "minutos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 8, 31, 14, 30)


def test_inicio_exatamente_19h00_e_fora_pula_para_proximo_dia() -> None:
    resultado = calcular_data_limite(_dt(2026, 8, 31, 19, 0), 30, "minutos", True, REGRA_ATIVA)
    assert resultado == _dt(2026, 9, 1, 9, 30)


# --------------------------------------------------------------------------------------
# proteção contra loop (item 38, 39)
# --------------------------------------------------------------------------------------


def test_nenhum_dia_ativo_levanta_erro_claro_para_horas() -> None:
    regra_sem_dia_ativo = RegraExpediente(
        ativo=True, tolerancia_retomada_minutos=30, dias={dia: JanelaDia(ativo=False) for dia in range(7)}
    )
    with pytest.raises(SlaExpedienteSemJanelaUtilError):
        calcular_data_limite(_dt(2026, 8, 31, 10, 0), 1, "horas", True, regra_sem_dia_ativo)


def test_nenhum_dia_ativo_levanta_erro_claro_para_dias_uteis() -> None:
    regra_sem_dia_ativo = RegraExpediente(
        ativo=True, tolerancia_retomada_minutos=30, dias={dia: JanelaDia(ativo=False) for dia in range(7)}
    )
    with pytest.raises(SlaExpedienteSemJanelaUtilError):
        calcular_data_limite(_dt(2026, 8, 31, 10, 0), 1, "dias_uteis", True, regra_sem_dia_ativo)


def test_dia_ativo_sem_nenhuma_janela_levanta_erro_claro() -> None:
    regra_sem_janela = RegraExpediente(
        ativo=True, tolerancia_retomada_minutos=30, dias={dia: JanelaDia(ativo=True) for dia in range(7)}
    )
    with pytest.raises(SlaExpedienteSemJanelaUtilError):
        calcular_data_limite(_dt(2026, 8, 31, 10, 0), 1, "horas", True, regra_sem_janela)


# --------------------------------------------------------------------------------------
# validação de entrada (item 19)
# --------------------------------------------------------------------------------------


def test_quantidade_zero_rejeitada() -> None:
    with pytest.raises(SlaCalculoInvalidoError):
        calcular_data_limite(_dt(2026, 8, 31, 10, 0), 0, "horas", True, REGRA_ATIVA)


def test_quantidade_negativa_rejeitada() -> None:
    with pytest.raises(SlaCalculoInvalidoError):
        calcular_data_limite(_dt(2026, 8, 31, 10, 0), -5, "minutos", True, REGRA_ATIVA)


def test_unidade_desconhecida_rejeitada() -> None:
    with pytest.raises(SlaCalculoInvalidoError):
        calcular_data_limite(_dt(2026, 8, 31, 10, 0), 5, "semanas", True, REGRA_ATIVA)
