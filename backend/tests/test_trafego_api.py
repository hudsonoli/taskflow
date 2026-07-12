from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.sessao_trabalho import SessaoTrabalho


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


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 7, 12, hour, minute, tzinfo=timezone.utc)


def add_session(
    client,
    *,
    empresa_id="empresa-principal",
    demanda_id="demanda-1",
    usuario_id="user-1",
    departamento_id=None,
    workflow_etapa_id="etapa-1",
    status="ativa",
    inicio_em=None,
    fim_em=None,
):
    inicio = inicio_em or dt(10)
    with client.session_factory() as db:
        with db.begin():
            sessao = SessaoTrabalho(
                id=str(uuid4()),
                empresa_id=empresa_id,
                agencia_id="agencia-1",
                demanda_id=demanda_id,
                workflow_etapa_id=workflow_etapa_id,
                usuario_id=usuario_id,
                departamento_id=departamento_id,
                evento_inicio_id=str(uuid4()),
                evento_fim_id=str(uuid4()) if fim_em else None,
                status=status,
                inicio_em=inicio,
                fim_em=fim_em,
                duracao_segundos=int((fim_em - inicio).total_seconds()) if fim_em else None,
                motivo_encerramento="pausa" if fim_em else None,
                created_at=inicio,
                updated_at=fim_em or inicio,
            )
            db.add(sessao)
            db.flush()
            return sessao.id


def test_trafego_agora_empty(client):
    response = client.get("/trafego/agora")

    assert response.status_code == 200
    assert response.json() == []


def test_trafego_agora_active_filters_order_and_pagination(client, monkeypatch):
    from app.services import trafego_query_service

    monkeypatch.setattr(trafego_query_service, "utc_now", lambda: dt(12))
    older_id = add_session(client, demanda_id="demanda-1", usuario_id="user-1", inicio_em=dt(9))
    add_session(client, demanda_id="demanda-2", usuario_id="user-1", inicio_em=dt(10))
    add_session(client, demanda_id="demanda-3", usuario_id="user-2", inicio_em=dt(8))

    response = client.get("/trafego/agora", params={"usuarioId": "user-1", "limit": 1})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sessaoId"] == older_id
    assert data[0]["tempoDecorridoSegundos"] == 10800
    assert data[0]["inicioEm"].endswith("Z")


def test_trafego_agora_rejects_invalid_pagination(client):
    assert client.get("/trafego/agora", params={"limit": 201}).status_code == 422
    assert client.get("/trafego/agora", params={"offset": -1}).status_code == 422


def test_trafego_carga_requires_empresa_and_valid_group(client):
    assert client.get("/trafego/carga").status_code == 422
    assert client.get("/trafego/carga", params={"empresaId": "empresa-principal", "agrupamento": "setor"}).status_code == 422


def test_trafego_carga_by_user(client, monkeypatch):
    from app.services import trafego_query_service

    monkeypatch.setattr(trafego_query_service, "utc_now", lambda: dt(12))
    add_session(client, demanda_id="demanda-1", usuario_id="user-1", inicio_em=dt(9))
    add_session(client, demanda_id="demanda-2", usuario_id="user-1", inicio_em=dt(10))
    add_session(client, demanda_id="demanda-2", usuario_id=None, departamento_id="dep-1", inicio_em=dt(9))

    response = client.get("/trafego/carga", params={"empresaId": "empresa-principal", "agrupamento": "usuario"})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["agrupamentoId"] == "user-1"
    assert data[0]["tipoAgrupamento"] == "usuario"
    assert data[0]["sessoesAtivas"] == 2
    assert data[0]["demandasDistintas"] == 2
    assert data[0]["tempoAtivoTotalSegundos"] == 18000


def test_trafego_carga_by_department_ignores_null_group(client, monkeypatch):
    from app.services import trafego_query_service

    monkeypatch.setattr(trafego_query_service, "utc_now", lambda: dt(12))
    add_session(client, demanda_id="demanda-1", departamento_id="dep-1", inicio_em=dt(9))
    add_session(client, demanda_id="demanda-2", departamento_id=None, inicio_em=dt(9))

    response = client.get("/trafego/carga", params={"empresaId": "empresa-principal", "agrupamento": "departamento"})

    assert response.status_code == 200
    assert [item["agrupamentoId"] for item in response.json()] == ["dep-1"]


