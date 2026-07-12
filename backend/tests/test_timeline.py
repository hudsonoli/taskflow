from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.schemas.evento import EventoCreate
from app.services.evento_service import EventoService


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
        test_client.session_factory = TestingSessionLocal
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def create_evento(client, **overrides):
    service = EventoService()
    payload = {
        "empresaId": "empresa-1",
        "agenciaId": "agencia-principal",
        "tipo": "projeto.criado",
        "entidadeTipo": "projeto",
        "entidadeId": "projeto-1",
        "usuarioId": "user-1",
        "payload": {"nome": "Campanha Julho"},
        "metadata": {"source": "test"},
    }
    payload.update(overrides)
    data = EventoCreate(**payload)
    with client.session_factory() as db:
        evento = service.create_evento(db, data)
        return evento.id


def test_timeline_empty(client):
    response = client.get("/timeline")

    assert response.status_code == 200
    assert response.json() == []


def test_timeline_filter_by_entidade(client):
    matched_id = create_evento(client, entidadeTipo="projeto", entidadeId="projeto-1")
    create_evento(client, entidadeTipo="demanda", entidadeId="demanda-1")

    response = client.get(
        "/timeline",
        params={"entidadeTipo": "projeto", "entidadeId": "projeto-1"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [matched_id]


def test_timeline_filter_by_empresa(client):
    matched_id = create_evento(client, empresaId="empresa-1")
    create_evento(client, empresaId="empresa-2")

    response = client.get("/timeline", params={"empresaId": "empresa-1"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [matched_id]


def test_timeline_filter_by_tipo(client):
    matched_id = create_evento(
        client,
        tipo="demanda.prioridade_alterada",
        entidadeTipo="demanda",
        entidadeId="demanda-1",
    )
    create_evento(client, tipo="projeto.criado")

    response = client.get("/timeline", params={"tipo": "demanda.prioridade_alterada"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [matched_id]


def test_timeline_filter_by_usuario_id(client):
    matched_id = create_evento(client, usuarioId="user-1")
    create_evento(client, usuarioId="user-2")

    response = client.get("/timeline", params={"usuarioId": "user-1"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [matched_id]


def test_timeline_orders_by_occurred_at_desc_and_created_at_desc(client):
    older = create_evento(
        client,
        entidadeId="projeto-antigo",
        occurredAt="2026-07-10T10:00:00+00:00",
    )
    newer = create_evento(
        client,
        entidadeId="projeto-novo",
        occurredAt="2026-07-11T10:00:00+00:00",
    )

    response = client.get("/timeline")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids.index(newer) < ids.index(older)


def test_timeline_pagination(client):
    base = datetime(2026, 7, 11, 10, tzinfo=timezone.utc)
    for index in range(3):
        create_evento(
            client,
            entidadeId=f"projeto-{index}",
            occurredAt=(base + timedelta(minutes=index)).isoformat(),
        )

    response = client.get("/timeline", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_timeline_data_inicio_filter(client):
    create_evento(client, entidadeId="fora", occurredAt="2026-07-09T10:00:00+00:00")
    inside = create_evento(client, entidadeId="dentro", occurredAt="2026-07-10T10:00:00+00:00")

    response = client.get("/timeline", params={"dataInicio": "2026-07-10T00:00:00+00:00"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [inside]


def test_timeline_data_fim_filter(client):
    inside = create_evento(client, entidadeId="dentro", occurredAt="2026-07-10T10:00:00+00:00")
    create_evento(client, entidadeId="fora", occurredAt="2026-07-11T10:00:00+00:00")

    response = client.get("/timeline", params={"dataFim": "2026-07-10T23:59:59+00:00"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [inside]


def test_timeline_rejects_naive_data_inicio(client):
    response = client.get("/timeline", params={"dataInicio": "2026-07-10T00:00:00"})

    assert response.status_code == 422


def test_timeline_rejects_invalid_date(client):
    response = client.get("/timeline", params={"dataInicio": "data-invalida"})

    assert response.status_code == 422


def test_timeline_rejects_limit_above_max(client):
    response = client.get("/timeline", params={"limit": 201})

    assert response.status_code == 422


def test_timeline_rejects_negative_offset(client):
    response = client.get("/timeline", params={"offset": -1})

    assert response.status_code == 422


def test_timeline_known_mapper_projeto_criado(client):
    create_evento(client, tipo="projeto.criado")

    response = client.get("/timeline")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["titulo"] == "Projeto criado"
    assert item["descricao"] == "Projeto criado."


def test_timeline_known_mapper_projeto_status_alterado(client):
    create_evento(
        client,
        tipo="projeto.status_alterado",
        payload={"statusAnterior": "planejamento", "statusNovo": "ativo"},
    )

    response = client.get("/timeline")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["titulo"] == "Projeto alterado"
    assert item["descricao"] == "Status alterado de Planejamento para Ativo."


def test_timeline_known_mapper_demanda_prioridade_alterada(client):
    create_evento(
        client,
        tipo="demanda.prioridade_alterada",
        entidadeTipo="demanda",
        entidadeId="demanda-1",
        payload={"prioridadeAnterior": "media", "prioridadeNova": "alta"},
    )

    response = client.get("/timeline")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["titulo"] == "Prioridade alterada"
    assert item["descricao"] == "Prioridade alterada de Média para Alta."


def test_timeline_known_mapper_workflow_etapa_avancada(client):
    create_evento(
        client,
        tipo="workflow.etapa_avancada",
        entidadeTipo="workflow",
        entidadeId="workflow-1",
        payload={"etapaOrigemNome": "Redação", "etapaDestinoNome": "Aprovação"},
    )

    response = client.get("/timeline")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["titulo"] == "Workflow"
    assert item["descricao"] == "Movido de Redação para Aprovação."


def test_timeline_unknown_type_uses_fallback(client):
    create_evento(client, tipo="evento.desconhecido")

    response = client.get("/timeline")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["titulo"] == "Evento"
    assert item["descricao"] == "Evento registrado."


def test_timeline_preserves_payload_and_metadata(client):
    payload = {"nested": {"items": [1, 2, 3]}, "statusAnterior": "planejamento"}
    metadata = {"source": "test", "tags": ["timeline", "auditoria"]}
    create_evento(client, payload=payload, metadata=metadata)

    response = client.get("/timeline")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["payload"] == payload
    assert item["metadata"] == metadata


def test_timeline_returns_timezone_aware_timestamps(client):
    create_evento(client, occurredAt="2026-07-11T10:00:00+00:00")

    response = client.get("/timeline")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["occurredAt"].endswith("Z")
    assert item["createdAt"].endswith("Z")
