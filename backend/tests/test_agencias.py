from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.domain.event_types import DomainEventType
from app.main import app
from app.models.agencia import Agencia
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.schemas.agencia import AgenciaCreate
from app.services.agencia_service import AgenciaService


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


def empresa_payload(**overrides):
    data = {
        "nome": "Empresa Agencia",
        "documento": uuid4().hex,
        "codigoInterno": f"EMP-{uuid4().hex[:8]}",
    }
    data.update(overrides)
    return data


def create_empresa(client, **overrides):
    response = client.post("/empresas", json=empresa_payload(**overrides))
    assert response.status_code == 201
    return response.json()


def agencia_payload(empresa_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "codigoInterno": f"ag-{uuid4().hex[:8]}",
        "nome": f"  Agencia {uuid4().hex[:8]}  ",
        "sigla": " ag ",
        "descricao": "  Unidade operacional  ",
    }
    data.update(overrides)
    return data


def create_agencia(client, empresa_id: str, **overrides):
    response = client.post("/agencias", json=agencia_payload(empresa_id, **overrides))
    assert response.status_code == 201
    return response.json()


def eventos(session_factory) -> list[Evento]:
    with session_factory() as db:
        return list(db.scalars(select(Evento).order_by(Evento.created_at)).all())


def agencias(session_factory) -> list[Agencia]:
    with session_factory() as db:
        return list(db.scalars(select(Agencia)).all())


def persist_empresa(session_factory, *, status: str = "ativa") -> Empresa:
    now = datetime.now(timezone.utc)
    empresa = Empresa(
        id=str(uuid4()),
        nome="Empresa Persistida",
        documento=uuid4().hex,
        codigo_interno=f"EMP-{uuid4().hex[:8]}",
        status=status,
        created_at=now,
        updated_at=now,
        inativado_at=None,
        inativado_por_usuario_id=None,
        motivo_inativacao=None,
    )
    with session_factory() as db:
        db.add(empresa)
        db.commit()
        db.refresh(empresa)
        return empresa


def test_create_agencia_normalizes_fields(client):
    empresa = create_empresa(client)

    agencia = create_agencia(
        client,
        empresa["id"],
        codigoInterno=" ag-001 ",
        nome="  Agencia   Centro  ",
        sigla=" ctr ",
        descricao="  Unidade   central  ",
    )

    assert agencia["id"]
    assert agencia["empresaId"] == empresa["id"]
    assert agencia["codigoInterno"] == "AG-001"
    assert agencia["nome"] == "Agencia Centro"
    assert agencia["sigla"] == "CTR"
    assert agencia["descricao"] == "Unidade central"
    assert agencia["status"] == "ativa"


def test_create_agencia_requires_existing_empresa(client):
    response = client.post("/agencias", json=agencia_payload(str(uuid4())))

    assert response.status_code == 422
    assert response.json() == {"detail": "Empresa não encontrada"}


def test_create_agencia_rejects_inactive_empresa(client):
    empresa = create_empresa(client)
    client.post(f"/empresas/{empresa['id']}/inativar", json={"motivoInativacao": "teste"})

    response = client.post("/agencias", json=agencia_payload(empresa["id"]))

    assert response.status_code == 422
    assert response.json() == {"detail": "Empresa inativa não permite criação de Agência"}


def test_list_agencias_requires_empresa_id(client):
    response = client.get("/agencias")

    assert response.status_code == 422


def test_list_agencias_by_empresa(client):
    empresa_a = create_empresa(client, codigoInterno="EMP-A")
    empresa_b = create_empresa(client, codigoInterno="EMP-B")
    first = create_agencia(client, empresa_a["id"], codigoInterno="AG-A", nome="Agencia A")
    create_agencia(client, empresa_b["id"], codigoInterno="AG-B", nome="Agencia B")

    response = client.get("/agencias", params={"empresaId": empresa_a["id"]})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [first["id"]]


