"""Migration 0036 (Gerenciador de Arquivos) — upgrade sobre dado legado e precondition do
downgrade, contra um banco SCRATCH descartável.

Nunca toca o banco de desenvolvimento nem o `taskfloww_test` da suíte: cada teste cria um
banco próprio (`taskfloww_scratch_0036_*`, mesmo servidor/credenciais de `DATABASE_URL_TEST`,
mesma exigência de CREATEDB que a suíte já tem), roda `alembic` como subprocesso contra ele e o
remove no fim. A FK `demanda_arquivos.demanda_id` é descartada no scratch só para inserir a
linha de teste sem montar empresa/demanda — não interfere nas colunas/constraints que a 0036
altera."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import BACKEND_DIR, _conexao_manutencao, obter_url_teste_validada

REV_0035 = "57c9ac75e1bc"
REV_0036 = "e4464f8f7bb9"
PREFIXO_SCRATCH = "taskfloww_scratch_0036_"

CHECKS_0036 = {
    "ck_demanda_arquivos_tipo",
    "ck_demanda_arquivos_status_layout",
    "ck_demanda_arquivos_status_layout_so_em_layout",
    "ck_demanda_arquivos_fisico_ou_link",
}


class _BancoScratch:
    def __init__(self, nome: str, url: str) -> None:
        self.nome = nome
        self.url = url

    def alembic(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=BACKEND_DIR,
            env={**os.environ, "DATABASE_URL": self.url},
            capture_output=True,
            text=True,
        )

    def conectar(self) -> psycopg.Connection:
        partes = urlsplit(self.url)
        return psycopg.connect(
            f"host={partes.hostname} port={partes.port or 5432} "
            f"user={partes.username} password={partes.password} dbname={self.nome}",
            autocommit=True,
        )

    def revisao_atual(self) -> str:
        resultado = self.alembic("current")
        assert resultado.returncode == 0, resultado.stderr
        return resultado.stdout

    def descartar_fk_de_demanda(self) -> None:
        with self.conectar() as conexao:
            fks = conexao.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'demanda_arquivos'::regclass AND contype = 'f'"
            ).fetchall()
            for (nome,) in fks:
                conexao.execute(f'ALTER TABLE demanda_arquivos DROP CONSTRAINT "{nome}"')

    def colunas_nullable(self) -> dict[str, str]:
        with self.conectar() as conexao:
            linhas = conexao.execute(
                "SELECT column_name, is_nullable FROM information_schema.columns "
                "WHERE table_name = 'demanda_arquivos'"
            ).fetchall()
        return dict(linhas)

    def checks(self) -> set[str]:
        with self.conectar() as conexao:
            linhas = conexao.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'demanda_arquivos'::regclass AND contype = 'c'"
            ).fetchall()
        return {nome for (nome,) in linhas}


@pytest.fixture()
def banco_scratch():
    url_teste = obter_url_teste_validada()
    nome = f"{PREFIXO_SCRATCH}{uuid.uuid4().hex[:8]}"
    assert nome.startswith(PREFIXO_SCRATCH)  # nunca dropa nada fora do prefixo scratch
    url = urlunsplit(urlsplit(url_teste)._replace(path=f"/{nome}"))

    with _conexao_manutencao(url_teste) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        with _conexao_manutencao(url_teste) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def test_legado_vira_anexo_e_downgrade_sem_links_funciona(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_0035).returncode == 0
    banco_scratch.descartar_fk_de_demanda()

    with banco_scratch.conectar() as conexao:
        conexao.execute(
            "INSERT INTO demanda_arquivos "
            "(id, demanda_id, nome_original, nome_fisico, content_type, tamanho_bytes, created_at) "
            "VALUES (%s, %s, 'legado.png', 'legado-fisico.png', 'image/png', 123, now())",
            (str(uuid.uuid4()), str(uuid.uuid4())),
        )

    resultado = banco_scratch.alembic("upgrade", REV_0036)
    assert resultado.returncode == 0, resultado.stderr
    with banco_scratch.conectar() as conexao:
        linha = conexao.execute(
            "SELECT tipo, status_layout, url, titulo, nome_original, nome_fisico, tamanho_bytes FROM demanda_arquivos"
        ).fetchone()
    # Registro legado vira anexo, com o conteúdo físico intacto e nenhum campo de link.
    assert linha == ("anexo", None, None, None, "legado.png", "legado-fisico.png", 123)
    assert CHECKS_0036 <= banco_scratch.checks()

    resultado = banco_scratch.alembic("downgrade", REV_0035)
    assert resultado.returncode == 0, resultado.stderr
    assert REV_0036 not in banco_scratch.revisao_atual()
    assert REV_0035 in banco_scratch.revisao_atual()
    assert not (CHECKS_0036 & banco_scratch.checks())
    with banco_scratch.conectar() as conexao:
        linha = conexao.execute("SELECT nome_original, nome_fisico, tamanho_bytes FROM demanda_arquivos").fetchone()
    assert linha == ("legado.png", "legado-fisico.png", 123)


def test_downgrade_com_link_aborta_antes_de_alterar_o_schema(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_0036).returncode == 0
    banco_scratch.descartar_fk_de_demanda()

    link_id = str(uuid.uuid4())
    with banco_scratch.conectar() as conexao:
        conexao.execute(
            "INSERT INTO demanda_arquivos (id, demanda_id, tipo, url, titulo, created_at) "
            "VALUES (%s, %s, 'link', 'https://example.com', 'Link', now())",
            (link_id, str(uuid.uuid4())),
        )
    colunas_antes = banco_scratch.colunas_nullable()
    checks_antes = banco_scratch.checks()

    resultado = banco_scratch.alembic("downgrade", REV_0035)
    saida = resultado.stdout + resultado.stderr
    assert resultado.returncode != 0
    # Falha explícita da precondition — não um NotNullViolation incidental no meio do rollback.
    assert "Cannot downgrade 0036 while link records exist" in saida
    assert "NotNullViolation" not in saida

    # Nada foi alterado: continua na 0036, schema e constraints idênticos, link preservado.
    assert REV_0036 in banco_scratch.revisao_atual()
    assert banco_scratch.colunas_nullable() == colunas_antes
    assert banco_scratch.checks() == checks_antes
    with banco_scratch.conectar() as conexao:
        assert conexao.execute("SELECT count(*) FROM demanda_arquivos WHERE tipo = 'link'").fetchone() == (1,)

    # Removido o link explicitamente, o downgrade passa a funcionar.
    with banco_scratch.conectar() as conexao:
        conexao.execute("DELETE FROM demanda_arquivos WHERE id = %s", (link_id,))
    resultado = banco_scratch.alembic("downgrade", REV_0035)
    assert resultado.returncode == 0, resultado.stderr
    assert REV_0035 in banco_scratch.revisao_atual()
