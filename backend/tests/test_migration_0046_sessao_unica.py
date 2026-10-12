"""Upgrade/downgrade da 0046 (uma sessão de trabalho ativa por pessoa) em PostgreSQL scratch, sem acessar DEV."""
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch
from tests.test_migration_0043_workflow_etapa import _semear_base

ANTERIOR = "d9f3b58e2a71"
NOVA = "f2c6a9d41b87"
INDICE = "uq_sessoes_trabalho_ativa_empresa_usuario"


@pytest.fixture()
def scratch():
    original = obter_url_teste_validada()
    nome = "taskfloww_scratch_0046_" + uuid.uuid4().hex[:8]
    url = urlunsplit(urlsplit(original)._replace(path=f"/{nome}"))
    with _conexao_manutencao(original) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        assert nome.startswith("taskfloww_scratch_0046_")
        with _conexao_manutencao(original) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _sessao(c, sid: str, *, usuario: str | None, status: str, demanda: str = "d-1", departamento: str | None = None) -> None:
    encerrada = status == "encerrada"
    c.execute(
        "INSERT INTO sessoes_trabalho (id, empresa_id, demanda_id, usuario_id, departamento_id, evento_inicio_id, evento_fim_id, status, inicio_em, fim_em, "
        "duracao_segundos, created_at, updated_at) VALUES (%s, 'emp-a', %s, %s, %s, %s, %s, %s, now(), CASE WHEN %s::boolean THEN now() END, "
        "CASE WHEN %s::boolean THEN 0 END, now(), now())",
        (sid, demanda, usuario, departamento, f"ev-{sid}", f"evf-{sid}" if encerrada else None, status, encerrada, encerrada),
    )


def _indice(c) -> str | None:
    linha = c.execute("SELECT indexdef FROM pg_indexes WHERE indexname = %s", (INDICE,)).fetchone()
    return linha[0] if linha else None


def test_upgrade_cria_indice_parcial_preserva_dados_e_down_remove(scratch):
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear_base(c)
        _sessao(c, "s-ativa", usuario="u-1", status="ativa")
        _sessao(c, "s-enc-1", usuario="u-1", status="encerrada", demanda="d-2")  # histórico da mesma pessoa não conta
        _sessao(c, "s-enc-2", usuario="u-1", status="encerrada", demanda="d-1")
        antes = c.execute("SELECT count(*), count(*) FILTER (WHERE status='ativa') FROM sessoes_trabalho").fetchone()
        assert _indice(c) is None
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        definicao = _indice(c)
        assert definicao and "UNIQUE" in definicao and "(empresa_id, usuario_id)" in definicao and "usuario_id IS NOT NULL" in definicao
        assert c.execute("SELECT count(*), count(*) FILTER (WHERE status='ativa') FROM sessoes_trabalho").fetchone() == antes  # sem backfill, sem mudança de dados
        # segunda ativa da MESMA pessoa: o banco recusa
        with pytest.raises(psycopg.errors.UniqueViolation):
            _sessao(c, "s-ativa-2", usuario="u-1", status="ativa", demanda="d-2")
        # departamental (sem usuário) fica fora do índice
        _sessao(c, "s-dep-1", usuario=None, status="ativa", demanda="d-1")
        _sessao(c, "s-dep-2", usuario=None, status="ativa", demanda="d-2")
    resultado = scratch.alembic("downgrade", ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    with scratch.conectar() as c:
        assert _indice(c) is None
        assert c.execute("SELECT count(*) FROM sessoes_trabalho").fetchone() == (5,)
    assert scratch.alembic("upgrade", NOVA).returncode == 0


def test_upgrade_para_antes_de_criar_o_indice_se_o_legado_tiver_conflito(scratch):
    """Legado incompatível NUNCA é corrigido automaticamente: a migration para, informa só a contagem e não deixa o índice pela metade."""
    assert scratch.alembic("upgrade", ANTERIOR).returncode == 0
    with scratch.conectar() as c:
        _semear_base(c)
        _sessao(c, "s-1", usuario="u-1", status="ativa", demanda="d-1")
        _sessao(c, "s-2", usuario="u-1", status="ativa", demanda="d-2")
    resultado = scratch.alembic("upgrade", NOVA)
    assert resultado.returncode != 0
    assert "1 usuário(s) com mais de uma sessão de trabalho ativa" in resultado.stderr
    assert "u-1" not in resultado.stderr.split("RuntimeError")[-1]  # sem id/identidade na mensagem
    with scratch.conectar() as c:
        assert _indice(c) is None
        assert c.execute("SELECT count(*) FROM sessoes_trabalho WHERE status = 'ativa'").fetchone() == (2,)  # nada foi encerrado
    assert ANTERIOR in scratch.revisao_atual()
