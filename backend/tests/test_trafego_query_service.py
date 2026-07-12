from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.sessao_trabalho import SessaoTrabalho
from app.services.trafego_query_service import TrafegoQueryService


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


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 7, 12, hour, minute, tzinfo=timezone.utc)


def add_session(
    db,
    *,
    empresa_id="empresa-1",
    demanda_id="demanda-1",
    usuario_id="user-1",
    departamento_id=None,
    workflow_etapa_id="etapa-1",
    status="ativa",
    inicio_em=None,
    fim_em=None,
    updated_at=None,
):
    inicio = inicio_em or dt(10)
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
        updated_at=updated_at or fim_em or inicio,
    )
    db.add(sessao)
    db.flush()
    return sessao


def test_agora_empty(session_factory):
    with session_factory() as db:
        assert TrafegoQueryService().list_agora(db, now_utc=dt(12)) == []


def test_agora_active_order_elapsed_and_pagination(session_factory):
    with session_factory() as db:
        with db.begin():
            older = add_session(db, demanda_id="demanda-1", inicio_em=dt(9))
            newer = add_session(db, demanda_id="demanda-2", inicio_em=dt(10))
        result = TrafegoQueryService().list_agora(db, limit=1, offset=0, now_utc=dt(12))
        assert [item.sessao_id for item in result] == [uuid4().__class__(older.id)]
        assert result[0].tempo_decorrido_segundos == 10800
        result_2 = TrafegoQueryService().list_agora(db, limit=1, offset=1, now_utc=dt(12))
        assert [item.sessao_id for item in result_2] == [uuid4().__class__(newer.id)]


def test_agora_filters_and_future_session_has_zero_elapsed(session_factory):
    with session_factory() as db:
        with db.begin():
            add_session(db, demanda_id="demanda-1", usuario_id="user-1", inicio_em=dt(13))
            add_session(db, demanda_id="demanda-2", usuario_id="user-2", inicio_em=dt(9))
        result = TrafegoQueryService().list_agora(db, usuario_id="user-1", now_utc=dt(12))
        assert len(result) == 1
        assert result[0].demanda_id == "demanda-1"
        assert result[0].tempo_decorrido_segundos == 0


def test_carga_by_user_uses_single_now_and_distinct_demands(session_factory):
    with session_factory() as db:
        with db.begin():
            add_session(db, demanda_id="demanda-1", usuario_id="user-1", inicio_em=dt(9), updated_at=dt(11))
            add_session(db, demanda_id="demanda-2", usuario_id="user-1", inicio_em=dt(10), updated_at=dt(11, 30))
            add_session(db, demanda_id="demanda-2", usuario_id=None, departamento_id="dep-1", inicio_em=dt(9))
        result = TrafegoQueryService().get_carga(db, empresa_id="empresa-1", agrupamento="usuario", now_utc=dt(12))
        assert len(result) == 1
        item = result[0]
        assert item.agrupamento_id == "user-1"
        assert item.sessoes_ativas == 2
        assert item.demandas_distintas == 2
        assert item.tempo_ativo_total_segundos == 18000
        assert item.inicio_mais_antigo == dt(9)
        assert item.ultima_atualizacao == dt(11, 30)


def test_carga_by_department_ignores_null_group(session_factory):
    with session_factory() as db:
        with db.begin():
            add_session(db, demanda_id="demanda-1", departamento_id="dep-1", inicio_em=dt(9))
            add_session(db, demanda_id="demanda-2", departamento_id=None, inicio_em=dt(9))
        result = TrafegoQueryService().get_carga(db, empresa_id="empresa-1", agrupamento="departamento", now_utc=dt(12))
        assert [item.agrupamento_id for item in result] == ["dep-1"]


def test_carga_invalid_group_raises(session_factory):
    with session_factory() as db:
        with pytest.raises(ValueError):
            TrafegoQueryService().get_carga(db, empresa_id="empresa-1", agrupamento="setor", now_utc=dt(12))


def test_resumo_empty_and_default_period(session_factory):
    with session_factory() as db:
        result = TrafegoQueryService().get_resumo(db, empresa_id="empresa-1", now_utc=dt(12))
        assert result.sessoes_ativas == 0
        assert result.tempo_operacional_estimado_segundos == 0
        assert result.inicio_periodo == dt(12) - timedelta(hours=24)
        assert result.fim_periodo == dt(12)


