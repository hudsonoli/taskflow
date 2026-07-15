from fastapi.testclient import TestClient

from app.api.routes import status
from app.main import app


client = TestClient(app)


def test_imports_modular_app():
    assert app.title == "Taskfloww API"


def test_root_route_contract():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Bem-vindo ao Taskfloww API"}


def test_health_route_contract():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, statement):
        return None


class FakeEngine:
    def connect(self):
        return FakeConnection()


class FakeRedisClient:
    def __init__(self, ping_result=True):
        self.ping_result = ping_result

    def ping(self):
        return self.ping_result


def test_status_route_online_contract(monkeypatch):
    monkeypatch.setattr(status, "get_engine", lambda: FakeEngine())
    monkeypatch.setattr(status, "get_redis_client", lambda: FakeRedisClient(True))

    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {
        "api": "online",
        "database": "online",
        "redis": "online",
    }


def test_status_route_redis_ping_false_contract(monkeypatch):
    monkeypatch.setattr(status, "get_engine", lambda: FakeEngine())
    monkeypatch.setattr(status, "get_redis_client", lambda: FakeRedisClient(False))

    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {
        "api": "online",
        "database": "online",
        "redis": "offline",
    }


def test_status_route_database_error_contract(monkeypatch):
    monkeypatch.setattr(
        status,
        "get_engine",
        lambda: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    monkeypatch.setattr(status, "get_redis_client", lambda: FakeRedisClient(True))

    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {
        "api": "online",
        "database": "offline",
        "redis": "unknown",
        "error": "database unavailable",
    }
