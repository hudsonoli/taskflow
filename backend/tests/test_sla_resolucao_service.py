"""Testes de app/services/sla_resolucao_service.py (Fase 2G.6C) — composição resolver +
calculadora. Cobertura leve: a lógica de resolução e a de cálculo já têm suíte própria em
test_sla_resolver.py e test_calculadora_expediente.py; aqui só confirma que a composição liga
as duas peças corretamente, sem persistir nada, sem publicar Evento, sem endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.calculadora_expediente import calcular_data_limite
from app.core.relogio import agora_local
from app.models.empresa import Empresa
from app.models.sla_regra import SlaRegra
from app.services.regra_expediente_service import RegraExpedienteService
from app.services.sla_resolucao_service import resolver_e_calcular_sla


def _sla_regra(db: Session, empresa: Empresa, **overrides) -> SlaRegra:
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(timezone.utc)
    base = dict(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        nome=f"SLA {sufixo}",
        nome_normalizado=f"sla {sufixo}",
        descricao=None,
        prioridade_alvo=None,
        departamento_id=None,
        cliente_id=None,
        prioridade_regra=100,
        prazo_primeira_resposta_quantidade=4,
        prazo_primeira_resposta_unidade="horas",
        prazo_resolucao_quantidade=48,
        prazo_resolucao_unidade="horas",
        considerar_apenas_expediente=True,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    base.update(overrides)
    regra = SlaRegra(**base)
    db.add(regra)
    db.flush()
    return regra


def test_sem_regra_combinando_retorna_none(db_session: Session, empresa: Empresa) -> None:
    resultado = resolver_e_calcular_sla(db_session, empresa_id=empresa.id, prioridade="alta")
    assert resultado is None


def test_resolve_e_calcula_os_dois_prazos(db_session: Session, empresa: Empresa) -> None:
    regra = _sla_regra(db_session, empresa)
    inicio = datetime(2026, 8, 28, 18, 30, tzinfo=agora_local().tzinfo)  # sexta, fuso da app

    resultado = resolver_e_calcular_sla(db_session, empresa_id=empresa.id, prioridade="alta", inicio=inicio)

    assert resultado is not None
    assert resultado.regra.id == regra.id

    regra_calculo = RegraExpedienteService().get_regra_calculo(db_session, empresa_id=empresa.id)
    esperado_primeira_resposta = calcular_data_limite(
        inicio,
        regra.prazo_primeira_resposta_quantidade,
        regra.prazo_primeira_resposta_unidade,
        regra.considerar_apenas_expediente,
        regra_calculo,
    )
    esperado_resolucao = calcular_data_limite(
        inicio,
        regra.prazo_resolucao_quantidade,
        regra.prazo_resolucao_unidade,
        regra.considerar_apenas_expediente,
        regra_calculo,
    )
    assert resultado.prazo_primeira_resposta_em == esperado_primeira_resposta
    assert resultado.prazo_resolucao_em == esperado_resolucao


def test_inicio_default_usa_agora_local(db_session: Session, empresa: Empresa) -> None:
    _sla_regra(
        db_session,
        empresa,
        prazo_primeira_resposta_unidade="dias_corridos",
        prazo_primeira_resposta_quantidade=1,
        prazo_resolucao_unidade="dias_corridos",
        prazo_resolucao_quantidade=2,
    )

    antes = agora_local()
    resultado = resolver_e_calcular_sla(db_session, empresa_id=empresa.id, prioridade="alta")
    depois = agora_local()

    assert resultado is not None
    # dias_corridos não olha expediente: resultado = inicio (não informado) + N dias exatos.
    # Reconstruindo o `inicio` implícito a partir do resultado, deve cair entre `antes`/`depois`
    # — confirma que `agora_local()` foi usado como default, não um valor arbitrário.
    inicio_usado = resultado.prazo_primeira_resposta_em - timedelta(days=1)
    assert antes <= inicio_usado <= depois
