from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.empresa import Empresa
from app.models.usuario import Usuario


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)


def now() -> datetime:
    return datetime(2026, 7, 15, 15, tzinfo=timezone.utc)


def empresa(**overrides) -> Empresa:
    payload = {
        "id": str(uuid4()),
        "nome": "TaskFloww Agencia",
        "documento": str(uuid4()),
        "codigo_interno": f"EMP-{uuid4().hex[:8]}",
        "status": "ativa",
        "created_at": now(),
        "updated_at": now(),
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    payload.update(overrides)
    return Empresa(**payload)


def usuario(empresa_id: str, **overrides) -> Usuario:
    payload = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"USR-{uuid4().hex[:8]}",
        "nome": "Joao Silva",
        "email": f"usuario-{uuid4().hex[:8]}@taskfloww.local",
        "perfil_base": "operador",
        "status": "ativo",
        "created_at": now(),
        "updated_at": now(),
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    payload.update(overrides)
    return Usuario(**payload)


def create_empresa(session_factory, **overrides) -> Empresa:
    item = empresa(**overrides)
    with session_factory() as db:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item


def persist_usuario(session_factory, item: Usuario) -> Usuario:
    with session_factory() as db:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item


def test_usuario_model_persists_required_fields(session_factory):
    empresa_item = create_empresa(session_factory)
    created = persist_usuario(session_factory, usuario(empresa_item.id))

    with session_factory() as db:
        persisted = db.get(Usuario, created.id)
        assert persisted is not None
        assert persisted.empresa_id == empresa_item.id
        assert persisted.nome == "Joao Silva"
        assert persisted.perfil_base == "operador"
        assert persisted.status == "ativo"
        assert persisted.acesso_sistema is True


def test_usuario_table_has_expected_columns(session_factory):
    with session_factory() as db:
        columns = {column["name"] for column in inspect(db.bind).get_columns("usuarios")}

    assert {
        "id",
        "empresa_id",
        "codigo_interno",
        "nome",
        "email",
        "perfil_base",
        "acesso_sistema",
        "status",
        "created_at",
        "updated_at",
        "inativado_at",
        "inativado_por_usuario_id",
        "motivo_inativacao",
    }.issubset(columns)


def test_empresa_id_is_required(session_factory):
    with pytest.raises(IntegrityError):
        persist_usuario(session_factory, usuario(empresa_id=None))


def test_empresa_id_must_reference_existing_empresa(session_factory):
    with pytest.raises(IntegrityError):
        persist_usuario(session_factory, usuario(str(uuid4())))


def test_first_usuario_can_be_created_without_inativado_por_usuario_id(session_factory):
    empresa_item = create_empresa(session_factory)
    created = persist_usuario(session_factory, usuario(empresa_item.id, inativado_por_usuario_id=None))

    assert created.inativado_por_usuario_id is None


def test_inativado_por_usuario_id_references_usuario_when_informed(session_factory):
    empresa_item = create_empresa(session_factory)
    actor = persist_usuario(session_factory, usuario(empresa_item.id, codigo_interno="USR-A", email="actor@taskfloww.local"))
    inactive = persist_usuario(
        session_factory,
        usuario(
            empresa_item.id,
            codigo_interno="USR-B",
            email="inactive@taskfloww.local",
            status="inativo",
            inativado_at=now(),
            inativado_por_usuario_id=actor.id,
            motivo_inativacao="teste",
        ),
    )

    assert inactive.inativado_por_usuario_id == actor.id


def test_inativado_por_usuario_id_rejects_missing_usuario(session_factory):
    empresa_item = create_empresa(session_factory)

    with pytest.raises(IntegrityError):
        persist_usuario(session_factory, usuario(empresa_item.id, inativado_por_usuario_id=str(uuid4())))


def test_codigo_interno_is_unique_per_empresa(session_factory):
    empresa_item = create_empresa(session_factory)
    persist_usuario(session_factory, usuario(empresa_item.id, codigo_interno="USR-1", email="um@taskfloww.local"))

    with pytest.raises(IntegrityError):
        persist_usuario(session_factory, usuario(empresa_item.id, codigo_interno="USR-1", email="dois@taskfloww.local"))


def test_codigo_interno_can_repeat_in_different_empresas(session_factory):
    first_empresa = create_empresa(session_factory, codigo_interno="EMP-1")
    second_empresa = create_empresa(session_factory, codigo_interno="EMP-2")

    first = persist_usuario(session_factory, usuario(first_empresa.id, codigo_interno="USR-1", email="um@taskfloww.local"))
    second = persist_usuario(session_factory, usuario(second_empresa.id, codigo_interno="USR-1", email="dois@taskfloww.local"))

    assert first.codigo_interno == second.codigo_interno
    assert first.empresa_id != second.empresa_id


def test_email_is_unique_per_empresa(session_factory):
    empresa_item = create_empresa(session_factory)
    email = "usuario@taskfloww.local"
    persist_usuario(session_factory, usuario(empresa_item.id, codigo_interno="USR-1", email=email))

    with pytest.raises(IntegrityError):
        persist_usuario(session_factory, usuario(empresa_item.id, codigo_interno="USR-2", email=email))


def test_same_email_is_allowed_in_different_empresas(session_factory):
    first_empresa = create_empresa(session_factory, codigo_interno="EMP-1")
    second_empresa = create_empresa(session_factory, codigo_interno="EMP-2")
    email = "usuario@taskfloww.local"

    first = persist_usuario(session_factory, usuario(first_empresa.id, codigo_interno="USR-1", email=email))
    second = persist_usuario(session_factory, usuario(second_empresa.id, codigo_interno="USR-1", email=email))

    assert first.email == second.email
    assert first.empresa_id != second.empresa_id


@pytest.mark.parametrize("perfil_base", ["admin", "gestor", "operador"])
def test_allowed_perfil_base_values(session_factory, perfil_base):
    empresa_item = create_empresa(session_factory)

    created = persist_usuario(session_factory, usuario(empresa_item.id, perfil_base=perfil_base))

    assert created.perfil_base == perfil_base


def test_invalid_perfil_base_is_rejected(session_factory):
    empresa_item = create_empresa(session_factory)

    with pytest.raises(IntegrityError):
        persist_usuario(session_factory, usuario(empresa_item.id, perfil_base="cliente"))


@pytest.mark.parametrize("status", ["ativo", "inativo", "bloqueado", "arquivado"])
def test_allowed_status_values(session_factory, status):
    empresa_item = create_empresa(session_factory)

    created = persist_usuario(session_factory, usuario(empresa_item.id, status=status))

    assert created.status == status


def test_invalid_status_is_rejected(session_factory):
    empresa_item = create_empresa(session_factory)

    with pytest.raises(IntegrityError):
        persist_usuario(session_factory, usuario(empresa_item.id, status="suspenso"))


def test_acesso_sistema_can_be_false(session_factory):
    empresa_item = create_empresa(session_factory)

    created = persist_usuario(session_factory, usuario(empresa_item.id, acesso_sistema=False))

    assert created.acesso_sistema is False


def test_nome_is_required(session_factory):
    empresa_item = create_empresa(session_factory)

    with pytest.raises(IntegrityError):
        persist_usuario(session_factory, usuario(empresa_item.id, nome=None))


def test_email_is_required(session_factory):
    empresa_item = create_empresa(session_factory)

    with pytest.raises(IntegrityError):
        persist_usuario(session_factory, usuario(empresa_item.id, email=None))
