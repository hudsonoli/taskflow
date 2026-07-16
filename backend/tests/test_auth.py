from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import auth as auth_routes
from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import auth as auth_dependency
from app.domain.event_types import DomainEventType
from app.main import app
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.services.auth_service import AuthService


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


def empresa(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "nome": "Empresa Auth",
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


def usuario(empresa_id: str, **overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"USR-{uuid4().hex[:8]}",
        "nome": "Admin Auth",
        "email": "admin@empresa.com",
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


def credencial(usuario_id: str, senha: str = "SenhaAtual123", **overrides):
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


def create_auth_user(session_factory, *, empresa_status="ativa", user_status="ativo", acesso_sistema=True, with_credential=True):
    emp = persist(session_factory, empresa(codigo_interno="BOX", status=empresa_status))
    user = persist(session_factory, usuario(emp.id, status=user_status, acesso_sistema=acesso_sistema))
    cred = None
    if with_credential:
        cred = persist(session_factory, credencial(user.id))
    return emp, user, cred


def login_payload(**overrides):
    data = {"empresaCodigo": " box ", "email": " Admin@Empresa.COM ", "senha": "SenhaAtual123"}
    data.update(overrides)
    return data


def login(client, **overrides):
    return client.post("/auth/login", json=login_payload(**overrides))


def eventos(session_factory) -> list[Evento]:
    with session_factory() as db:
        return list(db.scalars(select(Evento).order_by(Evento.created_at)).all())


def get_credential(session_factory, usuario_id: str) -> UsuarioCredencial:
    with session_factory() as db:
        return db.scalars(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == usuario_id)).one()


def test_valid_login_returns_access_token(client):
    create_auth_user(client.session_factory)

    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["accessToken"]
    assert body["tokenType"] == "bearer"
    assert "senha" not in str(body).lower()
    assert "hash" not in str(body).lower()


def test_valid_login_normalizes_email_and_empresa_codigo(client):
    create_auth_user(client.session_factory)

    response = client.post(
        "/auth/login",
        json={"empresaCodigo": " box ", "email": " ADMIN@EMPRESA.COM ", "senha": "SenhaAtual123"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "setup_kwargs,payload_overrides",
    [
        ({}, {"empresaCodigo": "INEXISTENTE"}),
        ({"empresa_status": "inativa"}, {}),
        ({}, {"email": "naoexiste@empresa.com"}),
        ({}, {"senha": "senha-errada"}),
        ({"user_status": "inativo"}, {}),
        ({"user_status": "bloqueado"}, {}),
        ({"user_status": "arquivado"}, {}),
        ({"acesso_sistema": False}, {}),
        ({"with_credential": False}, {}),
    ],
)
def test_invalid_login_scenarios_return_generic_response(client, setup_kwargs, payload_overrides):
    create_auth_user(client.session_factory, **setup_kwargs)

    response = login(client, **payload_overrides)

    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciais inválidas"}
    assert "admin@empresa.com" not in str(response.json()).lower()


def test_failed_login_event_omits_email_and_sensitive_data(client):
    emp, user, _ = create_auth_user(client.session_factory)

    response = login(client, senha="senha-errada")

    assert response.status_code == 401
    auth_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.AUTH_LOGIN_FALHA.value]
    assert len(auth_events) == 1
    event = auth_events[0]
    assert event.empresa_id == emp.id
    assert event.usuario_id == user.id
    assert event.payload["empresa_id"] == emp.id
    assert event.payload["usuario_id"] == user.id
    assert event.payload["resultado"] == "falha"
    assert "email" not in event.payload
    assert "senha" not in str(event.payload).lower()
    assert "hash" not in str(event.payload).lower()


def test_failed_login_without_resolved_empresa_does_not_invent_event_ids(client):
    create_auth_user(client.session_factory)

    response = login(client, empresaCodigo="NAOEXISTE")

    assert response.status_code == 401
    assert [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.AUTH_LOGIN_FALHA.value] == []


def test_failed_attempts_lock_temporarily_and_success_after_expiry_clears_state(client):
    _, user, _ = create_auth_user(client.session_factory)

    for _ in range(3):
        assert login(client, senha="senha-errada").status_code == 401

    locked = get_credential(client.session_factory, user.id)
    assert locked.tentativas_falhas == 3
    assert locked.bloqueado_ate is not None
    assert login(client).status_code == 401

    with client.session_factory() as db:
        current = db.scalars(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == user.id)).one()
        current.bloqueado_ate = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    response = login(client)

    assert response.status_code == 200
    cleared = get_credential(client.session_factory, user.id)
    assert cleared.tentativas_falhas == 0
    assert cleared.bloqueado_ate is None


