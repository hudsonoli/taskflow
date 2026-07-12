from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.event_types import DomainEventType
from app.models.evento import Evento
from app.models.sessao_trabalho import SessaoTrabalho
from app.services.sessao_trabalho_service import (
    MOTIVO_AGUARDANDO_CLIENTE,
    MOTIVO_BLOQUEIO,
    MOTIVO_CONCLUSAO,
    MOTIVO_MUDANCA_ETAPA,
    MOTIVO_PAUSA,
    STATUS_ATIVA,
    STATUS_ENCERRADA,
    SessaoTrabalhoService,
)
from app.services.trafego_event_handler import TrafegoEventHandler


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


def event(
    *,
    tipo=DomainEventType.DEMANDA_STATUS_ALTERADO.value,
    entidade_tipo="demanda",
    entidade_id="demanda-1",
    usuario_id="user-1",
    payload=None,
    occurred_at=None,
):
    return Evento(
        id=str(uuid4()),
        empresa_id="empresa-1",
        agencia_id="agencia-principal",
        tipo=tipo,
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        usuario_id=usuario_id,
        correlation_id=None,
        causation_id=None,
        payload=payload or {},
        metadata_=None,
        occurred_at=occurred_at or datetime(2026, 7, 12, 12, tzinfo=timezone.utc),
        created_at=datetime(2026, 7, 12, 12, tzinfo=timezone.utc),
    )


def sessions(db):
    return list(db.scalars(select(SessaoTrabalho).order_by(SessaoTrabalho.inicio_em)).all())


def persist_event(db, evento):
    db.add(evento)
    db.flush()
    return evento


def test_status_em_execucao_opens_session_from_entity_id(session_factory):
    evento = event(payload={"statusNovo": "em_execucao", "usuarioId": "user-1"})
    with session_factory() as db:
        with db.begin():
            persist_event(db, evento)
            sessao = TrafegoEventHandler().handle(db, evento)
            assert sessao.status == STATUS_ATIVA
            assert sessao.demanda_id == "demanda-1"
            assert sessao.inicio_em == evento.occurred_at


def test_status_em_execucao_does_not_open_without_responsavel(session_factory):
    evento = event(usuario_id=None, payload={"statusNovo": "em_execucao"})
    with session_factory() as db:
        with db.begin():
            persist_event(db, evento)
            assert TrafegoEventHandler().handle(db, evento) is None
        assert sessions(db) == []


def test_status_event_with_non_demanda_entity_is_ignored(session_factory):
    evento = event(entidade_tipo="projeto", entidade_id="projeto-1", payload={"statusNovo": "em_execucao", "usuarioId": "user-1"})
    with session_factory() as db:
        with db.begin():
            persist_event(db, evento)
            assert TrafegoEventHandler().handle(db, evento) is None
        assert sessions(db) == []


def test_divergent_entity_id_and_payload_demanda_id_is_ignored(session_factory):
    evento = event(payload={"statusNovo": "em_execucao", "demandaId": "demanda-2", "usuarioId": "user-1"})
    with session_factory() as db:
        with db.begin():
            persist_event(db, evento)
            assert TrafegoEventHandler().handle(db, evento) is None
        assert sessions(db) == []


@pytest.mark.parametrize(
    ("status_novo", "motivo"),
    [
        ("pausada", MOTIVO_PAUSA),
        ("bloqueada", MOTIVO_BLOQUEIO),
        ("aguardando_cliente", MOTIVO_AGUARDANDO_CLIENTE),
        ("concluida", MOTIVO_CONCLUSAO),
    ],
)
def test_status_change_closes_session(session_factory, status_novo, motivo):
    start = event(payload={"statusNovo": "em_execucao", "usuarioId": "user-1"})
    finish = event(payload={"statusNovo": status_novo, "usuarioId": "user-1"}, occurred_at=start.occurred_at + timedelta(hours=1))
    with session_factory() as db:
        with db.begin():
            persist_event(db, start)
            TrafegoEventHandler().handle(db, start)
            persist_event(db, finish)
            closed = TrafegoEventHandler().handle(db, finish)
            assert closed.status == STATUS_ENCERRADA
            assert closed.motivo_encerramento == motivo
            assert closed.evento_fim_id == finish.id
            assert closed.duracao_segundos == 3600


def test_irrelevant_event_is_ignored(session_factory):
    evento = event(tipo=DomainEventType.PROJETO_CRIADO.value, entidade_tipo="projeto", entidade_id="projeto-1")
    with session_factory() as db:
        with db.begin():
            persist_event(db, evento)
            assert TrafegoEventHandler().handle(db, evento) is None
        assert sessions(db) == []


def test_closing_missing_session_does_not_corrupt_data(session_factory):
    evento = event(payload={"statusNovo": "pausada", "usuarioId": "user-1"})
    with session_factory() as db:
        with db.begin():
            persist_event(db, evento)
            assert TrafegoEventHandler().handle(db, evento) is None
        assert sessions(db) == []


