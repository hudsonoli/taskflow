"""Upgrade/downgrade da 0049 (Expediente — Fase 3: armadura da pausa automática) em PostgreSQL scratch, sem acessar DEV.

Prova: (1) a coluna nasce NULL para toda regra existente (o deploy não arma nem pausa nada); (2) as flags existentes (inclusive `pausar_no_fim_periodo`) não mudam;
(3) o downgrade remove só a coluna e reaplica; (4) cadeia linear (cabeça única).
"""
import uuid
from urllib.parse import urlsplit, urlunsplit

import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0047_expediente import _semear

ANTERIOR = "b4d7f2a96c31"
NOVA = "c6e1a38d5b92"


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0049_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0049_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def test_upgrade_nasce_sem_armadura_e_nao_mexe_nas_flags(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        c.execute("UPDATE regra_expediente SET bloquear_fora_expediente = true, pausar_no_fim_periodo = true WHERE id = 'r-a'")  # estado prévio precisa ser preservado
        antes = c.execute("SELECT id, ativo, bloquear_fora_expediente, pausar_no_fim_periodo, logout_automatico_ativo FROM regra_expediente ORDER BY id").fetchall()
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        assert c.execute("SELECT id, pausa_automatica_ativada_em FROM regra_expediente ORDER BY id").fetchall() == [("r-a", None), ("r-b", None)]
        depois = c.execute("SELECT id, ativo, bloquear_fora_expediente, pausar_no_fim_periodo, logout_automatico_ativo FROM regra_expediente ORDER BY id").fetchall()
        assert depois == antes


def test_downgrade_remove_so_a_coluna_e_reaplica(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        antes = c.execute("SELECT row_to_json(t)::text FROM regra_expediente t ORDER BY id").fetchall()
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    assert "pausa_automatica_ativada_em" in scratch.colunas("regra_expediente")
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    assert "pausa_automatica_ativada_em" not in scratch.colunas("regra_expediente")
    with scratch.conectar() as c:
        assert c.execute("SELECT row_to_json(t)::text FROM regra_expediente t ORDER BY id").fetchall() == antes
    assert scratch.alembic("upgrade", NOVA).returncode == 0


def test_cadeia_linear_cabeca_unica() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    diretorio = ScriptDirectory.from_config(Config("alembic.ini"))
    assert len(diretorio.get_heads()) == 1  # cabeça única (a 0050 vem depois da 0049)
    assert diretorio.get_revision(NOVA).down_revision == ANTERIOR
