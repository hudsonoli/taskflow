"""Upgrade/downgrade em PostgreSQL scratch, sem acessar DEV."""
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0043_workflow_etapa import _semear_base, _etapa

ANTERIOR = "c8e2a47d1f93"
NOVA = "d9f3b58e2a71"
CAMPO = "esforco_estimado_minutos"
TABELAS = ("workflow_modelo_etapas", "demanda_workflow_etapas")


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0045_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0045_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def test_upgrade_preserva_legado_null_checks_e_down(scratch):
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear_base(c)
        _etapa(c, "snap", "d-1", 1)
        c.execute("INSERT INTO workflow_modelos (id, empresa_id, codigo_interno, codigo_referencia, ano_referencia, sequencial_referencia, nome, nome_normalizado, status, created_at, updated_at) VALUES ('modelo', 'emp-a', 'WM1', 'W261', 26, 1, 'Modelo', 'modelo', 'ativo', now(), now())")
        c.execute("INSERT INTO workflow_modelo_etapas (id, workflow_modelo_id, ordem, nome, tipo, quantidade_antes_deadline, unidade_prazo, created_at, updated_at) VALUES ('template', 'modelo', 1, 'Criar', 'execucao', 3, 'dias_uteis', now(), now())")
        antes = {t: c.execute(f'SELECT row_to_json(t)::text FROM {t} t').fetchall() for t in TABELAS}
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        for t in TABELAS:
            assert c.execute(f'SELECT {CAMPO} FROM {t}').fetchone() == (None,)
            assert c.execute(f"SELECT (to_jsonb(t) - '{CAMPO}') = %s::jsonb FROM {t} t", (antes[t][0][0],)).fetchone() == (True,)
            for valor in (0, 120, None):
                c.execute(f'UPDATE {t} SET {CAMPO} = %s', (valor,))
                assert c.execute(f'SELECT {CAMPO} FROM {t}').fetchone() == (valor,)
            with pytest.raises(psycopg.errors.CheckViolation):
                c.execute(f'UPDATE {t} SET {CAMPO} = -1')
            with pytest.raises(psycopg.errors.NumericValueOutOfRange):
                c.execute(f'UPDATE {t} SET {CAMPO} = 2147483648')
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        for t in TABELAS:
            assert CAMPO not in scratch.colunas(t)
            assert c.execute(f'SELECT row_to_json(t)::text FROM {t} t').fetchall() == antes[t]
    assert scratch.alembic("upgrade", NOVA).returncode == 0
