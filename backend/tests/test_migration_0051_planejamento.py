"""Upgrade/downgrade da 0051 (11B.2B-A — janela planejada + percentual de capacidade alocável) em PostgreSQL scratch, sem acessar DEV.

Prova: (1) etapas existentes nascem NULL/NULL e regras existentes com 100, sem reescrever nenhum outro dado; (2) os CHECKs aceitam só os estados válidos;
(3) o downgrade remove só as colunas/CHECKs novos; (4) cadeia linear, cabeça única.
"""
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0043_workflow_etapa import _etapa
from tests.test_migration_0047_expediente import _semear

ANTERIOR = "d7f3b91e4a58"
NOVA = "e8a4c2d71f96"
TABELAS_CAMPOS = {
    "demanda_workflow_etapas": ("planejado_inicio", "planejado_fim"),
    "regra_expediente": ("percentual_capacidade_alocavel",),
}


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0051_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0051_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _semear_com_etapas(c) -> None:
    _semear(c)
    _etapa(c, "snap-1", "d-1", 1)
    _etapa(c, "snap-2", "d-1", 2)
    c.execute("UPDATE regra_expediente SET bloquear_fora_expediente = true, pausar_no_fim_periodo = true WHERE id = 'r-a'")


def _snapshot(c, tabela: str) -> list:
    return c.execute(f"SELECT row_to_json(t)::text FROM {tabela} t ORDER BY id").fetchall()


def test_upgrade_nasce_nao_planejado_e_100_sem_reescrever_dados(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear_com_etapas(c)
        antes = {tabela: _snapshot(c, tabela) for tabela in (*TABELAS_CAMPOS, "demandas", "workflow_modelo_etapas", "sessoes_trabalho", "demanda_status_intervalos")}
        armada_antes = c.execute("SELECT id, pausa_automatica_ativada_em FROM regra_expediente ORDER BY id").fetchall()
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        assert c.execute("SELECT id, planejado_inicio, planejado_fim FROM demanda_workflow_etapas ORDER BY id").fetchall() == [("snap-1", None, None), ("snap-2", None, None)]
        assert c.execute("SELECT id, percentual_capacidade_alocavel FROM regra_expediente ORDER BY id").fetchall() == [("r-a", 100), ("r-b", 100)]
        # nenhuma outra coluna foi reescrita (as linhas, sem as colunas novas, são idênticas) e as tabelas não tocadas seguem idênticas
        for tabela, novas in TABELAS_CAMPOS.items():
            retirar = "".join(f" - '{coluna}'" for coluna in novas)
            for linha in antes[tabela]:
                assert c.execute(f"SELECT (to_jsonb(t){retirar}) = %s::jsonb FROM {tabela} t WHERE t.id = (%s::jsonb ->> 'id')", (linha[0], linha[0])).fetchone() == (True,)
        for tabela in ("demandas", "workflow_modelo_etapas", "sessoes_trabalho", "demanda_status_intervalos"):
            assert _snapshot(c, tabela) == antes[tabela]
        assert c.execute("SELECT id, pausa_automatica_ativada_em FROM regra_expediente ORDER BY id").fetchall() == armada_antes
        assert "planejado_inicio" not in scratch.colunas("workflow_modelo_etapas")


def test_checks_aceitam_so_os_estados_validos(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear_com_etapas(c)
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        for inicio, fim in ((None, None), ("2026-10-20", None), ("2026-10-20", "2026-10-20"), ("2026-10-20", "2026-10-30")):
            c.execute("UPDATE demanda_workflow_etapas SET planejado_inicio = %s, planejado_fim = %s WHERE id = 'snap-1'", (inicio, fim))
        for inicio, fim in ((None, "2026-10-30"), ("2026-10-30", "2026-10-20")):
            with pytest.raises(psycopg.errors.CheckViolation):
                c.execute("UPDATE demanda_workflow_etapas SET planejado_inicio = %s, planejado_fim = %s WHERE id = 'snap-1'", (inicio, fim))
        for valor in (1, 75, 100):
            c.execute("UPDATE regra_expediente SET percentual_capacidade_alocavel = %s WHERE id = 'r-a'", (valor,))
        for valor in (0, 101, -5):
            with pytest.raises(psycopg.errors.CheckViolation):
                c.execute("UPDATE regra_expediente SET percentual_capacidade_alocavel = %s WHERE id = 'r-a'", (valor,))
        with pytest.raises(psycopg.errors.NotNullViolation):
            c.execute("UPDATE regra_expediente SET percentual_capacidade_alocavel = NULL WHERE id = 'r-a'")


def test_downgrade_remove_so_o_que_a_migration_criou_e_reaplica(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear_com_etapas(c)
        antes = {tabela: _snapshot(c, tabela) for tabela in TABELAS_CAMPOS}
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    for tabela, colunas in TABELAS_CAMPOS.items():
        assert set(colunas) <= set(scratch.colunas(tabela))
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    for tabela, colunas in TABELAS_CAMPOS.items():
        assert not set(colunas) & set(scratch.colunas(tabela))
    with scratch.conectar() as c:
        for tabela in TABELAS_CAMPOS:
            assert _snapshot(c, tabela) == antes[tabela]
        restantes = {linha[0] for linha in c.execute("SELECT conname FROM pg_constraint WHERE conname IN ('ck_demanda_workflow_etapas_janela_planejada', 'ck_regra_expediente_percentual_capacidade_alocavel')").fetchall()}
        assert restantes == set()
    assert scratch.alembic("upgrade", NOVA).returncode == 0


def test_cadeia_linear_cabeca_unica() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    diretorio = ScriptDirectory.from_config(Config("alembic.ini"))
    assert len(diretorio.get_heads()) == 1
    assert diretorio.get_revision(NOVA).down_revision == ANTERIOR
