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
os.environ["EXPEDIENTE_TICK_HABILITADO"] = "false"  # a suíte não sobe o tick em background (os testes chamam o serviço direto, com relógio injetado)

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


@pytest.fixture(autouse=True)
def _relogio_do_expediente_fixo(monkeypatch):
    """O "agora" do EXPEDIENTE (gate de trabalho, janelas, tick) é fixo por padrão: segunda-feira 2026-10-05, 10:00 em America/Sao_Paulo, DENTRO do padrão 09–12/14–19. A suíte
    não pode depender da hora (nem do dia da semana) da máquina — o gate de trabalho também vale para abrir sessão (Fase 3). Testes que precisam de outro horário
    sobrescrevem com `monkeypatch.setattr("app.core.expediente.agora_utc", ...)` (fixture `relogio`)."""
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    instante = datetime(2026, 10, 5, 10, 0, tzinfo=ZoneInfo("America/Sao_Paulo")).astimezone(timezone.utc)
    monkeypatch.setattr("app.core.expediente.agora_utc", lambda: instante)
    yield


@pytest.fixture(autouse=True)
def _cache_regra_expediente_limpo():
    """O gate de expediente guarda a regra por empresa por alguns segundos (cache em memória do processo). Cada teste começa e termina sem esse estado."""
    from app.services.regra_expediente_service import invalidar_cache_regra

    invalidar_cache_regra()
    yield
    invalidar_cache_regra()


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
