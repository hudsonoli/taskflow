"""Upgrade/downgrade da 0048 (Expediente — Fase 2: logout automático) em PostgreSQL scratch, sem acessar DEV.

Prova: (1) as colunas nascem DESLIGADAS/NULL para toda regra existente (o deploy não desloga ninguém); (2) as flags de bloqueio e de pausa NÃO são alteradas; (3) o CHECK
impede logout ligado sem horário; (4) o downgrade remove só o que a 0048 criou e reaplica; (5) cadeia linear (cabeça única).
"""
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0047_expediente import _semear

ANTERIOR = "a3c8e5f17d24"
NOVA = "b4d7f2a96c31"


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0048_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0048_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def test_upgrade_nasce_desligado_e_nao_mexe_nas_outras_flags(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        c.execute("UPDATE regra_expediente SET bloquear_fora_expediente = true WHERE id = 'r-a'")  # estado "ligado" prévio precisa ser preservado
        antes = c.execute("SELECT id, ativo, bloquear_fora_expediente, pausar_no_fim_periodo, antecedencia_acesso_minutos, timezone FROM regra_expediente ORDER BY id").fetchall()
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        assert c.execute("SELECT id, logout_automatico_ativo, logout_horario FROM regra_expediente ORDER BY id").fetchall() == [("r-a", False, None), ("r-b", False, None)]
        depois = c.execute("SELECT id, ativo, bloquear_fora_expediente, pausar_no_fim_periodo, antecedencia_acesso_minutos, timezone FROM regra_expediente ORDER BY id").fetchall()
        assert depois == antes


def test_check_exige_horario_com_logout_ligado(scratch) -> None:
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        _semear_regra(c)
        c.execute("UPDATE regra_expediente SET logout_automatico_ativo = true, logout_horario = '18:10' WHERE id = 'r-x'")  # ok
        c.execute("UPDATE regra_expediente SET logout_automatico_ativo = false, logout_horario = NULL WHERE id = 'r-x'")  # ok
    with scratch.conectar() as c:
        _semear_regra(c, "r-y", "emp-y")
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("UPDATE regra_expediente SET logout_automatico_ativo = true, logout_horario = NULL WHERE id = 'r-y'")


def _semear_regra(c, regra_id: str = "r-x", empresa_id: str = "emp-x") -> None:
    c.execute(
        "INSERT INTO empresas (id, nome, codigo_interno, slug, status, created_at, updated_at) VALUES (%s, %s, %s, %s, 'ativa', now(), now())",
        (empresa_id, empresa_id, empresa_id.upper(), empresa_id),
    )
    c.execute("INSERT INTO regra_expediente (id, empresa_id, ativo, tolerancia_retomada_minutos, created_at, updated_at) VALUES (%s, %s, true, 30, now(), now())", (regra_id, empresa_id))


def test_downgrade_remove_so_o_que_a_0048_criou_e_reaplica(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        antes = c.execute("SELECT row_to_json(t)::text FROM regra_expediente t ORDER BY id").fetchall()
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    assert {"logout_automatico_ativo", "logout_horario"} <= set(scratch.colunas("regra_expediente"))
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    assert not {"logout_automatico_ativo", "logout_horario"} & set(scratch.colunas("regra_expediente"))
    with scratch.conectar() as c:
        assert c.execute("SELECT row_to_json(t)::text FROM regra_expediente t ORDER BY id").fetchall() == antes
    assert scratch.alembic("upgrade", NOVA).returncode == 0


def test_cadeia_linear_cabeca_unica() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    diretorio = ScriptDirectory.from_config(Config("alembic.ini"))
    assert diretorio.get_heads() == [NOVA]
    assert diretorio.get_revision(NOVA).down_revision == ANTERIOR