def test_auth_me_valid_token(client):
    _, user, _ = create_auth_user(client.session_factory)
    token = login(client).json()["accessToken"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "usuarioId": user.id,
        "empresaId": user.empresa_id,
        "nome": user.nome,
        "perfilBase": user.perfil_base,
        "acessoSistema": True,
        "status": "ativo",
    }
    assert "hash" not in str(response.json()).lower()
    assert "senha" not in str(response.json()).lower()
    assert "token" not in str(response.json()).lower()


def test_auth_me_without_token_returns_401(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_auth_me_invalid_token_returns_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer token-invalido"})

    assert response.status_code == 401


def test_auth_me_expired_token_returns_401(client, auth_settings):
    _, user, _ = create_auth_user(client.session_factory)
    token = create_access_token(
        sub=user.id,
        empresa_id=user.empresa_id,
        perfil_base=user.perfil_base,
        settings=auth_settings,
        expires_delta=timedelta(minutes=-1),
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_auth_me_revalidates_current_user_and_empresa_status(client):
    emp, user, _ = create_auth_user(client.session_factory)
    token = login(client).json()["accessToken"]
    with client.session_factory() as db:
        persisted = db.get(Empresa, emp.id)
        persisted.status = "inativa"
        db.commit()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_change_password_success_old_password_stops_working_new_password_works(client):
    _, user, _ = create_auth_user(client.session_factory)
    token = login(client).json()["accessToken"]

    response = client.post(
        "/auth/alterar-senha",
        json={"senhaAtual": "SenhaAtual123", "novaSenha": "NovaSenha123", "confirmacaoSenha": "NovaSenha123"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    assert login(client, senha="SenhaAtual123").status_code == 401
    assert login(client, senha="NovaSenha123").status_code == 200
    updated = get_credential(client.session_factory, user.id)
    assert updated.tentativas_falhas == 0
    assert updated.bloqueado_ate is None
    assert updated.senha_alterada_em is not None
    assert verify_password("NovaSenha123", updated.senha_hash)


def test_change_password_validates_current_password_confirmation_and_difference(client):
    create_auth_user(client.session_factory)
    token = login(client).json()["accessToken"]

    wrong_current = client.post(
        "/auth/alterar-senha",
        json={"senhaAtual": "errada", "novaSenha": "NovaSenha123", "confirmacaoSenha": "NovaSenha123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    same_password = client.post(
        "/auth/alterar-senha",
        json={"senhaAtual": "SenhaAtual123", "novaSenha": "SenhaAtual123", "confirmacaoSenha": "SenhaAtual123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    mismatch = client.post(
        "/auth/alterar-senha",
        json={"senhaAtual": "SenhaAtual123", "novaSenha": "NovaSenha123", "confirmacaoSenha": "OutraSenha123"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert wrong_current.status_code == 401
    assert wrong_current.json() == {"detail": "Credenciais inválidas"}
    assert same_password.status_code == 422
    assert mismatch.status_code == 422


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_change_password_rolls_back_when_event_publish_fails(session_factory, auth_settings):
    _, user, cred = create_auth_user(session_factory)
    service = AuthService(event_publisher=FailingPublisher(), settings=auth_settings)

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            persisted_user = db.get(Usuario, user.id)
            service.alterar_senha(
                db,
                usuario=persisted_user,
                senha_atual="SenhaAtual123",
                nova_senha="NovaSenha123",
                confirmacao_senha="NovaSenha123",
            )

    current = get_credential(session_factory, user.id)
    assert current.senha_hash == cred.senha_hash
    assert current.senha_alterada_em is None


def test_password_definition_rolls_back_when_event_publish_fails(session_factory, auth_settings):
    _, user, _ = create_auth_user(session_factory, with_credential=False)
    service = AuthService(event_publisher=FailingPublisher(), settings=auth_settings)

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.definir_senha_usuario(db, empresa_codigo="BOX", email=user.email, senha="SenhaNova123")

    with session_factory() as db:
        assert db.scalars(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == user.id)).first() is None
