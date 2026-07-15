from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Evento


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def make_payload(**overrides):
    payload = {
        "empresaId": "empresa-1",
        "agenciaId": "agencia-principal",
        "tipo": "demanda.criada",
        "entidadeTipo": "demanda",
        "entidadeId": "demanda-1",
        "usuarioId": "user-2",
        "payload": {"nome": "Campanha Julho", "prioridade": "alta"},
        "metadata": {"origem": "teste"},
    }
    payload.update(overrides)
    return payload


def create_evento(client, **overrides):
    response = client.post("/eventos", json=make_payload(**overrides))
    assert response.status_code == 201
    return response.json()


def test_create_evento(client):
    evento = create_evento(client)

    assert evento["id"]
    assert evento["empresaId"] == "empresa-1"
    assert evento["agenciaId"] == "agencia-principal"
    assert evento["tipo"] == "demanda.criada"
    assert evento["entidadeTipo"] == "demanda"
    assert evento["entidadeId"] == "demanda-1"
    assert evento["usuarioId"] == "user-2"
    assert evento["payload"] == {"nome": "Campanha Julho", "prioridade": "alta"}
    assert evento["metadata"] == {"origem": "teste"}
    assert evento["occurredAt"]
    assert evento["createdAt"]


def test_create_evento_accepts_informed_occurred_at(client):
    occurred_at = "2026-07-11T10:00:00+00:00"
    evento = create_evento(client, occurredAt=occurred_at)

    assert evento["occurredAt"] == "2026-07-11T10:00:00Z"


def test_create_evento_requires_timezone_when_occurred_at_is_informed(client):
    response = client.post("/eventos", json=make_payload(occurredAt="2026-07-11T10:00:00"))

    assert response.status_code == 422


def test_get_evento_by_id(client):
    created = create_evento(client)

    response = client.get(f"/eventos/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_evento_by_id_returns_404(client):
    response = client.get(f"/eventos/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Evento não encontrado"}


def test_list_eventos(client):
    first = create_evento(client, entidadeId="demanda-1")
    second = create_evento(client, entidadeId="demanda-2")

    response = client.get("/eventos")

    assert response.status_code == 200
    ids = [evento["id"] for evento in response.json()]
    assert second["id"] in ids
    assert first["id"] in ids


def test_filter_eventos_by_empresa(client):
    empresa_1 = create_evento(client, empresaId="empresa-1")
    create_evento(client, empresaId="empresa-2")

    response = client.get("/eventos", params={"empresaId": "empresa-1"})

    assert response.status_code == 200
    eventos = response.json()
    assert [evento["id"] for evento in eventos] == [empresa_1["id"]]


def test_filter_eventos_by_entidade(client):
    demanda = create_evento(client, entidadeTipo="demanda", entidadeId="demanda-1")
    create_evento(client, entidadeTipo="projeto", entidadeId="projeto-1")

    response = client.get(
        "/eventos",
        params={"entidadeTipo": "demanda", "entidadeId": "demanda-1"},
    )

    assert response.status_code == 200
    eventos = response.json()
    assert [evento["id"] for evento in eventos] == [demanda["id"]]


def test_filter_eventos_by_tipo_and_correlation_id(client):
    correlation_id = str(uuid4())
    matched = create_evento(client, tipo="projeto.atualizado", correlationId=correlation_id)
    create_evento(client, tipo="demanda.criada", correlationId=str(uuid4()))

    response = client.get(
        "/eventos",
        params={"tipo": "projeto.atualizado", "correlationId": correlation_id},
    )

    assert response.status_code == 200
    assert [evento["id"] for evento in response.json()] == [matched["id"]]


def test_list_eventos_orders_by_occurred_at_desc_and_created_at_desc(client):
    older = create_evento(
        client,
        entidadeId="demanda-antiga",
        occurredAt="2026-07-10T10:00:00+00:00",
    )
    newer = create_evento(
        client,
        entidadeId="demanda-nova",
        occurredAt="2026-07-11T10:00:00+00:00",
    )

    response = client.get("/eventos")

    assert response.status_code == 200
    ids = [evento["id"] for evento in response.json()]
    assert ids.index(newer["id"]) < ids.index(older["id"])


def test_filter_eventos_by_date_range(client):
    create_evento(client, entidadeId="fora", occurredAt="2026-07-09T10:00:00+00:00")
    inside = create_evento(client, entidadeId="dentro", occurredAt="2026-07-10T10:00:00+00:00")

    response = client.get(
        "/eventos",
        params={
            "dataInicio": "2026-07-10T00:00:00+00:00",
            "dataFim": "2026-07-10T23:59:59+00:00",
        },
    )

    assert response.status_code == 200
    assert [evento["id"] for evento in response.json()] == [inside["id"]]


def test_list_eventos_limit_and_offset(client):
    for index in range(3):
        create_evento(
            client,
            entidadeId=f"demanda-{index}",
            occurredAt=(datetime(2026, 7, 11, 10, tzinfo=timezone.utc) + timedelta(minutes=index)).isoformat(),
        )

    response = client.get("/eventos", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_eventos_rejects_limit_above_max(client):
    response = client.get("/eventos", params={"limit": 201})

    assert response.status_code == 422


def test_payload_json_is_preserved(client):
    payload = {"nested": {"items": [1, 2, 3]}, "ok": True}
    evento = create_evento(client, payload=payload)

    assert evento["payload"] == payload


def test_update_and_delete_methods_do_not_exist(client):
    evento = create_evento(client)

    assert client.put(f"/eventos/{evento['id']}", json={}).status_code == 405
    assert client.patch(f"/eventos/{evento['id']}", json={}).status_code == 405
    assert client.delete(f"/eventos/{evento['id']}").status_code == 405


def test_create_evento_validates_required_fields(client):
    response = client.post("/eventos", json={"payload": {}})

    assert response.status_code == 422


def test_model_uses_metadata_column_without_reserved_attribute_conflict(client):
    evento = create_evento(client, metadata={"canal": "api"})

    assert evento["metadata"] == {"canal": "api"}
    assert hasattr(Evento, "metadata_")
