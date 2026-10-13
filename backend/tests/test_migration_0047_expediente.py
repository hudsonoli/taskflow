"""Upgrade/downgrade da 0047 (Expediente — fundação) em PostgreSQL scratch, sem acessar DEV.

Prova: (1) os horários atuais viram períodos SEM deslocar nenhum horário; (2) a tolerância legada NÃO é convertida (continua honrada pelo gate atual); (3) as flags
críticas nascem FALSAS; (4) o gate de entrada em execução responde IGUAL, minuto a minuto, antes e depois; (5) o downgrade devolve o legado idêntico.
"""
import uuid
from datetime import datetime, time, timedelta
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from app.core.expediente import JanelaDia, RegraExpediente, esta_dentro_expediente, janela_de_periodos
from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0043_workflow_etapa import _semear_base

ANTERIOR = "f2c6a9d41b87"
NOVA = "a3c8e5f17d24"


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0047_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0047_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _regra(c, regra_id: str, empresa_id: str, *, ativo: bool, tolerancia: int, dias: dict[int, tuple[str, str, str, str] | None]) -> None:
    c.execute(
        "INSERT INTO regra_expediente (id, empresa_id, ativo, tolerancia_retomada_minutos, created_at, updated_at) VALUES (%s, %s, %s, %s, now(), now())",
        (regra_id, empresa_id, ativo, tolerancia),
    )
    for dia in range(7):
        horarios = dias.get(dia)
        c.execute(
            "INSERT INTO regra_expediente_dias (id, regra_expediente_id, dia_semana, ativo, manha_inicio, manha_fim, tarde_inicio, tarde_fim) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (f"{regra_id}-d{dia}", regra_id, dia, horarios is not None, *(horarios or (None, None, None, None))),
        )


def _semear(c) -> None:
    _semear_base(c)
    c.execute(
        "INSERT INTO empresas (id, nome, codigo_interno, slug, status, created_at, updated_at) VALUES ('emp-b', 'Empresa B', 'EMPB', 'empb', 'ativa', now(), now())"
    )
    # emp-a = a configuração REAL da produção (seg–sex 09–12/13–18, tolerância 30, fim de semana fechado)
    _regra(c, "r-a", "emp-a", ativo=True, tolerancia=30, dias={d: ("09:00", "12:00", "13:00", "18:00") for d in range(5)})
    # emp-b = variação: sábado aberto com períodos encostados, sem tolerância, controle mestre desligado
    _regra(c, "r-b", "emp-b", ativo=False, tolerancia=0, dias={**{d: ("08:00", "12:00", "13:30", "17:30") for d in range(5)}, 5: ("08:00", "12:00", "12:00", "16:00")})
    c.execute("UPDATE demandas SET status = 'pausada' WHERE id = 'd-2'")


def _legado(c, regra_id: str) -> list:
    return c.execute(
        "SELECT dia_semana, ativo, manha_inicio, manha_fim, tarde_inicio, tarde_fim FROM regra_expediente_dias WHERE regra_expediente_id = %s ORDER BY dia_semana",
        (regra_id,),
    ).fetchall()


def _dto_antigo(c, regra_id: str) -> RegraExpediente:
    regra = c.execute("SELECT ativo, tolerancia_retomada_minutos FROM regra_expediente WHERE id = %s", (regra_id,)).fetchone()
    dias = {
        dia: JanelaDia(ativo=ativo, manha_inicio=_hhmm(mi), manha_fim=_hhmm(mf), tarde_inicio=_hhmm(ti), tarde_fim=_hhmm(tf))
        for dia, ativo, mi, mf, ti, tf in _legado(c, regra_id)
    }
    return RegraExpediente(ativo=regra[0], tolerancia_retomada_minutos=regra[1], dias=dias)


def _dto_novo(c, regra_id: str) -> RegraExpediente:
    regra = c.execute("SELECT ativo, tolerancia_retomada_minutos, timezone, antecedencia_acesso_minutos FROM regra_expediente WHERE id = %s", (regra_id,)).fetchone()
    periodos = c.execute("SELECT dia_semana, inicio, fim FROM regra_expediente_periodos WHERE regra_expediente_id = %s ORDER BY dia_semana, ordem", (regra_id,)).fetchall()
    dias = {dia: janela_de_periodos([(_hhmm(i), _hhmm(f)) for d, i, f in periodos if d == dia]) for dia in range(7)}
    return RegraExpediente(ativo=regra[0], tolerancia_retomada_minutos=regra[1], dias=dias, timezone=regra[2], antecedencia_acesso_minutos=regra[3])


def _hhmm(valor: time | None) -> str | None:
    return None if valor is None else valor.strftime("%H:%M")