def test_resumo_closed_active_and_metrics(session_factory):
    with session_factory() as db:
        with db.begin():
            add_session(db, demanda_id="demanda-1", usuario_id="user-1", departamento_id="dep-1", status="encerrada", inicio_em=dt(9), fim_em=dt(10))
            add_session(db, demanda_id="demanda-2", usuario_id="user-2", departamento_id="dep-1", status="ativa", inicio_em=dt(11))
        result = TrafegoQueryService().get_resumo(
            db,
            empresa_id="empresa-1",
            data_inicio=dt(8),
            data_fim=dt(12),
            now_utc=dt(12),
        )
        assert result.sessoes_encerradas == 1
        assert result.sessoes_ativas == 1
        assert result.demandas_distintas == 2
        assert result.usuarios_distintos == 2
        assert result.departamentos_distintos == 1
        assert result.tempo_operacional_estimado_segundos == 7200
        assert result.tempo_medio_sessao_segundos == 3600
        assert result.maior_sessao_segundos == 3600


def test_resumo_period_clipping_cases(session_factory):
    with session_factory() as db:
        with db.begin():
            add_session(db, demanda_id="before", status="encerrada", inicio_em=dt(7), fim_em=dt(8))
            add_session(db, demanda_id="start", status="encerrada", inicio_em=dt(8), fim_em=dt(10))
            add_session(db, demanda_id="end", status="encerrada", inicio_em=dt(11), fim_em=dt(14))
            add_session(db, demanda_id="all", status="encerrada", inicio_em=dt(7), fim_em=dt(14))
        result = TrafegoQueryService().get_resumo(
            db,
            empresa_id="empresa-1",
            data_inicio=dt(9),
            data_fim=dt(12),
            now_utc=dt(12),
        )
        assert result.sessoes_encerradas == 3
        assert result.demandas_distintas == 3
        assert result.tempo_operacional_estimado_segundos == 3600 + 3600 + 10800
        assert result.maior_sessao_segundos == 10800


def test_resumo_active_future_has_zero_and_does_not_count(session_factory):
    with session_factory() as db:
        with db.begin():
            add_session(db, status="ativa", inicio_em=dt(13))
        result = TrafegoQueryService().get_resumo(
            db,
            empresa_id="empresa-1",
            data_inicio=dt(10),
            data_fim=dt(14),
            now_utc=dt(9),
        )
        assert result.sessoes_ativas == 0
        assert result.tempo_operacional_estimado_segundos == 0


def test_resumo_only_data_inicio_and_only_data_fim(session_factory):
    service = TrafegoQueryService()
    inicio, fim = service.resolve_period(data_inicio=dt(10), data_fim=None, now_utc=dt(12))
    assert inicio == dt(10)
    assert fim == dt(12)
    inicio, fim = service.resolve_period(data_inicio=None, data_fim=dt(12), now_utc=dt(20))
    assert inicio == dt(12) - timedelta(hours=24)
    assert fim == dt(12)


def test_resumo_rejects_invalid_period(session_factory):
    with session_factory() as db:
        with pytest.raises(ValueError):
            TrafegoQueryService().get_resumo(db, empresa_id="empresa-1", data_inicio=dt(12), data_fim=dt(10), now_utc=dt(12))


def test_resumo_filters(session_factory):
    with session_factory() as db:
        with db.begin():
            add_session(db, demanda_id="demanda-1", usuario_id="user-1", departamento_id="dep-1", status="encerrada", inicio_em=dt(9), fim_em=dt(10))
            add_session(db, demanda_id="demanda-2", usuario_id="user-2", departamento_id="dep-2", status="encerrada", inicio_em=dt(9), fim_em=dt(10))
        result = TrafegoQueryService().get_resumo(db, empresa_id="empresa-1", usuario_id="user-1", data_inicio=dt(8), data_fim=dt(12), now_utc=dt(12))
        assert result.demandas_distintas == 1
        assert result.usuarios_distintos == 1
        result = TrafegoQueryService().get_resumo(db, empresa_id="empresa-1", departamento_id="dep-2", data_inicio=dt(8), data_fim=dt(12), now_utc=dt(12))
        assert result.demandas_distintas == 1
        result = TrafegoQueryService().get_resumo(db, empresa_id="empresa-1", demanda_id="demanda-2", data_inicio=dt(8), data_fim=dt(12), now_utc=dt(12))
        assert result.demandas_distintas == 1
