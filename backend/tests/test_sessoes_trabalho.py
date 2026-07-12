from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.sessao_trabalho import SessaoTrabalho
from app.services.sessao_trabalho_service import (
    MOTIVO_PAUSA,
    MOTIVO_SUBSTITUICAO_SESSAO_ATIVA,
    STATUS_ATIVA,
    STATUS_CANCELADA,
    STATUS_ENCERRADA,
    SessaoTrabalhoService,
)


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


def now() -> datetime:
    return datetime(2026, 7, 12, 12, tzinfo=timezone.utc)


def open_session(db, **overrides):
    payload = {
        "empresa_id": "empresa-1",
        "agencia_id": "agencia-principal",
        "demanda_id": "demanda-1",
        "workflow_etapa_id": "etapa-1",
        "usuario_id": "user-1",
        "departamento_id": None,
        "evento_inicio_id": str(uuid4()),
        "inicio_em": now(),
    }
    payload.update(overrides)
    return SessaoTrabalhoService().open_session(db, **payload)


def list_sessions(db):
    return list(db.scalars(select(SessaoTrabalho).order_by(SessaoTrabalho.inicio_em)).all())


def test_open_session(session_factory):
    with session_factory() as db:
        with db.begin():
            sessao = open_session(db)
            sessao_id = sessao.id

    with session_factory() as db:
        persisted = db.get(SessaoTrabalho, sessao_id)
        assert persisted.status == STATUS_ATIVA
        assert persisted.usuario_id == "user-1"
        assert persisted.fim_em is None


def test_open_session_requires_usuario_or_departamento(session_factory):
    with session_factory() as db:
        with pytest.raises(ValueError, match="usuarioId ou departamentoId"):
            with db.begin():
                open_session(db, usuario_id=None, departamento_id=None)


def test_open_session_rejects_usuario_and_departamento_without_payload_justification(session_factory):
    with session_factory() as db:
        with pytest.raises(ValueError, match="justificativa"):
            with db.begin():
                open_session(db, usuario_id="user-1", departamento_id="departamento-1")


def test_open_session_allows_usuario_and_departamento_with_justification(session_factory):
    with session_factory() as db:
        with db.begin():
            sessao = open_session(
                db,
                usuario_id="user-1",
                departamento_id="departamento-1",
                allow_usuario_and_departamento=True,
            )
        assert sessao.usuario_id == "user-1"
        assert sessao.departamento_id == "departamento-1"


def test_repeated_start_event_is_idempotent(session_factory):
    event_id = str(uuid4())
    with session_factory() as db:
        with db.begin():
            first = open_session(db, evento_inicio_id=event_id)
            second = open_session(db, evento_inicio_id=event_id)
            assert first.id == second.id

    with session_factory() as db:
        assert len(list_sessions(db)) == 1


def test_repeated_finish_event_is_idempotent(session_factory):
    finish_event_id = str(uuid4())
    with session_factory() as db:
        with db.begin():
            sessao = open_session(db)
            first = SessaoTrabalhoService().close_session(
                db,
                sessao,
                evento_fim_id=finish_event_id,
                fim_em=now() + timedelta(hours=1),
                motivo_encerramento=MOTIVO_PAUSA,
            )
            second = SessaoTrabalhoService().close_session(
                db,
                sessao,
                evento_fim_id=finish_event_id,
                fim_em=now() + timedelta(hours=2),
                motivo_encerramento=MOTIVO_PAUSA,
            )
            assert first.id == second.id
            assert second.duracao_segundos == 3600


def test_close_session_by_pause(session_factory):
    with session_factory() as db:
        with db.begin():
            sessao = open_session(db)
            closed = SessaoTrabalhoService().close_session(
                db,
                sessao,
                evento_fim_id=str(uuid4()),
                fim_em=now() + timedelta(minutes=30),
                motivo_encerramento=MOTIVO_PAUSA,
            )
            assert closed.status == STATUS_ENCERRADA
            assert closed.duracao_segundos == 1800
            assert closed.evento_fim_id
            assert closed.motivo_encerramento == MOTIVO_PAUSA


def test_close_session_with_end_before_start_has_zero_duration(session_factory):
    with session_factory() as db:
        with db.begin():
            sessao = open_session(db, inicio_em=now())
            closed = SessaoTrabalhoService().close_session(
                db,
                sessao,
                evento_fim_id=str(uuid4()),
                fim_em=now() - timedelta(hours=1),
                motivo_encerramento=MOTIVO_PAUSA,
            )
            assert closed.duracao_segundos == 0


