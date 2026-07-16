from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial


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
        "nome": "Usuario Auth",
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


def credencial(usuario_id: str, **overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "usuario_id": usuario_id,
        "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$hash-de-teste",
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


def persist_usuario(session_factory) -> Usuario:
    emp = persist(session_factory, empresa())
    return persist(session_factory, usuario(emp.id))


def test_credential_persists_required_fields(session_factory):
    user = persist_usuario(session_factory)

    created = persist(session_factory, credencial(user.id))

    assert created.id
    assert created.usuario_id == user.id
    assert created.senha_hash
    assert created.senha_definida_em
    assert created.senha_alterada_em is None
    assert created.tentativas_falhas == 0
    assert created.bloqueado_ate is None
    assert created.created_at
    assert created.updated_at


def test_expected_columns_exist():
    assert set(UsuarioCredencial.__table__.columns.keys()) == {
        "id",
        "usuario_id",
        "senha_hash",
        "senha_definida_em",
        "senha_alterada_em",
        "tentativas_falhas",
        "bloqueado_ate",
        "created_at",
        "updated_at",
    }


def test_credential_is_unique_per_user(session_factory):
    user = persist_usuario(session_factory)
    persist(session_factory, credencial(user.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, credencial(user.id))


def test_user_fk_is_required(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, credencial(None))


def test_user_fk_must_reference_existing_user(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, credencial(str(uuid4())))


def test_senha_hash_is_required(session_factory):
    user = persist_usuario(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, credencial(user.id, senha_hash=None))


def test_tentativas_falhas_default_is_zero(session_factory):
    user = persist_usuario(session_factory)
    now = datetime.now(timezone.utc)
    created = UsuarioCredencial(
        id=str(uuid4()),
        usuario_id=user.id,
        senha_hash="$argon2id$v=19$m=65536,t=3,p=4$hash-de-teste",
        senha_definida_em=now,
        senha_alterada_em=None,
        bloqueado_ate=None,
        created_at=now,
        updated_at=now,
    )

    persisted = persist(session_factory, created)

    assert persisted.tentativas_falhas == 0


def test_bloqueado_ate_is_nullable(session_factory):
    user = persist_usuario(session_factory)
    created = persist(session_factory, credencial(user.id, bloqueado_ate=None))

    assert created.bloqueado_ate is None


def test_timestamps_are_persisted(session_factory):
    user = persist_usuario(session_factory)
    created = persist(session_factory, credencial(user.id))

    assert created.senha_definida_em is not None
    assert created.created_at is not None
    assert created.updated_at is not None


def test_user_creation_does_not_create_credential_automatically(session_factory):
    persist_usuario(session_factory)

    with session_factory() as db:
        assert db.query(UsuarioCredencial).count() == 0
