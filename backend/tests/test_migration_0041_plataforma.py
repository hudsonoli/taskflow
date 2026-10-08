"""Migration 0041 (Administração da Plataforma — slug da empresa, nome fantasia, administradores_plataforma) — upgrade
a partir do estado de produção (`9a3d4e6f1b28`), backfill do slug, preservação dos dados existentes e downgrade,
contra um banco SCRATCH descartável (mesmo padrão de test_migration_0036_arquivos.py: nunca toca o banco de
desenvolvimento nem o `taskfloww_test`)."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import BACKEND_DIR, _conexao_manutencao, obter_url_teste_validada

REV_ANTERIOR = "9a3d4e6f1b28"
REV_0041 = "c5b2e8a91d47"
PREFIXO_SCRATCH = "taskfloww_scratch_0041_"

LOGO_KEY_DEMO = "personalizacao/demo-id/logo-aaaaaaaa.png"


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

    def existe_tabela(self, nome: str) -> bool:
        with self.conectar() as conexao:
            return conexao.execute("SELECT to_regclass(%s)", (nome,)).fetchone()[0] is not None

    def colunas(self, tabela: str) -> set[str]:
        with self.conectar() as conexao:
            linhas = conexao.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s", (tabela,)
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


def _semear_estado_de_producao(banco: _BancoScratch) -> None:
    """DEMO + um usuário (conta de sistema, como o proprietário) + personalização com logo, tudo na revisão anterior."""
    with banco.conectar() as conexao:
        conexao.execute(
            "INSERT INTO empresas (id, nome, codigo_interno, status, created_at, updated_at) "
            "VALUES ('demo-id', 'Empresa Demo', 'DEMO', 'ativa', '2026-01-01', '2026-01-01')"
        )
        conexao.execute(
            "INSERT INTO usuarios (id, empresa_id, codigo_interno, nome, email, perfil_base, acesso_sistema, status, "
            "is_system_account, created_at, updated_at) "
            "VALUES ('usr-1', 'demo-id', 'U-1', 'Proprietário', 'dono@example.com', 'admin', true, 'ativo', true, now(), now())"
        )
        conexao.execute(
            "INSERT INTO configuracoes_personalizacao "
            "(id, empresa_id, logo_storage_key, logo_mime_type, cor_primaria, cor_secundaria, tema, created_at, updated_at) "
            "VALUES ('cfg-1', 'demo-id', %s, 'image/png', '#112233', '#445566', 'escuro', now(), now())",
            (LOGO_KEY_DEMO,),
        )


def test_upgrade_preenche_slug_preserva_dados_e_downgrade_reverte(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    _semear_estado_de_producao(banco_scratch)

    resultado = banco_scratch.alembic("upgrade", REV_0041)
    assert resultado.returncode == 0, resultado.stderr
    assert REV_0041 in banco_scratch.revisao_atual()

    with banco_scratch.conectar() as conexao:
        empresa = conexao.execute("SELECT nome, codigo_interno, slug, nome_fantasia, status FROM empresas").fetchone()
        usuario = conexao.execute("SELECT perfil_base, is_system_account, status, email FROM usuarios").fetchone()
        cfg = conexao.execute(
            "SELECT logo_storage_key, logo_mime_type, cor_primaria, cor_secundaria, tema FROM configuracoes_personalizacao"
        ).fetchone()
        admins = conexao.execute("SELECT count(*) FROM administradores_plataforma").fetchone()[0]

    # DEMO: slug preenchido ("DEMO" -> "demo"), código de login intacto, nada mais mudou
    assert empresa == ("Empresa Demo", "DEMO", "demo", None, "ativa")
    # a linha do usuário (perfil admin legado + conta de sistema) NÃO foi alterada
    assert usuario == ("admin", True, "ativo", "dono@example.com")
    # personalização e chave de storage do logo preservadas (a migration não move arquivo algum)
    assert cfg == (LOGO_KEY_DEMO, "image/png", "#112233", "#445566", "escuro")
    # a autoridade nasce só pelo CLI — a migration não cria administrador
    assert admins == 0

    resultado = banco_scratch.alembic("downgrade", REV_ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    assert REV_ANTERIOR in banco_scratch.revisao_atual() and REV_0041 not in banco_scratch.revisao_atual()
    assert not banco_scratch.existe_tabela("administradores_plataforma")
    assert not ({"slug", "nome_fantasia"} & banco_scratch.colunas("empresas"))
    with banco_scratch.conectar() as conexao:
        assert conexao.execute("SELECT codigo_interno FROM empresas").fetchone() == ("DEMO",)
        assert conexao.execute("SELECT perfil_base, is_system_account FROM usuarios").fetchone() == ("admin", True)
        assert conexao.execute("SELECT logo_storage_key FROM configuracoes_personalizacao").fetchone() == (LOGO_KEY_DEMO,)


def test_backfill_trata_reservados_curtos_e_colisoes(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    codigos = [("e1", "ADMIN", "2026-01-01"), ("e2", "AB", "2026-01-02"), ("e3", "Acme Ltda", "2026-01-03"),
               ("e4", "ACME-LTDA", "2026-01-04"), ("e5", "Ação Ünica", "2026-01-05")]
    with banco_scratch.conectar() as conexao:
        for empresa_id, codigo, criado in codigos:
            conexao.execute(
                "INSERT INTO empresas (id, nome, codigo_interno, status, created_at, updated_at) "
                "VALUES (%s, %s, %s, 'ativa', %s, %s)",
                (empresa_id, f"Empresa {empresa_id}", codigo, criado, criado),
            )
    assert banco_scratch.alembic("upgrade", REV_0041).returncode == 0
    with banco_scratch.conectar() as conexao:
        slugs = dict(conexao.execute("SELECT id, slug FROM empresas").fetchall())
    assert len(set(slugs.values())) == 5  # únicos
    assert slugs["e1"] == "admin-empresa"  # reservado ganha sufixo
    assert slugs["e2"] == "ab-empresa"  # curto demais (<3) ganha sufixo
    assert slugs["e3"] == "acme-ltda" and slugs["e4"] == "acme-ltda-2"  # colisão -> sufixo numérico, mais antiga fica com a base
    assert slugs["e5"] == "acao-unica"  # acentos removidos


def test_constraints_do_banco_recusam_slug_invalido_e_duplicado(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_0041).returncode == 0

    def inserir(conexao, empresa_id: str, codigo: str, slug: str | None) -> None:
        conexao.execute(
            "INSERT INTO empresas (id, nome, codigo_interno, slug, status, created_at, updated_at) "
            "VALUES (%s, 'X', %s, %s, 'ativa', now(), now())",
            (empresa_id, codigo, slug),
        )

    with banco_scratch.conectar() as conexao:
        inserir(conexao, "ok-1", "OK1", "valido-1")
        for indice, ruim in enumerate(["ab", "x" * 41, "Maiuscula", "-borda", "borda-", "com_espaco", "plataforma", "api", "login",
                                       "logout", "admin", "suporte", None, "valido-1"]):
            with pytest.raises(psycopg.errors.Error):
                inserir(conexao, f"bad-{indice}", f"BAD{indice}", ruim)


def test_tabela_de_administradores_exige_um_por_usuario_e_revogacao_registrada(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    _semear_estado_de_producao(banco_scratch)
    assert banco_scratch.alembic("upgrade", REV_0041).returncode == 0
    with banco_scratch.conectar() as conexao:
        conexao.execute(
            "INSERT INTO administradores_plataforma (id, usuario_id, ativo, criado_em) VALUES ('adm-1', 'usr-1', true, now())"
        )
        with pytest.raises(psycopg.errors.UniqueViolation):
            conexao.execute(
                "INSERT INTO administradores_plataforma (id, usuario_id, ativo, criado_em) VALUES ('adm-2', 'usr-1', true, now())"
            )
        conexao.execute("UPDATE administradores_plataforma SET ativo = false, revogado_em = now() WHERE id = 'adm-1'")
        with pytest.raises(psycopg.errors.CheckViolation):  # inativo sem data de revogação
            conexao.execute("UPDATE administradores_plataforma SET revogado_em = NULL WHERE id = 'adm-1'")
        with pytest.raises(psycopg.errors.ForeignKeyViolation):  # usuário inexistente
            conexao.execute(
                "INSERT INTO administradores_plataforma (id, usuario_id, ativo, criado_em) VALUES ('adm-3', 'nao-existe', true, now())"
            )