def test_list_agencias_filters_by_status(client):
    empresa = create_empresa(client)
    active = create_agencia(client, empresa["id"], codigoInterno="AG-A", nome="Agencia Ativa")
    inactive = create_agencia(client, empresa["id"], codigoInterno="AG-I", nome="Agencia Inativa")
    client.post(f"/agencias/{inactive['id']}/inativar", json={"motivoInativacao": "teste"})

    response = client.get("/agencias", params={"empresaId": empresa["id"], "status": "ativa"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [active["id"]]


def test_get_agencia_by_id(client):
    empresa = create_empresa(client)
    created = create_agencia(client, empresa["id"])

    response = client.get(f"/agencias/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_agencia_by_id_returns_404(client):
    response = client.get(f"/agencias/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Agência não encontrada"}


def test_update_agencia(client):
    empresa = create_empresa(client)
    created = create_agencia(client, empresa["id"])

    response = client.patch(
        f"/agencias/{created['id']}",
        json={"codigoInterno": " ag-009 ", "nome": " Agencia Sul ", "sigla": " sul ", "descricao": " nova unidade "},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["codigoInterno"] == "AG-009"
    assert updated["nome"] == "Agencia Sul"
    assert updated["sigla"] == "SUL"
    assert updated["descricao"] == "nova unidade"
    assert updated["empresaId"] == created["empresaId"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("empresaId", str(uuid4())),
        ("status", "inativa"),
        ("createdAt", "2026-07-15T00:00:00Z"),
        ("updatedAt", "2026-07-15T00:00:00Z"),
        ("inativadoAt", "2026-07-15T00:00:00Z"),
        ("motivoInativacao", "teste"),
        ("inativadoPorUsuarioId", str(uuid4())),
    ],
)
def test_patch_rejects_forbidden_fields(client, field, value):
    empresa = create_empresa(client)
    created = create_agencia(client, empresa["id"])

    response = client.patch(f"/agencias/{created['id']}", json={field: value})

    assert response.status_code == 422
    assert field in response.json()["detail"]


def test_codigo_interno_duplicate_in_same_empresa_is_rejected_after_normalization(client):
    empresa = create_empresa(client)
    create_agencia(client, empresa["id"], codigoInterno="AG-DUP")

    response = client.post("/agencias", json=agencia_payload(empresa["id"], codigoInterno=" ag-dup "))

    assert response.status_code == 409
    assert response.json() == {"detail": "codigoInterno já cadastrado para esta Empresa"}


def test_nome_duplicate_in_same_empresa_is_rejected_after_normalization(client):
    empresa = create_empresa(client)
    create_agencia(client, empresa["id"], nome="Agencia Norte")

    response = client.post("/agencias", json=agencia_payload(empresa["id"], nome="  Agencia   Norte  "))

    assert response.status_code == 409
    assert response.json() == {"detail": "nome já cadastrado para esta Empresa"}


def test_duplicates_are_allowed_in_different_empresas(client):
    empresa_a = create_empresa(client, codigoInterno="EMP-A")
    empresa_b = create_empresa(client, codigoInterno="EMP-B")

    first = create_agencia(client, empresa_a["id"], codigoInterno="AG-001", nome="Agencia Central")
    second = create_agencia(client, empresa_b["id"], codigoInterno=" ag-001 ", nome="Agencia Central")

    assert first["codigoInterno"] == second["codigoInterno"]
    assert first["nome"] == second["nome"]
    assert first["empresaId"] != second["empresaId"]


def test_inativar_agencia(client):
    empresa = create_empresa(client)
    created = create_agencia(client, empresa["id"])

    response = client.post(
        f"/agencias/{created['id']}/inativar",
        json={"motivoInativacao": "encerramento", "actorUsuarioId": None},
    )

    assert response.status_code == 200
    agencia = response.json()
    assert agencia["status"] == "inativa"
    assert agencia["inativadoAt"]
    assert agencia["motivoInativacao"] == "encerramento"
    assert agencia["inativadoPorUsuarioId"] is None


def test_reativar_agencia(client):
    empresa = create_empresa(client)
    created = create_agencia(client, empresa["id"])
    client.post(f"/agencias/{created['id']}/inativar", json={"motivoInativacao": "teste"})

    response = client.post(f"/agencias/{created['id']}/reativar")

    assert response.status_code == 200
    agencia = response.json()
    assert agencia["status"] == "ativa"
    assert agencia["inativadoAt"] is None
    assert agencia["motivoInativacao"] is None
    assert agencia["inativadoPorUsuarioId"] is None


def test_invalid_transitions_are_rejected(client):
    empresa = create_empresa(client)
    active = create_agencia(client, empresa["id"], codigoInterno="AG-A", nome="Agencia Ativa")
    inactive = create_agencia(client, empresa["id"], codigoInterno="AG-I", nome="Agencia Inativa")
    client.post(f"/agencias/{inactive['id']}/inativar", json={"motivoInativacao": "teste"})

    reactivate_active = client.post(f"/agencias/{active['id']}/reativar")
    inactivate_inactive = client.post(f"/agencias/{inactive['id']}/inativar", json={"motivoInativacao": "teste"})

    assert reactivate_active.status_code == 409
    assert reactivate_active.json() == {"detail": "Agência já está ativa"}
    assert inactivate_inactive.status_code == 409
    assert inactivate_inactive.json() == {"detail": "Agência já está inativa"}


def test_delete_route_does_not_exist(client):
    empresa = create_empresa(client)
    created = create_agencia(client, empresa["id"])

    response = client.delete(f"/agencias/{created['id']}")

    assert response.status_code == 405


def test_emits_agencia_events_with_restricted_payload(client):
    empresa = create_empresa(client)
    created = create_agencia(client, empresa["id"], codigoInterno="AG-EVENTOS", nome="Agencia Eventos")
    client.patch(f"/agencias/{created['id']}", json={"nome": "Agencia Alterada"})
    client.post(f"/agencias/{created['id']}/inativar", json={"motivoInativacao": "teste"})
    client.post(f"/agencias/{created['id']}/reativar")

    persisted_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "agencia"]
    event_types = [evento.tipo for evento in persisted_events]

    assert event_types == [
        DomainEventType.AGENCIA_CRIADA.value,
        DomainEventType.AGENCIA_ALTERADA.value,
        DomainEventType.AGENCIA_INATIVADA.value,
        DomainEventType.AGENCIA_REATIVADA.value,
    ]
    for evento in persisted_events:
        assert evento.empresa_id == empresa["id"]
        assert evento.entidade_id == created["id"]
        assert set(evento.payload) == {"empresa_id", "agencia_id", "timestamp", "actor_usuario_id"}
        assert evento.payload["empresa_id"] == empresa["id"]
        assert evento.payload["agencia_id"] == created["id"]
        assert evento.payload["timestamp"]
        assert "nome" not in evento.payload
        assert "sigla" not in evento.payload
        assert "descricao" not in evento.payload


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_create_rolls_back_when_event_publish_fails(session_factory):
    empresa = persist_empresa(session_factory)
    service = AgenciaService(event_publisher=FailingPublisher())
    data = AgenciaCreate(
        empresaId=empresa.id,
        codigoInterno="AG-ROLLBACK",
        nome="Agencia Rollback",
        sigla="RB",
        descricao="teste rollback",
    )

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.create_agencia(db, data)

    assert agencias(session_factory) == []
    assert eventos(session_factory) == []
