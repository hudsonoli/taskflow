"""Migration 0042 (numeração configurável — Fase 7D.1): upgrade a partir do estado de produção (`c5b2e8a91d47`), backfill
do identificador histórico, constraints e downgrade, contra um banco SCRATCH descartável (mesmo padrão de
test_migration_0041_plataforma.py: nunca toca o banco de desenvolvimento nem o `taskfloww_test`)."""

from __future__ import annotations

import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch

REV_ANTERIOR = "c5b2e8a91d47"
REV_0042 = "e4a7c1d93b60"
PREFIXO_SCRATCH = "taskfloww_scratch_0042_"


@pytest.fixture()
def banco_scratch():
    url_teste = obter_url_teste_validada()
    nome = f"{PREFIXO_SCRATCH}{uuid.uuid4().hex[:8]}"
    assert nome.startswith(PREFIXO_SCRATCH)
    url = urlunsplit(urlsplit(url_teste)._replace(path=f"/{nome}"))
    with _conexao_manutencao(url_teste) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        with _conexao_manutencao(url_teste) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _semear(conexao, empresa_id: str, codigo: str, numeros: list[int]) -> None:
    conexao.execute(
        "INSERT INTO empresas (id, nome, codigo_interno, slug, status, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, 'ativa', now(), now())",
        (empresa_id, f"Empresa {codigo}", codigo, codigo.lower()),
    )
    for numero in numeros:
        conexao.execute(
            "INSERT INTO demandas (id, empresa_id, codigo_referencia, ano_referencia, sequencial_referencia, numero_operacional, "
            "nome, status, prioridade, sinalizada, created_at, updated_at) "
            "VALUES (%s, %s, %s, 26, %s, %s, %s, 'planejada', 'media', false, now(), now())",
            (f"d-{empresa_id}-{numero}", empresa_id, f"T26{numero:06d}", numero, numero, f"Tarefa {numero}"),
        )
    conexao.execute(
        "INSERT INTO sequencias_operacionais (id, empresa_id, tipo_entidade, ultimo_numero, created_at, updated_at) "
        "VALUES (%s, %s, 'demanda', %s, now(), now())",
        (f"seq-{empresa_id}", empresa_id, max(numeros)),
    )


def test_upgrade_backfill_historico_sem_padding_e_constraints(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    with banco_scratch.conectar() as conexao:
        _semear(conexao, "emp-a", "EMPA", [1, 2, 845])
        _semear(conexao, "emp-b", "EMPB", [1, 2063])

    resultado = banco_scratch.alembic("upgrade", REV_0042)
    assert resultado.returncode == 0, resultado.stderr
    assert REV_0042 in banco_scratch.revisao_atual()

    with banco_scratch.conectar() as conexao:
        ident = {(e, n): i for e, n, i in conexao.execute("SELECT empresa_id, numero_operacional, identificador FROM demandas")}
        # histórico = formato ORIGINAL `#N`, sem padding e sem consultar nenhuma configuração
        assert ident == {("emp-a", 1): "#1", ("emp-a", 2): "#2", ("emp-a", 845): "#845", ("emp-b", 1): "#1", ("emp-b", 2063): "#2063"}
        assert conexao.execute("SELECT count(*) FROM demandas WHERE identificador IS NULL").fetchone()[0] == 0
        # o inteiro e o contador seguem intactos
        assert conexao.execute("SELECT max(numero_operacional) FROM demandas WHERE empresa_id='emp-a'").fetchone()[0] == 845
        seq = conexao.execute(
            "SELECT ultimo_numero, prefixo, digitos, incluir_ano, separador FROM sequencias_operacionais WHERE empresa_id='emp-a'"
        ).fetchone()
        assert seq == (845, "#", 1, False, "")  # defaults = comportamento de sempre
        # NOT NULL
        nullable = conexao.execute(
            "SELECT is_nullable FROM information_schema.columns WHERE table_name='demandas' AND column_name='identificador'"
        ).fetchone()[0]
        assert nullable == "NO"
        # UNIQUE por empresa: mesmo identificador em OUTRA empresa é permitido (já provado: `#1` em A e em B); na mesma, não
        with pytest.raises(psycopg.errors.UniqueViolation):
            conexao.execute("UPDATE demandas SET identificador = '#1' WHERE empresa_id='emp-a' AND numero_operacional = 2")
        # a unicidade do número operacional NÃO foi tocada
        with pytest.raises(psycopg.errors.UniqueViolation):
            conexao.execute("UPDATE demandas SET numero_operacional = 1 WHERE empresa_id='emp-a' AND numero_operacional = 2")
        # check dos dígitos
        for ruim in (0, 11):
            with pytest.raises(psycopg.errors.CheckViolation):
                conexao.execute("UPDATE sequencias_operacionais SET digitos = %s WHERE empresa_id='emp-a'", (ruim,))


def test_downgrade_remove_colunas_e_preserva_numero_operacional(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    with banco_scratch.conectar() as conexao:
        _semear(conexao, "emp-a", "EMPA", [1, 845])
    assert banco_scratch.alembic("upgrade", REV_0042).returncode == 0
    with banco_scratch.conectar() as conexao:
        conexao.execute("UPDATE sequencias_operacionais SET prefixo='BOX', digitos=5, incluir_ano=true, separador='-'")

    resultado = banco_scratch.alembic("downgrade", REV_ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    assert REV_ANTERIOR in banco_scratch.revisao_atual() and REV_0042 not in banco_scratch.revisao_atual()
    assert "identificador" not in banco_scratch.colunas("demandas")
    assert not ({"prefixo", "digitos", "incluir_ano", "separador"} & banco_scratch.colunas("sequencias_operacionais"))
    with banco_scratch.conectar() as conexao:
        assert sorted(n for (n,) in conexao.execute("SELECT numero_operacional FROM demandas")) == [1, 845]
        assert conexao.execute("SELECT ultimo_numero FROM sequencias_operacionais").fetchone() == (845,)

    # e sobe de novo (reversível e re-aplicável)
    assert banco_scratch.alembic("upgrade", REV_0042).returncode == 0
    with banco_scratch.conectar() as conexao:
        assert sorted(i for (i,) in conexao.execute("SELECT identificador FROM demandas")) == ["#1", "#845"]
