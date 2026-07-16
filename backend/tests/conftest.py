from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import auth as auth_routes
from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import auth as auth_dependency
from app.main import app
from app.models.agencia import Agencia
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.services.auth_service import AuthService

TEST_PASSWORD = "SenhaAtual123"


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def auth_settings():
    return Settings(
        auth_secret_key="test-auth-secret",
        auth_algorithm="HS256",
        auth_access_token_expire_minutes=30,
        auth_max_failed_attempts=3,
        auth_lockout_minutes=15,
    )


@pytest.fixture()
def client(session_factory, auth_settings, monkeypatch):
    service = AuthService(settings=auth_settings)
    monkeypatch.setattr(auth_routes, "auth_service", service)
    monkeypatch.setattr(auth_dependency, "auth_service", service)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.session_factory = session_factory
        test_client.auth_settings = auth_settings
        yield test_client
    app.dependency_overrides.clear()


def make_empresa(**overrides) -> Empresa:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "nome": "Empresa Teste",
        "documento": uuid4().hex,
        "codigo_interno": f"EMP-{uuid4().hex[:8]}",
        "status": "ativa",
        "created_at": now,
        "updated_at": now,
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    data.update(overrides)
    return Empresa(**data)


def make_usuario(empresa_id: str, **overrides) -> Usuario:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"USR-{uuid4().hex[:8]}",
        "nome": "Usuario Teste",
        "email": f"usuario-{uuid4().hex[:8]}@empresa.com",
        "perfil_base": "admin",
        "acesso_sistema": True,
        "status": "ativo",
        "created_at": now,
        "updated_at": now,
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    data.update(overrides)
    return Usuario(**data)


def make_credencial(usuario_id: str, senha: str = TEST_PASSWORD, **overrides) -> UsuarioCredencial:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "usuario_id": usuario_id,
        "senha_hash": hash_password(senha),
        "senha_definida_em": now,
        "senha_alterada_em": None,
        "tentativas_falhas": 0,
        "bloqueado_ate": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return UsuarioCredencial(**data)


def persist(session_factory, *objects):
    with session_factory() as db:
        db.add_all(objects)
        db.commit()
        for obj in objects:
            db.refresh(obj)
        return objects[0] if len(objects) == 1 else objects


def create_auth_context(session_factory, *, perfil_base="admin", empresa_status="ativa", user_status="ativo", acesso_sistema=True):
    empresa = make_empresa(codigo_interno=f"BOX-{uuid4().hex[:6].upper()}", status=empresa_status)
    usuario = make_usuario(
        empresa.id,
        perfil_base=perfil_base,
        status=user_status,
        acesso_sistema=acesso_sistema,
        email=f"{perfil_base}-{uuid4().hex[:8]}@empresa.com",
    )
    credencial = make_credencial(usuario.id)
    return persist(session_factory, empresa, usuario, credencial)


def auth_headers(client, usuario: Usuario, empresa: Empresa, senha: str = TEST_PASSWORD) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"empresaCodigo": empresa.codigo_interno, "email": usuario.email, "senha": senha},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


def persist_agencia(session_factory, empresa_id: str, **overrides) -> Agencia:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"AG-{uuid4().hex[:8]}",
        "nome": f"Agencia {uuid4().hex[:8]}",
        "sigla": "AG",
        "descricao": "Unidade operacional",
        "status": "ativa",
        "created_at": now,
        "updated_at": now,
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return persist(session_factory, Agencia(**data))


def eventos(session_factory) -> list[Evento]:
    with session_factory() as db:
        return list(db.scalars(select(Evento).order_by(Evento.created_at)).all())