def test_upgrade_copia_horarios_sem_deslocar_nem_converter_tolerancia(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        legado_a, legado_b = _legado(c, "r-a"), _legado(c, "r-b")
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr

    with scratch.conectar() as c:
        # períodos = cópia fiel (manhã → 1, tarde → 2), só de dias ativos
        periodos_a = c.execute("SELECT dia_semana, ordem, inicio, fim FROM regra_expediente_periodos WHERE regra_expediente_id = 'r-a' ORDER BY dia_semana, ordem").fetchall()
        assert len(periodos_a) == 10
        assert periodos_a[0] == (0, 1, time(9, 0), time(12, 0)) and periodos_a[1] == (0, 2, time(13, 0), time(18, 0))
        assert {d for d, *_ in periodos_a} == {0, 1, 2, 3, 4}  # sábado e domingo continuam fechados
        sabado_b = c.execute("SELECT ordem, inicio, fim FROM regra_expediente_periodos WHERE regra_expediente_id = 'r-b' AND dia_semana = 5 ORDER BY ordem").fetchall()
        assert sabado_b == [(1, time(8, 0), time(12, 0)), (2, time(12, 0), time(16, 0))]
        # a tolerância legada NÃO foi convertida nem somada aos períodos
        assert c.execute("SELECT id, tolerancia_retomada_minutos FROM regra_expediente ORDER BY id").fetchall() == [("r-a", 30), ("r-b", 0)]
        # o legado ficou intacto (expand sem contract)
        assert _legado(c, "r-a") == legado_a and _legado(c, "r-b") == legado_b
        # flags críticas nascem FALSAS; antecedência 30; fuso preenchido; feriados automáticos desligados
        for linha in c.execute("SELECT bloquear_fora_expediente, pausar_no_fim_periodo, antecedencia_acesso_minutos, timezone, feriados_automaticos FROM regra_expediente").fetchall():
            assert linha[0] is False and linha[1] is False and linha[2] == 30 and linha[4] is False
            assert linha[3] == "America/Sao_Paulo"
        # a master `ativo` de cada empresa é preservada
        assert c.execute("SELECT id, ativo FROM regra_expediente ORDER BY id").fetchall() == [("r-a", True), ("r-b", False)]
        # usuário: isenção nasce FALSE; demanda: pausa legada ganha origem 'manual' (nunca existiu pausa automática), instante desconhecido
        assert c.execute("SELECT acesso_fora_expediente FROM usuarios").fetchall() == [(False,)]
        assert c.execute("SELECT id, pausa_origem, pausada_em FROM demandas ORDER BY id").fetchall() == [("d-1", None, None), ("d-2", "manual", None)]
        # nada de dia especial
        assert c.execute("SELECT count(*) FROM regra_expediente_dias_especiais").fetchone() == (0,)


def test_o_gate_de_entrada_responde_igual_antes_e_depois_minuto_a_minuto(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        antigo = {r: _dto_antigo(c, r) for r in ("r-a", "r-b")}
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        novo = {r: _dto_novo(c, r) for r in ("r-a", "r-b")}
    segunda = datetime(2026, 10, 12)
    for regra_id in ("r-a", "r-b"):
        for minuto in range(7 * 24 * 60):
            momento = segunda + timedelta(minutes=minuto)
            assert esta_dentro_expediente(momento, regra=novo[regra_id]) is esta_dentro_expediente(momento, regra=antigo[regra_id]), (regra_id, momento)


def test_constraints_novas_e_o_check_antigo_removido(scratch) -> None:
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        _semear_base(c)
        _regra(c, "r-x", "emp-a", ativo=True, tolerancia=0, dias={})
        # o CHECK antigo (4 horários obrigatórios em dia ativo) caiu: dia ativo sem horários legados é aceito
        c.execute("UPDATE regra_expediente_dias SET ativo = true WHERE id = 'r-x-d0'")
        c.execute("INSERT INTO regra_expediente_periodos (id, regra_expediente_id, dia_semana, ordem, inicio, fim) VALUES ('p1', 'r-x', 0, 1, '08:00', '12:00')")
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("INSERT INTO regra_expediente_periodos (id, regra_expediente_id, dia_semana, ordem, inicio, fim) VALUES ('p2', 'r-x', 0, 2, '12:00', '12:00')")
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("INSERT INTO regra_expediente_periodos (id, regra_expediente_id, dia_semana, ordem, inicio, fim) VALUES ('p3', 'r-x', 9, 1, '08:00', '09:00')")
        with pytest.raises(psycopg.errors.UniqueViolation):
            c.execute("INSERT INTO regra_expediente_periodos (id, regra_expediente_id, dia_semana, ordem, inicio, fim) VALUES ('p4', 'r-x', 0, 1, '13:00', '14:00')")
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("UPDATE regra_expediente SET antecedencia_acesso_minutos = 721")
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("UPDATE demandas SET pausa_origem = 'robo' WHERE id = 'd-1'")
        c.execute("UPDATE demandas SET pausa_origem = 'expediente' WHERE id = 'd-1'")
        base = "INSERT INTO regra_expediente_dias_especiais (id, empresa_id, regra_expediente_id, data, nome, origem, tipo, created_at, updated_at) VALUES (%s, 'emp-a', 'r-x', %s, 'X', %s, %s, now(), now())"
        c.execute(base, ("e1", "2026-10-12", "manual", "feriado"))
        c.execute(base, ("e2", "2026-10-12", "automatico", "feriado"))  # mesma data, origem diferente: coexistem
        with pytest.raises(psycopg.errors.UniqueViolation):
            c.execute(base, ("e3", "2026-10-12", "manual", "recesso"))
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute(base, ("e4", "2026-10-13", "manual", "carnaval"))
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute(base, ("e5", "2026-10-13", "robo", "feriado"))
        assert c.execute("SELECT ativo FROM regra_expediente_dias_especiais WHERE id = 'e1'").fetchone() == (True,)
        # apagar a regra leva períodos e dias especiais junto
        c.execute("INSERT INTO regra_expediente_dias_especiais_periodos (id, dia_especial_id, ordem, inicio, fim) VALUES ('ep1', 'e1', 1, '09:00', '12:00')")
        c.execute("DELETE FROM regra_expediente WHERE id = 'r-x'")
        assert c.execute("SELECT (SELECT count(*) FROM regra_expediente_periodos), (SELECT count(*) FROM regra_expediente_dias_especiais), (SELECT count(*) FROM regra_expediente_dias_especiais_periodos)").fetchone() == (0, 0, 0)


def test_downgrade_devolve_o_legado_identico_e_reaplica(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        antes = {t: c.execute(f"SELECT row_to_json(t)::text FROM {t} t ORDER BY id").fetchall() for t in ("regra_expediente", "regra_expediente_dias", "demandas", "usuarios")}
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        depois = {t: c.execute(f"SELECT row_to_json(t)::text FROM {t} t ORDER BY id").fetchall() for t in ("regra_expediente", "regra_expediente_dias")}
        assert depois["regra_expediente"] == antes["regra_expediente"]
        assert depois["regra_expediente_dias"] == antes["regra_expediente_dias"]
        for tabela in ("regra_expediente_periodos", "regra_expediente_dias_especiais", "regra_expediente_dias_especiais_periodos"):
            assert c.execute("SELECT to_regclass(%s)", (tabela,)).fetchone() == (None,)
    assert "pausa_origem" not in scratch.colunas("demandas") and "acesso_fora_expediente" not in scratch.colunas("usuarios")
    assert "timezone" not in scratch.colunas("regra_expediente")
    assert scratch.alembic("upgrade", NOVA).returncode == 0


def test_downgrade_com_configuracao_nova_reduz_para_o_legado_possivel(scratch) -> None:
    """Perda DOCUMENTADA: o legado só comporta 2 períodos. Dia com 3+ mantém os 2 primeiros; com 1 ou 0 volta inativo; o CHECK antigo é recriado e satisfeito."""
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        _semear_base(c)
        _regra(c, "r-y", "emp-a", ativo=True, tolerancia=0, dias={})
        periodos = [("r-y", 0, 1, "08:00", "10:00"), ("r-y", 0, 2, "11:00", "13:00"), ("r-y", 0, 3, "14:00", "18:00"), ("r-y", 1, 1, "08:00", "12:00"), ("r-y", 2, 1, "08:00", "12:00"), ("r-y", 2, 2, "13:00", "17:00")]
        for indice, (regra, dia, ordem, inicio, fim) in enumerate(periodos):
            c.execute("INSERT INTO regra_expediente_periodos (id, regra_expediente_id, dia_semana, ordem, inicio, fim) VALUES (%s, %s, %s, %s, %s, %s)", (f"q{indice}", regra, dia, ordem, inicio, fim))
        c.execute("UPDATE regra_expediente_dias SET ativo = true WHERE regra_expediente_id = 'r-y' AND dia_semana IN (0, 1, 2)")
    assert scratch.alembic("downgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        linhas = {linha[0]: linha for linha in _legado(c, "r-y")}
        assert linhas[0][1:] == (True, time(8, 0), time(10, 0), time(11, 0), time(13, 0))  # 3 períodos → só os 2 primeiros
        assert linhas[1][1] is False and linhas[1][2] is None  # 1 período → inativo
        assert linhas[2][1:] == (True, time(8, 0), time(12, 0), time(13, 0), time(17, 0))
        assert linhas[3][1] is False
        with pytest.raises(psycopg.errors.CheckViolation):  # o CHECK antigo voltou
            c.execute("UPDATE regra_expediente_dias SET ativo = true WHERE id = 'r-y-d3'")
