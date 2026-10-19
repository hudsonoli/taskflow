"""Upgrade/downgrade da 0050 (Tráfego V2 — Fase 1: `demanda_status_intervalos`) em PostgreSQL scratch, sem acessar DEV.

Prova: (1) migração ADITIVA — Demandas, sessões, eventos e workflow idênticos; (2) cada Demanda NÃO terminal ganha UM intervalo aberto `origem='migracao'` com o MESMO `inicio_em`
(o marcador do início da medição — nada é reconstruído), com o estado atual e a etapa ATUAL (ou NULL); terminais não ganham nada; (3) constraints/índices existem; (4) o downgrade remove
só a tabela; (5) cadeia linear.
"""
import uuid
from urllib.parse import urlsplit, urlunsplit

import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0043_workflow_etapa import _etapa, _semear_base

ANTERIOR = "c6e1a38d5b92"
NOVA = "d7f3b91e4a58"


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0050_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0050_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _semear(c) -> None:
    _semear_base(c, demandas=6)
    for demanda, status in (("d-1", "em_execucao"), ("d-2", "pausada"), ("d-3", "concluida"), ("d-4", "cancelada"), ("d-5", "arquivada"), ("d-6", "aguardando_cliente")):
        c.execute("UPDATE demandas SET status = %s WHERE id = %s", (status, demanda))
    _etapa(c, "e-1a", "d-1", 1)
    _etapa(c, "e-1b", "d-1", 2)  # etapa ATUAL de d-1
    _etapa(c, "e-1c", "d-1", 3)
    _etapa(c, "e-6a", "d-6", 1)
    c.execute("UPDATE demanda_workflow_etapas SET status = 'concluida', concluida_em = now() WHERE id IN ('e-1a', 'e-6a')")  # e-6a: workflow de d-6 todo concluído → etapa NULL


def _instantaneo(c) -> dict:
    return {
        t: c.execute(f"SELECT row_to_json(x)::text FROM {t} x ORDER BY id").fetchall()
        for t in ("demandas", "demanda_workflow_etapas", "eventos", "sessoes_trabalho", "usuarios", "empresas")
    }


def test_upgrade_abre_um_intervalo_por_demanda_nao_terminal_sem_alterar_nada(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        antes = _instantaneo(c)
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        linhas = c.execute(
            "SELECT demanda_id, status, workflow_etapa_id, origem, fim_em, duracao_segundos, motivo_fim, iniciado_por_usuario_id, evento_inicio_id, inicio_em "
            "FROM demanda_status_intervalos ORDER BY demanda_id"
        ).fetchall()
        assert [(l[0], l[1]) for l in linhas] == [("d-1", "em_execucao"), ("d-2", "pausada"), ("d-6", "aguardando_cliente")]  # terminais (d-3, d-4, d-5) não ganham nada
        assert [l[2] for l in linhas] == ["e-1b", None, None]  # etapa ATUAL; sem workflow = NULL; workflow todo concluído = NULL
        assert all(l[3] == "migracao" and l[4] is None and l[5] is None and l[6] is None and l[7] is None and l[8] is None for l in linhas)  # abertos, sem ator, sem evento
        assert len({l[9] for l in linhas}) == 1  # TODOS com o mesmo `inicio_em` = o marcador do início da medição
        assert _instantaneo(c) == antes  # nada mais mudou: demandas, etapas, eventos, sessões


def test_constraints_e_indices(scratch) -> None:
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        constraints = {r[0] for r in c.execute("SELECT conname FROM pg_constraint WHERE conrelid = 'demanda_status_intervalos'::regclass").fetchall()}
        assert {
            "ck_demanda_status_intervalos_status",
            "ck_demanda_status_intervalos_origem",
            "ck_demanda_status_intervalos_motivo_fim",
            "ck_demanda_status_intervalos_aberto_ou_fechado",
        } <= constraints
        indices = {r[0] for r in c.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'demanda_status_intervalos'").fetchall()}
        assert {
            "uq_demanda_status_intervalos_aberto_por_demanda",
            "uq_demanda_status_intervalos_evento_inicio",
            "ix_demanda_status_intervalos_empresa_demanda_inicio",
            "ix_demanda_status_intervalos_empresa_status_inicio",
            "ix_demanda_status_intervalos_workflow_etapa_id",
        } <= indices
        definicao = c.execute("SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_demanda_status_intervalos_aberto_por_demanda'").fetchone()[0]
        assert "UNIQUE" in definicao and "fim_em IS NULL" in definicao  # no máximo UM aberto por Demanda


def test_downgrade_remove_so_a_tabela_e_reaplica(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        antes = _instantaneo(c)
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        assert c.execute("SELECT to_regclass('demanda_status_intervalos')").fetchone() == (None,)
        assert _instantaneo(c) == antes  # Demandas, sessões, eventos e workflow intactos
    assert scratch.alembic("upgrade", NOVA).returncode == 0


def test_cadeia_linear_cabeca_unica() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    diretorio = ScriptDirectory.from_config(Config("alembic.ini"))
    # cabeça ÚNICA (migrations posteriores a 0050 — ex.: 0051 — avançam a cabeça; esta fase só exige que a 0050 continue na cadeia, ligada à anterior)
    assert len(diretorio.get_heads()) == 1
    assert NOVA in {revisao.revision for revisao in diretorio.walk_revisions()}
    assert diretorio.get_revision(NOVA).down_revision == ANTERIOR
