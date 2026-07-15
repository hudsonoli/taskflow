from datetime import timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.event_types import DomainEventType, EVENT_TYPES
from app.models import Evento
from app.schemas.evento import EventoCreate
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.evento_service import EventoService


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


def count_eventos(session_factory) -> int:
    with session_factory() as db:
        return db.scalar(select(func.count()).select_from(Evento))


def list_eventos(session_factory) -> list[Evento]:
    with session_factory() as db:
        return list(db.scalars(select(Evento)).all())


def publish_evento(session_factory, **overrides):
    publisher = DomainEventPublisher()
    payload = {
        "tipo": DomainEventType.PROJETO_CRIADO,
        "empresa_id": "empresa-1",
        "agencia_id": "agencia-principal",
        "entidade_tipo": "projeto",
        "entidade_id": "projeto-1",
        "usuario_id": "user-1",
        "payload": {"nome": "Campanha Julho"},
        "metadata": {"source": "test"},
    }
    payload.update(overrides)
    with session_factory() as db:
        with db.begin():
            evento = publisher.publish(db, **payload)
            evento_id = evento.id
            created_at = evento.created_at
            occurred_at = evento.occurred_at
        return evento_id, created_at, occurred_at


def test_publish_projeto_event(session_factory):
    evento_id, _, _ = publish_evento(session_factory, tipo=DomainEventType.PROJETO_CRIADO)

    eventos = list_eventos(session_factory)
    assert len(eventos) == 1
    assert eventos[0].id == evento_id
    assert eventos[0].tipo == DomainEventType.PROJETO_CRIADO.value
    assert eventos[0].entidade_tipo == "projeto"


def test_publish_demanda_event(session_factory):
    publish_evento(
        session_factory,
        tipo=DomainEventType.DEMANDA_PRIORIDADE_ALTERADA,
        entidade_tipo="demanda",
        entidade_id="demanda-1",
        payload={"prioridadeAnterior": "media", "prioridadeNova": "alta"},
    )

    eventos = list_eventos(session_factory)
    assert eventos[0].tipo == DomainEventType.DEMANDA_PRIORIDADE_ALTERADA.value
    assert eventos[0].payload == {"prioridadeAnterior": "media", "prioridadeNova": "alta"}


def test_publish_workflow_event(session_factory):
    publish_evento(
        session_factory,
        tipo=DomainEventType.WORKFLOW_ETAPA_AVANCADA,
        entidade_tipo="workflow",
        entidade_id="workflow-1",
        payload={
            "etapaOrigemId": "etapa-1",
            "etapaDestinoId": "etapa-2",
            "etapaOrigemNome": "Briefing",
            "etapaDestinoNome": "Redação",
        },
    )

    eventos = list_eventos(session_factory)
    assert eventos[0].tipo == DomainEventType.WORKFLOW_ETAPA_AVANCADA.value
    assert eventos[0].payload["etapaDestinoNome"] == "Redação"


def test_payload_and_metadata_are_persisted(session_factory):
    publish_evento(
        session_factory,
        payload={"statusAnterior": "planejamento", "statusNovo": "ativo"},
        metadata={"source": "api.projetos", "requestId": "req-1"},
    )

    eventos = list_eventos(session_factory)
    assert eventos[0].payload == {"statusAnterior": "planejamento", "statusNovo": "ativo"}
    assert eventos[0].metadata_ == {"source": "api.projetos", "requestId": "req-1"}


def test_correlation_id_and_causation_id_are_persisted(session_factory):
    correlation_id = uuid4()
    causation_id = uuid4()

    publish_evento(session_factory, correlation_id=correlation_id, causation_id=causation_id)

    eventos = list_eventos(session_factory)
    assert eventos[0].correlation_id == str(correlation_id)
    assert eventos[0].causation_id == str(causation_id)