def test_open_replaces_active_equivalent_session(session_factory):
    with session_factory() as db:
        with db.begin():
            first = open_session(db, evento_inicio_id=str(uuid4()), inicio_em=now())
            second = open_session(db, evento_inicio_id=str(uuid4()), inicio_em=now() + timedelta(minutes=10))
            assert first.id != second.id
            assert first.status == STATUS_ENCERRADA
            assert first.motivo_encerramento == MOTIVO_SUBSTITUICAO_SESSAO_ATIVA
            assert second.status == STATUS_ATIVA


def test_different_demandas_can_have_active_sessions_for_same_user(session_factory):
    with session_factory() as db:
        with db.begin():
            open_session(db, demanda_id="demanda-1", usuario_id="user-1")
            open_session(db, demanda_id="demanda-2", usuario_id="user-1")
    with session_factory() as db:
        active = [sessao for sessao in list_sessions(db) if sessao.status == STATUS_ATIVA]
        assert len(active) == 2


def test_same_demanda_can_have_active_sessions_for_different_users(session_factory):
    with session_factory() as db:
        with db.begin():
            open_session(db, demanda_id="demanda-1", usuario_id="user-1")
            open_session(db, demanda_id="demanda-1", usuario_id="user-2")
    with session_factory() as db:
        active = [sessao for sessao in list_sessions(db) if sessao.status == STATUS_ATIVA]
        assert len(active) == 2


def test_closed_session_does_not_return_to_active(session_factory):
    with session_factory() as db:
        with db.begin():
            sessao = open_session(db)
            service = SessaoTrabalhoService()
            service.close_session(
                db,
                sessao,
                evento_fim_id=str(uuid4()),
                fim_em=now() + timedelta(minutes=1),
                motivo_encerramento=MOTIVO_PAUSA,
            )
            service.close_session(
                db,
                sessao,
                evento_fim_id=str(uuid4()),
                fim_em=now() + timedelta(minutes=2),
                motivo_encerramento=MOTIVO_PAUSA,
            )
            assert sessao.status == STATUS_ENCERRADA


def test_invalid_status_is_rejected(session_factory):
    with session_factory() as db:
        with pytest.raises(ValueError, match="Status de sessão inválido"):
            SessaoTrabalhoService().list_sessions(db, status="invalido")


def test_database_rejects_invalid_status_constraint(session_factory):
    with session_factory() as db:
        invalid = SessaoTrabalho(
            id=str(uuid4()),
            empresa_id="empresa-1",
            agencia_id=None,
            demanda_id="demanda-1",
            workflow_etapa_id=None,
            usuario_id="user-1",
            departamento_id=None,
            evento_inicio_id=str(uuid4()),
            evento_fim_id=None,
            status="invalido",
            inicio_em=now(),
            fim_em=None,
            duracao_segundos=None,
            motivo_encerramento=None,
            created_at=now(),
            updated_at=now(),
        )
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()


def test_rollback_does_not_persist_session(session_factory):
    with pytest.raises(RuntimeError):
        with session_factory() as db:
            with db.begin():
                open_session(db)
                raise RuntimeError("rollback")

    with session_factory() as db:
        assert list_sessions(db) == []


def test_list_and_filter_sessions(client):
    with client.session_factory() as db:
        with db.begin():
            target = open_session(db, empresa_id="empresa-1", demanda_id="demanda-1", usuario_id="user-1")
            target_id = target.id
            open_session(db, empresa_id="empresa-2", demanda_id="demanda-2", usuario_id="user-2")

    response = client.get(
        "/sessoes-trabalho",
        params={"empresaId": "empresa-1", "demandaId": "demanda-1", "usuarioId": "user-1"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [target_id]


def test_get_session_by_id(client):
    with client.session_factory() as db:
        with db.begin():
            sessao = open_session(db)
            sessao_id = sessao.id

    response = client.get(f"/sessoes-trabalho/{sessao_id}")

    assert response.status_code == 200
    assert response.json()["id"] == sessao_id


def test_get_session_by_id_404(client):
    response = client.get(f"/sessoes-trabalho/{uuid4()}")

    assert response.status_code == 404


def test_session_routes_are_read_only(client):
    assert client.post("/sessoes-trabalho", json={}).status_code == 405
    assert client.put(f"/sessoes-trabalho/{uuid4()}", json={}).status_code == 405
    assert client.patch(f"/sessoes-trabalho/{uuid4()}", json={}).status_code == 405
    assert client.delete(f"/sessoes-trabalho/{uuid4()}").status_code == 405


def test_cancelada_is_reserved_for_future_admin_invalidation(session_factory):
    assert STATUS_CANCELADA == "cancelada"
