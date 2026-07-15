from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.agencia import Agencia
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
        "nome": "Empresa Modelo",
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
        "nome": "Usuario Modelo",
        "email": f"usuario-{uuid4().hex[:8]}@empresa.com",
        "perfil_base": "operador",
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


def agencia(empresa_id: str, **overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"AG-{uuid4().hex[:8]}",
        "nome": f"Agencia {uuid4().hex[:8]}",
        "sigla": "AG",
        "descricao": "Agencia de teste",
        "status": "ativa",
        "created_at": now,
        "updated_at": now,
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Agencia(**data)


def persist(session_factory, *objects):
    with session_factory() as db:
        db.add_all(objects)
        db.commit()
        for obj in objects:
            db.refresh(obj)
        return objects[0] if len(objects) == 1 else objects


def test_agencia_persists_required_fields(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, agencia(emp.id, codigo_interno="AG-001", nome="Agencia Centro", sigla="CTR"))

    assert created.id
    assert created.empresa_id == emp.id
    assert created.codigo_interno == "AG-001"
    assert created.nome == "Agencia Centro"
    assert created.sigla == "CTR"
    assert created.status == "ativa"
    assert created.created_at
    assert created.updated_at


def test_expected_columns_exist():
    columns = set(Agencia.__table__.columns.keys())

    assert columns == {
        "id",
        "empresa_id",
        "codigo_interno",
        "nome",
        "sigla",
        "descricao",
        "status",
        "created_at",
        "updated_at",
        "inativado_at",
        "motivo_inativacao",
        "inativado_por_usuario_id",
    }


def test_empresa_id_is_required(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, agencia(None))


def test_empresa_id_must_reference_existing_empresa(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, agencia(str(uuid4())))


def test_codigo_interno_unique_per_empresa(session_factory):
    emp = persist(session_factory, empresa())
    persist(session_factory, agencia(emp.id, codigo_interno="AG-DUP"))

    with pytest.raises(IntegrityError):
        persist(session_factory, agencia(emp.id, codigo_interno="AG-DUP"))


def test_codigo_interno_can_repeat_in_different_empresas(session_factory):
    emp_a, emp_b = persist(session_factory, empresa(), empresa(documento=uuid4().hex))

    first = persist(session_factory, agencia(emp_a.id, codigo_interno="AG-001"))
    second = persist(session_factory, agencia(emp_b.id, codigo_interno="AG-001"))

    assert first.codigo_interno == second.codigo_interno
    assert first.empresa_id != second.empresa_id


def test_nome_unique_per_empresa(session_factory):
    emp = persist(session_factory, empresa())
    persist(session_factory, agencia(emp.id, nome="Agencia Norte"))

    with pytest.raises(IntegrityError):
        persist(session_factory, agencia(emp.id, nome="Agencia Norte"))


def test_nome_can_repeat_in_different_empresas(session_factory):
    emp_a, emp_b = persist(session_factory, empresa(), empresa(documento=uuid4().hex))

    first = persist(session_factory, agencia(emp_a.id, nome="Agencia Compartilhada"))
    second = persist(session_factory, agencia(emp_b.id, nome="Agencia Compartilhada"))

    assert first.nome == second.nome
    assert first.empresa_id != second.empresa_id


@pytest.mark.parametrize("status", ["ativa", "inativa", "arquivada"])
def test_allowed_status_values(session_factory, status):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, agencia(emp.id, status=status))

    assert created.status == status


def test_invalid_status_is_rejected(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, agencia(emp.id, status="bloqueada"))


def test_soft_delete_fields_can_reference_user(session_factory):
    emp = persist(session_factory, empresa())
    actor = persist(session_factory, usuario(emp.id))
    now = datetime.now(timezone.utc)

    created = persist(
        session_factory,
        agencia(
            emp.id,
            status="inativa",
            inativado_at=now,
            motivo_inativacao="encerramento",
            inativado_por_usuario_id=actor.id,
        ),
    )

    assert created.status == "inativa"
    assert created.inativado_at
    assert created.motivo_inativacao == "encerramento"
    assert created.inativado_por_usuario_id == actor.id


def test_inativado_por_usuario_id_can_be_null(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, agencia(emp.id, inativado_por_usuario_id=None))

    assert created.inativado_por_usuario_id is None


def test_inativado_por_usuario_id_must_reference_existing_usuario(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, agencia(emp.id, inativado_por_usuario_id=str(uuid4())))