def test_timestamps_are_timezone_aware_utc_before_commit(session_factory):
    _, created_at, occurred_at = publish_evento(session_factory)

    assert created_at.tzinfo is not None
    assert created_at.utcoffset() == timezone.utc.utcoffset(created_at)
    assert occurred_at.tzinfo is not None
    assert occurred_at.utcoffset() == timezone.utc.utcoffset(occurred_at)


def test_invalid_event_type_is_rejected_and_not_persisted(session_factory):
    publisher = DomainEventPublisher()

    with session_factory() as db:
        with pytest.raises(ValueError, match="Tipo de evento não catalogado"):
            with db.begin():
                publisher.publish(
                    db,
                    tipo="projeto.nao_catalogado",
                    empresa_id="empresa-1",
                    entidade_tipo="projeto",
                    entidade_id="projeto-1",
                    payload={"nome": "Campanha Julho"},
                )

    assert count_eventos(session_factory) == 0


def test_nested_sensitive_key_in_payload_is_rejected(session_factory):
    publisher = DomainEventPublisher()

    with session_factory() as db:
        with pytest.raises(ValueError, match="Payload contém chave sensível"):
            with db.begin():
                publisher.publish(
                    db,
                    tipo=DomainEventType.DEMANDA_ATUALIZADA,
                    empresa_id="empresa-1",
                    entidade_tipo="demanda",
                    entidade_id="demanda-1",
                    payload={"alteracao": [{"dadosBancarios": {"conta": "123"}}]},
                )

    assert count_eventos(session_factory) == 0


def test_nested_sensitive_key_in_metadata_is_rejected(session_factory):
    publisher = DomainEventPublisher()

    with session_factory() as db:
        with pytest.raises(ValueError, match="Metadata contém chave sensível"):
            with db.begin():
                publisher.publish(
                    db,
                    tipo=DomainEventType.PROJETO_ATUALIZADO,
                    empresa_id="empresa-1",
                    entidade_tipo="projeto",
                    entidade_id="projeto-1",
                    payload={"nome": "Campanha Julho"},
                    metadata={"headers": {"Authorization": "Bearer token"}},
                )

    assert count_eventos(session_factory) == 0


def test_commit_false_with_external_commit_persists_event(session_factory):
    publish_evento(session_factory, tipo=DomainEventType.DEMANDA_CRIADA)

    assert count_eventos(session_factory) == 1


def test_commit_false_with_rollback_does_not_persist_event(session_factory):
    publisher = DomainEventPublisher()

    with pytest.raises(RuntimeError):
        with session_factory() as db:
            with db.begin():
                publisher.publish(
                    db,
                    tipo=DomainEventType.WORKFLOW_ETAPA_BLOQUEADA,
                    empresa_id="empresa-1",
                    entidade_tipo="workflow",
                    entidade_id="workflow-1",
                    payload={"etapaId": "etapa-1"},
                )
                raise RuntimeError("forca rollback")

    assert count_eventos(session_factory) == 0


def test_commit_true_service_behavior_is_preserved(session_factory):
    service = EventoService()
    data = EventoCreate(
        empresaId="empresa-1",
        agenciaId="agencia-principal",
        tipo=DomainEventType.PROJETO_STATUS_ALTERADO.value,
        entidadeTipo="projeto",
        entidadeId="projeto-1",
        usuarioId="user-1",
        payload={"statusAnterior": "planejamento", "statusNovo": "ativo"},
        metadata={"source": "test"},
    )

    with session_factory() as db:
        evento = service.create_evento(db, data, commit=True)
        evento_id = evento.id

    eventos = list_eventos(session_factory)
    assert len(eventos) == 1
    assert eventos[0].id == evento_id


def test_event_types_are_centralized_from_enum():
    assert DomainEventType.PROJETO_CRIADO.value in EVENT_TYPES
    assert DomainEventType.DEMANDA_CRIADA.value in EVENT_TYPES
    assert DomainEventType.WORKFLOW_ETAPA_AVANCADA.value in EVENT_TYPES
    assert EVENT_TYPES == frozenset(event_type.value for event_type in DomainEventType)
