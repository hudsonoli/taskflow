"""Raiz da suíte de testes do backend.

CRÍTICO: a validação + cópia abaixo precisa rodar antes de qualquer `import app.*` (deste
arquivo ou de qualquer fixture/teste) — `app.core.config.get_settings()` é `@lru_cache`d e
lê `DATABASE_URL` do ambiente na primeira chamada; se algo importasse `app.*` antes disso, o
app inteiro ficaria permanentemente amarrado ao banco errado pelo resto do processo. Por
isso a ordem é: (1) ler DATABASE_URL_TEST, (2) validar nome exato + diferença da
DATABASE_URL de dev — `obter_url_teste_validada()` aborta com RuntimeError se qualquer
checagem falhar, (3) só então copiar pra DATABASE_URL. `tests/fixtures/database.py` não
importa nada de `app.*`, então importar essa validação aqui é seguro.
"""

import os

from tests.fixtures.database import obter_url_teste_validada

os.environ["DATABASE_URL"] = obter_url_teste_validada()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.empresa",
    "tests.fixtures.usuarios",
    "tests.fixtures.auth",
    "tests.fixtures.uploads",
]


@pytest.fixture()
def app(db_session: Session):
    """App real, com `get_db` trocado pra devolver a sessão transacional do teste (ver
    tests/fixtures/database.py) — nenhuma outra parte do app é mockada."""
    from app.db.session import get_db
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides[get_db] = lambda: db_session
    yield fastapi_app
    fastapi_app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client(app) -> TestClient:
    """Cliente HTTP anônimo (sem Authorization) — ponto de partida pros clientes
    autenticados de tests/fixtures/auth.py. Cada teste recebe uma instância nova: nenhum
    header fica configurado aqui além dos padrões do TestClient, então não há risco de um
    teste herdar Authorization de outro."""
    return TestClient(app)
