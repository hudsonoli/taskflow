"""Infra de banco para a suíte de testes — nunca toca no banco de desenvolvimento.

Trava de segurança: o nome do banco de `DATABASE_URL_TEST` precisa ser exatamente
`TEST_DB_NAME`. Se não bater, a suíte inteira aborta antes de qualquer `CREATE
DATABASE`/`alembic upgrade`/sessão ser aberta — não existe caminho de código aqui que rode
migration, truncate ou qualquer limpeza contra outro banco. Suporte a um banco por worker
(pytest-xdist) é só uma nota de evolução futura — não implementado nesta entrega.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

TEST_DB_NAME = "taskfloww_test"

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Mesma fonte que app/core/config.py usa (backend/.env) — carregado aqui porque a validação
# de DATABASE_URL_TEST precisa rodar ANTES de qualquer `import app.*` (que é quem
# normalmente dispara esse load_dotenv).
load_dotenv(BACKEND_DIR / ".env")

# Capturado UMA vez, neste import — antes que conftest.py sobrescreva DATABASE_URL com o
# valor de teste. `obter_url_teste_validada()` é chamada de novo mais tarde (pela fixture
# `test_database_url`, defesa em profundidade), quando `os.environ["DATABASE_URL"]` já foi
# trocado; comparar contra essa constante (e não reler `os.environ["DATABASE_URL"]` ao vivo)
# é o que evita o falso positivo "DATABASE_URL_TEST é igual a DATABASE_URL".
_DATABASE_URL_DEV_ORIGINAL = os.environ.get("DATABASE_URL")


def _extrair_nome_banco(database_url: str) -> str:
    return urlsplit(database_url).path.lstrip("/")


def obter_url_teste_validada() -> str:
    """Lê DATABASE_URL_TEST e valida o nome do banco.

    Levanta RuntimeError (aborta a coleta de testes) se a variável não estiver definida, se
    o nome do banco não for exatamente `taskfloww_test`, ou se apontar pro mesmo banco de
    `DATABASE_URL` (desenvolvimento) — únicas barreiras que impedem a suíte de rodar contra
    o banco de desenvolvimento por engano.
    """
    database_url = os.environ.get("DATABASE_URL_TEST")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL_TEST não está definida (ver backend/.env.example) — a suíte de "
            "testes recusa rodar sem um banco de teste explícito."
        )
    nome_banco = _extrair_nome_banco(database_url)
    if nome_banco != TEST_DB_NAME:
        raise RuntimeError(
            f"DATABASE_URL_TEST aponta para o banco '{nome_banco}', mas o único nome "
            f"aceito nesta entrega é '{TEST_DB_NAME}'. Abortando antes de rodar qualquer "
            "migration ou criar conexão — isso existe pra nunca rodar a suíte contra o "
            "banco de desenvolvimento por engano."
        )
    if _DATABASE_URL_DEV_ORIGINAL and _DATABASE_URL_DEV_ORIGINAL == database_url:
        raise RuntimeError(
            "DATABASE_URL_TEST é idêntica a DATABASE_URL (desenvolvimento) — abortando "
            "para nunca rodar a suíte de testes contra o banco de desenvolvimento."
        )
    return database_url


def _conexao_manutencao(database_url: str) -> psycopg.Connection:
    """Conexão autocommit na base `postgres` (manutenção) — CREATE DATABASE não roda
    dentro de uma transação, então autocommit é obrigatório aqui."""
    partes = urlsplit(database_url)
    conninfo = (
        f"host={partes.hostname} port={partes.port or 5432} "
        f"user={partes.username} password={partes.password} dbname=postgres"
    )
    conexao = psycopg.connect(conninfo)
    conexao.autocommit = True
    return conexao


def garantir_banco_teste_existe(database_url: str) -> None:
    nome_banco = _extrair_nome_banco(database_url)
    if nome_banco != TEST_DB_NAME:
        raise RuntimeError(f"Recusando criar/verificar banco não-teste: {nome_banco}")
    with _conexao_manutencao(database_url) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (nome_banco,))
            existe = cursor.fetchone() is not None
            if not existe:
                # Nome de banco não aceita parametrização em CREATE DATABASE — já validado
                # contra TEST_DB_NAME (== "taskfloww_test") acima, não é entrada livre.
                try:
                    cursor.execute(f'CREATE DATABASE "{nome_banco}"')
                except psycopg.errors.InsufficientPrivilege as exc:
                    raise RuntimeError(
                        f"O usuário do Postgres não tem permissão CREATEDB para criar "
                        f"'{nome_banco}'. Conceda CREATEDB a esse usuário (ou crie o banco "
                        "manualmente) — a suíte não tenta alterar permissões automaticamente."
                    ) from exc


def rodar_migrations(database_url: str) -> None:
    """`alembic upgrade head` como subprocesso, uma vez por sessão da suíte — não por
    teste. `migrations/env.py` já lê DATABASE_URL do ambiente, então só precisamos passar a
    URL de teste (revalidada aqui de novo, defesa em profundidade)."""
    nome_banco = _extrair_nome_banco(database_url)
    if nome_banco != TEST_DB_NAME:
        raise RuntimeError(f"Recusando rodar migrations contra banco não-teste: {nome_banco}")

    ambiente = {**os.environ, "DATABASE_URL": database_url}
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=ambiente,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade head falhou (banco de teste):\n{resultado.stdout}\n{resultado.stderr}"
        )


def _validar_suporte_a_create_savepoint() -> None:
    """Confirma que a versão instalada do SQLAlchemy aceita
    `join_transaction_mode="create_savepoint"` antes de qualquer teste depender disso — se
    não aceitar, aborta com uma mensagem clara em vez de deixar o `db_session` falhar com um
    TypeError obscuro no meio da suíte."""
    import inspect

    parametros = inspect.signature(Session.__init__).parameters
    if "join_transaction_mode" not in parametros:
        raise RuntimeError(
            "A versão instalada do SQLAlchemy não suporta "
            "Session(join_transaction_mode=...). Pare aqui — a alternativa (listener manual "
            "de after_transaction_end reabrindo SAVEPOINT) precisa ser aprovada antes de "
            "implementada, conforme o plano."
        )


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return obter_url_teste_validada()


@pytest.fixture(scope="session")
def test_engine(test_database_url: str) -> Engine:
    _validar_suporte_a_create_savepoint()
    garantir_banco_teste_existe(test_database_url)
    rodar_migrations(test_database_url)
    engine = create_engine(test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(test_engine: Engine):
    """Isolamento por teste: transação externa + sessão vinculada a ela em
    `join_transaction_mode="create_savepoint"` (API oficial do SQLAlchemy 2.0 pra este
    cenário). Se o código da aplicação chamar `db.commit()` (os services fazem isso), o
    SQLAlchemy abre um SAVEPOINT novo em vez de encerrar a transação externa — nada
    sobrevive ao `rollback()` final, nenhum teste depende de ordem de execução."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
