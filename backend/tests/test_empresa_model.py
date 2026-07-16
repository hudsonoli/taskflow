from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.empresa import Empresa


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)


def now() -> datetime:
    return datetime(2026, 7, 15, 14, tzinfo=timezone.utc)


def empresa(**overrides) -> Empresa:
    payload = {
        "id": str(uuid4()),
        "nome": "TaskFloww Agencia",
        "documento": "00000000000100",
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


def persist(session_factory, item: Empresa) -> Empresa:
    with session_factory() as db:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item


def test_empresa_model_persists_required_fields(session_factory):
    created = persist(session_factory, empresa())

    with session_factory() as db:
        persisted = db.get(Empresa, created.id)
        assert persisted is not None
        assert persisted.nome == "TaskFloww Agencia"
        assert persisted.status == "ativa"
        assert persisted.codigo_interno == created.codigo_interno


def test_empresa_table_has_expected_columns(session_factory):
    with session_factory() as db:
        columns = {column["name"] for column in inspect(db.bind).get_columns("empresas")}

    assert {
        "id",
        "nome",
        "documento",
        "codigo_interno",
        "status",
        "created_at",
        "updated_at",
        "inativado_at",
        "inativado_por_usuario_id",
        "motivo_inativacao",
    }.issubset(columns)


def test_codigo_interno_is_unique(session_factory):
    codigo = "EMP-UNICA"
    persist(session_factory, empresa(codigo_interno=codigo, documento="00000000000100"))

    with pytest.raises(IntegrityError):
        persist(session_factory, empresa(codigo_interno=codigo, documento="00000000000200"))


def test_documento_is_unique_when_informed(session_factory):
    documento = "00000000000100"
    persist(session_factory, empresa(codigo_interno="EMP-1", documento=documento))

    with pytest.raises(IntegrityError):
        persist(session_factory, empresa(codigo_interno="EMP-2", documento=documento))


def test_documento_allows_multiple_nulls(session_factory):
    first = persist(session_factory, empresa(codigo_interno="EMP-1", documento=None))
    second = persist(session_factory, empresa(codigo_interno="EMP-2", documento=None))

    with session_factory() as db:
        empresas = list(db.scalars(select(Empresa).order_by(Empresa.codigo_interno)).all())

    assert [item.id for item in empresas] == [first.id, second.id]


def test_status_constraint_rejects_invalid_value(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, empresa(status="suspensa"))


def test_nome_is_required(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, empresa(nome=None))