def test_workflow_advance_closes_previous_step_and_opens_new_when_explicit(session_factory):
    start = event(payload={"statusNovo": "em_execucao", "usuarioId": "user-1", "workflowEtapaId": "etapa-1"})
    workflow = event(
        tipo=DomainEventType.WORKFLOW_ETAPA_AVANCADA.value,
        entidade_tipo="workflow",
        entidade_id="workflow-1",
        payload={
            "demandaId": "demanda-1",
            "etapaOrigemId": "etapa-1",
            "etapaDestinoId": "etapa-2",
            "usuarioId": "user-1",
            "iniciarExecucao": True,
        },
        occurred_at=start.occurred_at + timedelta(minutes=15),
    )
    with session_factory() as db:
        with db.begin():
            persist_event(db, start)
            TrafegoEventHandler().handle(db, start)
            persist_event(db, workflow)
            new_session = TrafegoEventHandler().handle(db, workflow)
            all_sessions = sessions(db)
            assert len(all_sessions) == 2
            assert all_sessions[0].status == STATUS_ENCERRADA
            assert all_sessions[0].motivo_encerramento == MOTIVO_MUDANCA_ETAPA
            assert new_session.workflow_etapa_id == "etapa-2"
            assert new_session.status == STATUS_ATIVA


def test_workflow_advance_does_not_open_without_explicit_execution(session_factory):
    start = event(payload={"statusNovo": "em_execucao", "usuarioId": "user-1", "workflowEtapaId": "etapa-1"})
    workflow = event(
        tipo=DomainEventType.WORKFLOW_ETAPA_AVANCADA.value,
        entidade_tipo="workflow",
        entidade_id="workflow-1",
        payload={"demandaId": "demanda-1", "etapaDestinoId": "etapa-2", "usuarioId": "user-1"},
        occurred_at=start.occurred_at + timedelta(minutes=15),
    )
    with session_factory() as db:
        with db.begin():
            persist_event(db, start)
            TrafegoEventHandler().handle(db, start)
            persist_event(db, workflow)
            TrafegoEventHandler().handle(db, workflow)
            all_sessions = sessions(db)
            assert len(all_sessions) == 1
            assert all_sessions[0].status == STATUS_ENCERRADA


def test_workflow_advance_does_not_open_without_destination_responsavel(session_factory):
    workflow = event(
        tipo=DomainEventType.WORKFLOW_ETAPA_AVANCADA.value,
        entidade_tipo="workflow",
        entidade_id="workflow-1",
        usuario_id=None,
        payload={"demandaId": "demanda-1", "etapaDestinoId": "etapa-2", "iniciarExecucao": True},
    )
    with session_factory() as db:
        with db.begin():
            persist_event(db, workflow)
            assert TrafegoEventHandler().handle(db, workflow) is None
        assert sessions(db) == []


def test_workflow_block_closes_session(session_factory):
    start = event(payload={"statusNovo": "em_execucao", "usuarioId": "user-1"})
    block = event(
        tipo=DomainEventType.WORKFLOW_ETAPA_BLOQUEADA.value,
        entidade_tipo="workflow",
        entidade_id="workflow-1",
        payload={"demandaId": "demanda-1", "usuarioId": "user-1"},
        occurred_at=start.occurred_at + timedelta(minutes=20),
    )
    with session_factory() as db:
        with db.begin():
            persist_event(db, start)
            TrafegoEventHandler().handle(db, start)
            persist_event(db, block)
            closed = TrafegoEventHandler().handle(db, block)
            assert closed.status == STATUS_ENCERRADA
            assert closed.motivo_encerramento == MOTIVO_BLOQUEIO


def test_reprocessing_start_event_is_safe(session_factory):
    evento = event(payload={"statusNovo": "em_execucao", "usuarioId": "user-1"})
    with session_factory() as db:
        with db.begin():
            persist_event(db, evento)
            first = TrafegoEventHandler().handle(db, evento)
            second = TrafegoEventHandler().handle(db, evento)
            assert first.id == second.id
        assert len(sessions(db)) == 1


def test_reprocessing_finish_event_is_safe(session_factory):
    start = event(payload={"statusNovo": "em_execucao", "usuarioId": "user-1"})
    finish = event(payload={"statusNovo": "pausada", "usuarioId": "user-1"}, occurred_at=start.occurred_at + timedelta(minutes=10))
    with session_factory() as db:
        with db.begin():
            persist_event(db, start)
            TrafegoEventHandler().handle(db, start)
            persist_event(db, finish)
            first = TrafegoEventHandler().handle(db, finish)
            second = TrafegoEventHandler().handle(db, finish)
            assert first.id == second.id
            assert second.duracao_segundos == 600


def test_handler_rollback_removes_session(session_factory):
    evento = event(payload={"statusNovo": "em_execucao", "usuarioId": "user-1"})
    with pytest.raises(RuntimeError):
        with session_factory() as db:
            with db.begin():
                persist_event(db, evento)
                TrafegoEventHandler().handle(db, evento)
                raise RuntimeError("rollback")

    with session_factory() as db:
        assert sessions(db) == []


def test_service_can_open_by_department_when_user_absent(session_factory):
    evento = event(usuario_id=None, payload={"statusNovo": "em_execucao", "departamentoId": "departamento-1"})
    with session_factory() as db:
        with db.begin():
            persist_event(db, evento)
            sessao = TrafegoEventHandler().handle(db, evento)
            assert sessao.departamento_id == "departamento-1"
            assert sessao.usuario_id is None
