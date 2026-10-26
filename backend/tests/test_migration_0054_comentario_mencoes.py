"""Upgrade/downgrade da 0054 (P1_AGORA_MENTIONS — @menções em comentários) em PostgreSQL scratch, sem acessar DEV.

Prova: (1) só cria a tabela `demanda_comentario_mencoes` (nada existente é reescrito, sem backfill); (2) PK (comentário, usuário) impede a menção repetida e o CASCADE apaga as linhas junto com o comentário;
(3) o downgrade remove só a tabela e reaplica (comentários permanecem); (4) cadeia linear, cabeça única.
"""
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0043_workflow_etapa import _etapa
from tests.test_migration_0047_expediente import _semear

ANTERIOR = "a9d2c6e84b17"
NOVA = "b3e7d1c85a46"
INTOCADAS = ("usuarios", "regra_expediente", "demandas", "demanda_workflow_etapas", "demanda_comentarios", "eventos")


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0054_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0054_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _snapshot(c, tabela: str) -> list:
    return c.execute(f"SELECT row_to_json(t)::text FROM {tabela} t ORDER BY id").fetchall()


def _tabela_existe(c) -> bool:
    return c.execute("SELECT to_regclass('public.demanda_comentario_mencoes') IS NOT NULL").fetchone()[0]


def _comentario(c, ident: str) -> None:
    c.execute(
        "INSERT INTO demanda_comentarios (id, demanda_id, autor_usuario_id, texto, created_at, updated_at) VALUES (%s, 'd-1', NULL, 'oi', now(), now())",
        (ident,),
    )


def test_upgrade_so_cria_a_tabela_e_nao_reescreve_nada(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        _etapa(c, "snap-1", "d-1", 1)
        _comentario(c, "c-1")
        assert not _tabela_existe(c)
        antes = {tabela: _snapshot(c, tabela) for tabela in INTOCADAS}
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        assert _tabela_existe(c)
        assert c.execute("SELECT count(*) FROM demanda_comentario_mencoes").fetchone() == (0,)  # sem backfill: o "@" de comentários antigos segue sendo só texto
        for tabela in INTOCADAS:
            assert _snapshot(c, tabela) == antes[tabela], tabela


def test_chave_unica_e_cascade_do_comentario(scratch) -> None:
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        _etapa(c, "snap-1", "d-1", 1)
        _comentario(c, "c-1")
        usuario = c.execute("SELECT id, empresa_id FROM usuarios LIMIT 1").fetchone()
        linha = "INSERT INTO demanda_comentario_mencoes (comentario_id, usuario_id, empresa_id, created_at) VALUES ('c-1', %s, %s, now())"
        c.execute(linha, usuario)
        with pytest.raises(psycopg.errors.UniqueViolation):  # a mesma pessoa não é mencionada duas vezes no mesmo comentário
            c.execute(linha, usuario)
    with scratch.conectar() as c:
        c.execute("DELETE FROM demanda_comentarios WHERE id = 'c-1'")
        assert c.execute("SELECT count(*) FROM demanda_comentario_mencoes").fetchone() == (0,)


def test_downgrade_remove_so_a_tabela_e_reaplica(scratch) -> None:
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear(c)
        _etapa(c, "snap-1", "d-1", 1)
        _comentario(c, "c-1")
        antes = {tabela: _snapshot(c, tabela) for tabela in INTOCADAS}
    assert scratch.alembic("upgrade", NOVA).returncode == 0
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        assert not _tabela_existe(c)
        for tabela in INTOCADAS:  # os comentários continuam; só as menções se vão
            assert _snapshot(c, tabela) == antes[tabela], tabela
    assert scratch.alembic("upgrade", NOVA).returncode == 0


def test_cadeia_linear_cabeca_unica() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    diretorio = ScriptDirectory.from_config(Config("alembic.ini"))
    assert len(diretorio.get_heads()) == 1
    assert diretorio.get_revision(NOVA).down_revision == ANTERIOR