def test_trafego_resumo_requires_empresa(client):
    assert client.get("/trafego/resumo").status_code == 422


def test_trafego_resumo_period_and_metrics(client, monkeypatch):
    from app.services import trafego_query_service

    monkeypatch.setattr(trafego_query_service, "utc_now", lambda: dt(12))
    add_session(client, demanda_id="demanda-1", usuario_id="user-1", departamento_id="dep-1", status="encerrada", inicio_em=dt(9), fim_em=dt(10))
    add_session(client, demanda_id="demanda-2", usuario_id="user-2", departamento_id="dep-1", status="ativa", inicio_em=dt(11))

    response = client.get(
        "/trafego/resumo",
        params={
            "empresaId": "empresa-principal",
            "dataInicio": "2026-07-12T08:00:00+00:00",
            "dataFim": "2026-07-12T12:00:00+00:00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["sessoesAtivas"] == 1
    assert data["sessoesEncerradas"] == 1
    assert data["demandasDistintas"] == 2
    assert data["usuariosDistintos"] == 2
    assert data["departamentosDistintos"] == 1
    assert data["tempoOperacionalEstimadoSegundos"] == 7200
    assert data["tempoMedioSessaoSegundos"] == 3600
    assert data["maiorSessaoSegundos"] == 3600


def test_trafego_resumo_only_data_inicio_and_only_data_fim(client, monkeypatch):
    from app.services import trafego_query_service

    monkeypatch.setattr(trafego_query_service, "utc_now", lambda: dt(12))
    response = client.get("/trafego/resumo", params={"empresaId": "empresa-principal", "dataInicio": "2026-07-12T10:00:00+00:00"})
    assert response.status_code == 200
    assert response.json()["inicioPeriodo"] == "2026-07-12T10:00:00Z"
    assert response.json()["fimPeriodo"] == "2026-07-12T12:00:00Z"

    response = client.get("/trafego/resumo", params={"empresaId": "empresa-principal", "dataFim": "2026-07-12T12:00:00+00:00"})
    assert response.status_code == 200
    assert response.json()["inicioPeriodo"] == "2026-07-11T12:00:00Z"
    assert response.json()["fimPeriodo"] == "2026-07-12T12:00:00Z"


def test_trafego_resumo_rejects_invalid_dates(client):
    response = client.get(
        "/trafego/resumo",
        params={
            "empresaId": "empresa-principal",
            "dataInicio": "2026-07-12T12:00:00+00:00",
            "dataFim": "2026-07-12T10:00:00+00:00",
        },
    )
    assert response.status_code == 422

    response = client.get(
        "/trafego/resumo",
        params={"empresaId": "empresa-principal", "dataInicio": "2026-07-12T12:00:00"},
    )
    assert response.status_code == 422


def test_trafego_resumo_filters(client, monkeypatch):
    from app.services import trafego_query_service

    monkeypatch.setattr(trafego_query_service, "utc_now", lambda: dt(12))
    add_session(client, demanda_id="demanda-1", usuario_id="user-1", departamento_id="dep-1", status="encerrada", inicio_em=dt(9), fim_em=dt(10))
    add_session(client, demanda_id="demanda-2", usuario_id="user-2", departamento_id="dep-2", status="encerrada", inicio_em=dt(9), fim_em=dt(10))

    response = client.get("/trafego/resumo", params={"empresaId": "empresa-principal", "usuarioId": "user-1"})
    assert response.status_code == 200
    assert response.json()["demandasDistintas"] == 1

    response = client.get("/trafego/resumo", params={"empresaId": "empresa-principal", "departamentoId": "dep-2"})
    assert response.status_code == 200
    assert response.json()["demandasDistintas"] == 1

    response = client.get("/trafego/resumo", params={"empresaId": "empresa-principal", "demandaId": "demanda-2"})
    assert response.status_code == 200
    assert response.json()["demandasDistintas"] == 1


def test_trafego_routes_are_read_only(client):
    for path in ["/trafego/agora", "/trafego/carga", "/trafego/resumo"]:
        assert client.post(path, json={}).status_code == 405
        assert client.put(path, json={}).status_code == 405
        assert client.patch(path, json={}).status_code == 405
        assert client.delete(path).status_code == 405
