from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.domain.event_types import DomainEventType
from app.main import app
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.schemas.empresa import EmpresaCreate
from app.services.empresa_service import EmpresaService


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


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.session_factory = session_factory
        yield test_client
    app.dependency_overrides.clear()


def payload(**overrides):
    data = {
        "nome": "TaskFloww Agencia",
        "documento": "00000000000100",
        "codigoInterno": f"EMP-{uuid4().hex[:8]}",
    }
    data.update(overrides)
    return data


def create_empresa(client, **overrides):
    response = client.post("/empresas", json=payload(**overrides))
    assert response.status_code == 201
    return response.json()


def eventos(session_factory) -> list[Evento]:
    with session_factory() as db:
        return list(db.scalars(select(Evento).order_by(Evento.created_at)).all())


def empresas(session_factory) -> list[Empresa]:
    with session_factory() as db:
        return list(db.scalars(select(Empresa)).all())


def test_create_empresa(client):
    empresa = create_empresa(client)

    assert empresa["id"]
    assert empresa["nome"] == "TaskFloww Agencia"
    assert empresa["documento"] == "00000000000100"
    assert empresa["codigoInterno"].startswith("EMP-")
    assert empresa["status"] == "ativa"
    assert empresa["createdAt"]
    assert empresa["updatedAt"]


def test_list_empresas(client):
    first = create_empresa(client, nome="Empresa A", codigoInterno="EMP-A")
    second = create_empresa(client, nome="Empresa B", codigoInterno="EMP-B", documento="00000000000200")

    response = client.get("/empresas")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert first["id"] in ids
    assert second["id"] in ids


def test_list_empresas_filters_by_status(client):
    active = create_empresa(client, codigoInterno="EMP-ATIVA")
    inactive = create_empresa(client, codigoInterno="EMP-INATIVA", documento="00000000000200")
    client.post(f"/empresas/{inactive['id']}/inativar", json={"motivoInativacao": "teste"})

    response = client.get("/empresas", params={"status": "ativa"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [active["id"]]


def test_get_empresa_by_id(client):
    created = create_empresa(client)

    response = client.get(f"/empresas/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_empresa_by_id_returns_404(client):
    response = client.get(f"/empresas/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Empresa não encontrada"}


def test_update_nome_and_documento(client):
    created = create_empresa(client)

    response = client.patch(
        f"/empresas/{created['id']}",
        json={"nome": "TaskFloww Atualizada", "documento": "00000000000999"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["nome"] == "TaskFloww Atualizada"
    assert updated["documento"] == "00000000000999"
    assert updated["codigoInterno"] == created["codigoInterno"]


def test_patch_rejects_status_change(client):
    created = create_empresa(client)

    response = client.patch(f"/empresas/{created['id']}", json={"status": "inativa"})

    assert response.status_code == 422
    assert "status" in response.json()["detail"]


def test_codigo_interno_duplicate_is_rejected(client):
    create_empresa(client, codigoInterno="EMP-DUP")

    response = client.post("/empresas", json=payload(codigoInterno="EMP-DUP", documento="00000000000200"))

    assert response.status_code == 409
    assert response.json() == {"detail": "codigoInterno já cadastrado"}


def test_documento_duplicate_is_rejected(client):
    create_empresa(client, codigoInterno="EMP-1", documento="00000000000100")

    response = client.post("/empresas", json=payload(codigoInterno="EMP-2", documento="00000000000100"))

    assert response.status_code == 409
    assert response.json() == {"detail": "documento já cadastrado"}


def test_documento_null_is_allowed_for_multiple_empresas(client):
    first = create_empresa(client, codigoInterno="EMP-1", documento=None)
    second = create_empresa(client, codigoInterno="EMP-2", documento=None)

    assert first["documento"] is None
    assert second["documento"] is None


def test_inativar_empresa(client):
    created = create_empresa(client)

    response = client.post(
        f"/empresas/{created['id']}/inativar",
        json={"motivoInativacao": "encerramento operacional", "actorUsuarioId": "user-1"},
    )

    assert response.status_code == 200
    empresa = response.json()
    assert empresa["status"] == "inativa"
    assert empresa["inativadoAt"]
    assert empresa["inativadoPorUsuarioId"] == "user-1"
    assert empresa["motivoInativacao"] == "encerramento operacional"


def test_reativar_empresa(client):
    created = create_empresa(client)
    client.post(f"/empresas/{created['id']}/inativar", json={"motivoInativacao": "teste"})

    response = client.post(f"/empresas/{created['id']}/reativar")

    assert response.status_code == 200
    empresa = response.json()
    assert empresa["status"] == "ativa"
    assert empresa["inativadoAt"] is None
    assert empresa["inativadoPorUsuarioId"] is None
    assert empresa["motivoInativacao"] is None


def test_reactivate_active_empresa_is_rejected(client):
    created = create_empresa(client)

    response = client.post(f"/empresas/{created['id']}/reativar")

    assert response.status_code == 409
    assert response.json() == {"detail": "Empresa já está ativa"}


def test_inactivate_inactive_empresa_is_rejected(client):
    created = create_empresa(client)
    client.post(f"/empresas/{created['id']}/inativar", json={"motivoInativacao": "teste"})

    response = client.post(f"/empresas/{created['id']}/inativar", json={"motivoInativacao": "teste"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Empresa já está inativa"}


def test_delete_route_does_not_exist(client):
    created = create_empresa(client)

    response = client.delete(f"/empresas/{created['id']}")

    assert response.status_code == 405


def test_emits_create_update_inactivate_and_reactivate_events(client):
    created = create_empresa(client, codigoInterno="EMP-EVENTOS")
    client.patch(f"/empresas/{created['id']}", json={"nome": "Empresa Alterada"})
    client.post(f"/empresas/{created['id']}/inativar", json={"motivoInativacao": "teste"})
    client.post(f"/empresas/{created['id']}/reativar")

    persisted_events = eventos(client.session_factory)
    event_types = [evento.tipo for evento in persisted_events]

    assert event_types == [
        DomainEventType.EMPRESA_CRIADA.value,
        DomainEventType.EMPRESA_ALTERADA.value,
        DomainEventType.EMPRESA_INATIVADA.value,
        DomainEventType.EMPRESA_REATIVADA.value,
    ]
    assert all(evento.entidade_tipo == "empresa" for evento in persisted_events)
    assert all(evento.empresa_id == created["id"] for evento in persisted_events)


def test_documento_is_not_in_event_payload(client):
    created = create_empresa(client, documento="00000000000100")
    client.patch(f"/empresas/{created['id']}", json={"documento": "00000000000200"})

    for evento in eventos(client.session_factory):
        assert "documento" not in evento.payload


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_create_rolls_back_when_event_publish_fails(session_factory):
    service = EmpresaService(event_publisher=FailingPublisher())
    data = EmpresaCreate(nome="Empresa Rollback", documento="00000000000100", codigoInterno="EMP-ROLLBACK")

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.create_empresa(db, data)

    assert empresas(session_factory) == []
    assert eventos(session_factory) == []
