"""Upgrade/downgrade da 0052 (11B.2D-A — jornada individual + ausências) em PostgreSQL scratch, sem acessar DEV.

Prova: (1) só 3 tabelas novas, vazias — usuários existentes continuam SEM jornada personalizada, nenhuma ausência é inventada e nada existente é reescrito (regra de expediente, usuários, demandas,
etapas, sessões, intervalos); (2) CHECKs/UNIQUEs aceitam só o que devem; (3) o downgrade remove só as tabelas novas e reaplica; (4) cadeia linear, cabeça única.
"""
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0043_workflow_etapa import _etapa
from tests.test_migration_0047_expediente import _semear

ANTERIOR = "e8a4c2d71f96"
NOVA = "f1b7c3a95d28"
TABELAS_NOVAS = ("usuario_jornadas", "usuario_jornada_periodos", "usuario_ausencias")
INTOCADAS = ("usuarios", "regra_expediente", "regra_expediente_periodos", "regra_expediente_dias_especiais", "demandas", "demanda_workflow_etapas", "sessoes_trabalho", "demanda_status_intervalos", "eventos")


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0052_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0052_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _snapshot(c, tabela: str) -> list:
    return c.execute(f"SELECT row_to_json(t)::text FROM {tabela} t ORDER BY id").fetchall()


def _semear_dados(c) -> None:
    _semear(c)
    _etapa(c, "snap-1", "d-1", 1)
    c.execute("UPDATE regra_expediente SET bloquear_fora_expediente = true, pausar_no_fim_periodo = true, percentual_capacidade_alocavel = 80 WHERE id = 'r-a'")
    c.execute("UPDATE demanda_workflow_etapas SET planejado_inicio = '2026-10-20', planejado_fim = '2026-10-23', esforco_estimado_minutos = 240 WHERE id = 'snap-1'")


def test_upgrade_cria_so_tres_tabelas_vazias_e_nao_reescreve_nada(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    for tabela in TABELAS_NOVAS:
        assert not scratch.existe_tabela(tabela)
    with scratch.conectar() as c:
        _semear_dados(c)
        antes = {tabela: _snapshot(c, tabela) for tabela in INTOCADAS}
        usuarios = c.execute("SELECT count(*) FROM usuarios").fetchone()[0]
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        for tabela in TABELAS_NOVAS:
            assert c.execute(f"SELECT count(*) FROM {tabela}").fetchone() == (0,), tabela  # sem backfill
        assert usuarios >= 1 and c.execute("SELECT count(*) FROM usuarios u WHERE NOT EXISTS (SELECT 1 FROM usuario_jornadas j WHERE j.usuario_id = u.id)").fetchone()[0] == usuarios  # ninguém tem jornada própria
        for tabela in INTOCADAS:
            assert _snapshot(c, tabela) == antes[tabela], tabela
        assert c.execute("SELECT percentual_capacidade_alocavel FROM regra_expediente WHERE id = 'r-a'").fetchone() == (80,)


def test_constraints_aceitam_so_o_valido(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear_dados(c)
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        c.execute("INSERT INTO usuario_jornadas (id, empresa_id, usuario_id, created_at, updated_at) VALUES ('j-1', 'emp-a', 'u-1', now(), now())")
        with pytest.raises(psycopg.errors.UniqueViolation):  # UNIQUE(usuario_id): uma jornada por usuário
            c.execute("INSERT INTO usuario_jornadas (id, empresa_id, usuario_id, created_at, updated_at) VALUES ('j-2', 'emp-a', 'u-1', now(), now())")
        c.execute("INSERT INTO usuario_jornada_periodos (id, jornada_id, dia_semana, ordem, inicio, fim) VALUES ('p-1', 'j-1', 0, 1, '09:00', '12:00')")
        c.execute("INSERT INTO usuario_jornada_periodos (id, jornada_id, dia_semana, ordem, inicio, fim) VALUES ('p-2', 'j-1', 0, 2, '13:00', '17:00')")
        for dia, ordem, inicio, fim in ((7, 1, "09:00", "12:00"), (-1, 1, "09:00", "12:00"), (1, 0, "09:00", "12:00"), (1, 1, "12:00", "09:00"), (1, 1, "09:00", "09:00")):
            with pytest.raises(psycopg.errors.CheckViolation):
                c.execute("INSERT INTO usuario_jornada_periodos (id, jornada_id, dia_semana, ordem, inicio, fim) VALUES (%s, 'j-1', %s, %s, %s, %s)", (f"x{dia}{ordem}", dia, ordem, inicio, fim))
        with pytest.raises(psycopg.errors.UniqueViolation):  # (jornada, dia, ordem) único
            c.execute("INSERT INTO usuario_jornada_periodos (id, jornada_id, dia_semana, ordem, inicio, fim) VALUES ('p-3', 'j-1', 0, 1, '18:00', '19:00')")
        for tipo in ("ferias", "afastamento", "folga", "outro"):
            c.execute("INSERT INTO usuario_ausencias (id, empresa_id, usuario_id, tipo, inicio, fim, created_at, updated_at) VALUES (%s, 'emp-a', 'u-1', %s, '2026-10-26', '2026-10-26', now(), now())", (f"a-{tipo}", tipo))
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("INSERT INTO usuario_ausencias (id, empresa_id, usuario_id, tipo, inicio, fim, created_at, updated_at) VALUES ('a-x', 'emp-a', 'u-1', 'licenca', '2026-10-26', '2026-10-27', now(), now())")
        with pytest.raises(psycopg.errors.CheckViolation):  # fim >= início
            c.execute("INSERT INTO usuario_ausencias (id, empresa_id, usuario_id, tipo, inicio, fim, created_at, updated_at) VALUES ('a-y', 'emp-a', 'u-1', 'ferias', '2026-10-27', '2026-10-26', now(), now())")
        # ausências podem se sobrepor (a sobreposição é resolvida no cálculo, sem constraint de exclusão)
        c.execute("INSERT INTO usuario_ausencias (id, empresa_id, usuario_id, tipo, inicio, fim, created_at, updated_at) VALUES ('a-z', 'emp-a', 'u-1', 'outro', '2026-10-26', '2026-10-28', now(), now())")
        # remover a jornada leva os períodos junto (CASCADE)
        c.execute("DELETE FROM usuario_jornadas WHERE id = 'j-1'")
        assert c.execute("SELECT count(*) FROM usuario_jornada_periodos").fetchone() == (0,)


def test_downgrade_remove_so_as_tabelas_novas_e_reaplica(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear_dados(c)
        antes = {tabela: _snapshot(c, tabela) for tabela in INTOCADAS}
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    for tabela in TABELAS_NOVAS:
        assert scratch.existe_tabela(tabela)
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    for tabela in TABELAS_NOVAS:
        assert not scratch.existe_tabela(tabela)
    with scratch.conectar() as c:
        for tabela in INTOCADAS:
            assert _snapshot(c, tabela) == antes[tabela], tabela
    assert scratch.alembic("upgrade", NOVA).returncode == 0


def test_cadeia_linear_cabeca_unica() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    diretorio = ScriptDirectory.from_config(Config("alembic.ini"))
    assert len(diretorio.get_heads()) == 1  # cabeça única (a 0053 vem depois da 0052)
    assert diretorio.get_revision(NOVA).down_revision == ANTERIOR
