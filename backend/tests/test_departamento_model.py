from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.schemas.departamento import DepartamentoUpdate


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


def now() -> datetime:
    return datetime.now(timezone.utc)


def empresa(**overrides):
    data = {
        "id": str(uuid4()),
        "nome": "Empresa Modelo",
        "documento": uuid4().hex,
        "codigo_interno": f"EMP-{uuid4().hex[:8]}",
        "status": "ativa",
        "created_at": now(),
        "updated_at": now(),
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    data.update(overrides)
    return Empresa(**data)


def usuario(empresa_id: str, **overrides):
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"USR-{uuid4().hex[:8]}",
        "nome": "Usuario Modelo",
        "email": f"usuario-{uuid4().hex[:8]}@empresa.com",
        "perfil_base": "operador",
        "acesso_sistema": True,
        "status": "ativo",
        "created_at": now(),
        "updated_at": now(),
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    data.update(overrides)
    return Usuario(**data)


def departamento(empresa_id: str, **overrides):
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"DEP-{uuid4().hex[:8]}",
        "nome": f"Departamento {uuid4().hex[:8]}",
        "descricao": "Departamento de teste",
        "status": "ativa",
        "created_at": now(),
        "updated_at": now(),
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Departamento(**data)


def persist(session_factory, *objects):
    with session_factory() as db:
        db.add_all(objects)
        db.commit()
        for obj in objects:
            db.refresh(obj)
        return objects[0] if len(objects) == 1 else objects


def test_departamento_persists_required_fields(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, departamento(emp.id, codigo_interno="DEP-001", nome="Atendimento"))

    assert created.id
    assert created.empresa_id == emp.id
    assert created.codigo_interno == "DEP-001"
    assert created.nome == "Atendimento"
    assert created.status == "ativa"
    assert Departamento.__table__.c.created_at.type.timezone is True
    assert Departamento.__table__.c.updated_at.type.timezone is True


def test_model_is_registered_in_base_metadata():
    assert "departamentos" in Base.metadata.tables


def test_expected_columns_exist_and_email_does_not_exist():
    columns = set(Departamento.__table__.columns.keys())

    assert columns == {
        "id",
        "empresa_id",
        "codigo_interno",
        "nome",
        "descricao",
        "status",
        "created_at",
        "updated_at",
        "inativado_at",
        "motivo_inativacao",
        "inativado_por_usuario_id",
    }
    assert "email" not in columns


def test_empresa_id_is_required(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, departamento(None))


def test_empresa_id_must_reference_existing_empresa(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, departamento(str(uuid4())))


def test_inativado_por_usuario_id_must_reference_existing_usuario(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, departamento(emp.id, inativado_por_usuario_id=str(uuid4())))


def test_inativado_por_usuario_id_can_reference_usuario(session_factory):
    emp = persist(session_factory, empresa())
    actor = persist(session_factory, usuario(emp.id))
    created = persist(
        session_factory,
        departamento(
            emp.id,
            status="inativa",
            inativado_at=now(),
            motivo_inativacao="encerramento",
            inativado_por_usuario_id=actor.id,
        ),
    )

    assert created.inativado_por_usuario_id == actor.id


def test_codigo_interno_unique_per_empresa(session_factory):
    emp = persist(session_factory, empresa())
    persist(session_factory, departamento(emp.id, codigo_interno="DEP-DUP"))

    with pytest.raises(IntegrityError):
        persist(session_factory, departamento(emp.id, codigo_interno="DEP-DUP"))


def test_codigo_interno_can_repeat_in_different_empresas(session_factory):
    emp_a, emp_b = persist(session_factory, empresa(), empresa(documento=uuid4().hex))

    first = persist(session_factory, departamento(emp_a.id, codigo_interno="DEP-001"))
    second = persist(session_factory, departamento(emp_b.id, codigo_interno="DEP-001"))

    assert first.codigo_interno == second.codigo_interno
    assert first.empresa_id != second.empresa_id


def test_nome_unique_per_empresa(session_factory):
    emp = persist(session_factory, empresa())
    persist(session_factory, departamento(emp.id, nome="Atendimento"))

    with pytest.raises(IntegrityError):
        persist(session_factory, departamento(emp.id, nome="Atendimento"))


def test_nome_can_repeat_in_different_empresas(session_factory):
    emp_a, emp_b = persist(session_factory, empresa(), empresa(documento=uuid4().hex))

    first = persist(session_factory, departamento(emp_a.id, nome="Midia"))
    second = persist(session_factory, departamento(emp_b.id, nome="Midia"))

    assert first.nome == second.nome
    assert first.empresa_id != second.empresa_id


def test_nome_empty_is_rejected(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, departamento(emp.id, nome="   "))


def test_codigo_interno_empty_is_rejected(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, departamento(emp.id, codigo_interno="   "))


@pytest.mark.parametrize("status", ["ativa", "inativa", "arquivada"])
def test_allowed_status_values(session_factory, status):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, departamento(emp.id, status=status))

    assert created.status == status


def test_invalid_status_is_rejected(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, departamento(emp.id, status="bloqueada"))


def test_descricao_can_be_null(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, departamento(emp.id, descricao=None))

    assert created.descricao is None


def test_inativacao_fields_can_be_null(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(
        session_factory,
        departamento(
            emp.id,
            inativado_at=None,
            motivo_inativacao=None,
            inativado_por_usuario_id=None,
        ),
    )

    assert created.inativado_at is None
    assert created.motivo_inativacao is None
    assert created.inativado_por_usuario_id is None


def test_departamento_update_rejects_forbidden_fields():
    forbidden = [
        "empresaId",
        "status",
        "createdAt",
        "updatedAt",
        "inativadoAt",
        "motivoInativacao",
        "inativadoPorUsuarioId",
    ]

    for field in forbidden:
        with pytest.raises(ValidationError):
            DepartamentoUpdate.model_validate({field: "valor"})
