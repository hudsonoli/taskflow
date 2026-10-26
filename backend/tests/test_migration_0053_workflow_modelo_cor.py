"""Upgrade/downgrade da 0053 (P1_WORKFLOW_COLOR — cor do modelo de workflow) em PostgreSQL scratch, sem acessar DEV.

Prova: (1) só uma coluna nullable nova; modelos existentes ficam com cor NULL (nenhuma cor escolhida pelo banco) e nada existente é reescrito; (2) o CHECK aceita só NULL ou `#RRGGBB` em maiúsculas;
(3) o downgrade remove só a coluna/constraint e reaplica; (4) cadeia linear, cabeça única.
"""
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0043_workflow_etapa import _etapa
from tests.test_migration_0047_expediente import _semear

ANTERIOR = "f1b7c3a95d28"
NOVA = "a9d2c6e84b17"
INTOCADAS = ("usuarios", "regra_expediente", "demandas", "demanda_workflow_etapas", "sessoes_trabalho", "demanda_status_intervalos", "eventos")


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0053_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0053_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _snapshot(c, tabela: str) -> list:
    return c.execute(f"SELECT row_to_json(t)::text FROM {tabela} t ORDER BY id").fetchall()


def _modelo(c, ident: str) -> None:
    c.execute(
        "INSERT INTO workflow_modelos (id, empresa_id, codigo_interno, codigo_referencia, ano_referencia, sequencial_referencia, nome, nome_normalizado, status, created_at, updated_at) "
        "VALUES (%s, 'emp-a', %s, %s, 26, %s, %s, %s, 'ativo', now(), now())",
        (ident, f"wf-{ident}", f"W26{ident[-4:]}", int(ident[-1]), f"Modelo {ident}", f"modelo {ident}"),
    )


def _colunas(c) -> set[str]:
    return {linha[0] for linha in c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'workflow_modelos'").fetchall()}


def test_upgrade_so_adiciona_a_coluna_cor_nula_e_nao_reescreve_nada(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        _etapa(c, "snap-1", "d-1", 1)
        _modelo(c, "wf-1")
        _modelo(c, "wf-2")
        assert "cor" not in _colunas(c)
        antes = {tabela: _snapshot(c, tabela) for tabela in INTOCADAS}
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        assert "cor" in _colunas(c)
        assert c.execute("SELECT count(*) FROM workflow_modelos WHERE cor IS NOT NULL").fetchone() == (0,)  # sem backfill: ninguém ganha cor automática
        assert c.execute("SELECT count(*) FROM workflow_modelos").fetchone() == (2,)
        for tabela in INTOCADAS:
            assert _snapshot(c, tabela) == antes[tabela], tabela
        assert c.execute("SELECT is_nullable, character_maximum_length FROM information_schema.columns WHERE table_name = 'workflow_modelos' AND column_name = 'cor'").fetchone() == ("YES", 7)


def test_check_aceita_so_null_ou_hex_canonico_em_maiusculas(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        _modelo(c, "wf-1")
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        for valida in ("#8B5CF6", "#000000", "#FFFFFF", None):
            c.execute("UPDATE workflow_modelos SET cor = %s WHERE id = 'wf-1'", (valida,))
        for invalida in ("#8b5cf6", "#FFF", "#8B5CF", "#8B5CF67", "8B5CF6", "red", "", "rgb(1,2,3)", "#8B5CF6;"):
            with pytest.raises((psycopg.errors.CheckViolation, psycopg.errors.StringDataRightTruncation)):  # a coluna é VARCHAR(7): o que passa de 7 caracteres nem chega ao CHECK
                c.execute("UPDATE workflow_modelos SET cor = %s WHERE id = 'wf-1'", (invalida,))


def test_downgrade_remove_so_a_coluna_e_reaplica(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        _modelo(c, "wf-1")
        antes = {tabela: _snapshot(c, tabela) for tabela in INTOCADAS}
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        c.execute("UPDATE workflow_modelos SET cor = '#8B5CF6' WHERE id = 'wf-1'")
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        assert "cor" not in _colunas(c)
        assert c.execute("SELECT count(*) FROM workflow_modelos").fetchone() == (1,)  # o modelo continua; só a cor se vai
        for tabela in INTOCADAS:
            assert _snapshot(c, tabela) == antes[tabela], tabela
    assert scratch.alembic("upgrade", NOVA).returncode == 0


def test_cadeia_linear_cabeca_unica() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    diretorio = ScriptDirectory.from_config(Config("alembic.ini"))
    assert len(diretorio.get_heads()) == 1  # cabeça única (a 0054 vem depois da 0053)
    assert diretorio.get_revision(NOVA).down_revision == ANTERIOR
