"""Atomicidade da resolução de SLA na criação da Demanda (Fase 2G.6D1 — auditoria e correção).

Contexto do bug (encontrado e corrigido ANTES de qualquer commit/push/deploy — nunca chegou a
ir ao ar): `RegraExpedienteService.get_ou_criar` executa `db.commit()` quando precisa semear o
singleton da Empresa pela primeira vez. Antes desta correção, esse commit podia acontecer
DEPOIS que a Demanda, a referência e o número operacional já tinham sido `add`/`flush`ados na
mesma Session (dentro de `_resolver_e_persistir_sla_snapshot` → `resolver_e_calcular_sla` →
`get_regra_calculo`) — uma falha tardia (ex.: publicação de evento) só desfazia o que veio
depois desse commit, deixando uma Demanda órfã (com número operacional/código de referência
reais, mas sem snapshot de SLA) persistida no banco mesmo com a criação tendo "falhado" pro
chamador.

A correção (`DemandaService._garantir_regra_expediente_antes_da_criacao`) garante a
`RegraExpediente` da Empresa ANTES de qualquer escrita da criação — restaurando o invariante
que sempre protegeu `get_ou_criar` (documentado na própria classe: seu commit autônomo só é
seguro se nada mais estiver pendente na Session no momento em que roda)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.sla_regra import SlaRegra
from app.schemas.demanda import DemandaCreate
from app.services.demanda_service import DemandaService
from app.services.regra_expediente_service import RegraExpedienteService


def _sla_regra_ativa_com_expediente(db: Session, empresa: Empresa, **overrides) -> SlaRegra:
    agora = datetime.now(timezone.utc)
    base = dict(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        nome=f"SLA {uuid.uuid4().hex[:8]}",
        nome_normalizado=f"sla {uuid.uuid4().hex[:8]}",
        descricao=None,
        prioridade_alvo=None,
        departamento_id=None,
        cliente_id=None,
        prioridade_regra=1,
        prazo_primeira_resposta_quantidade=4,
        prazo_primeira_resposta_unidade="horas",
        prazo_resolucao_quantidade=48,
        prazo_resolucao_unidade="horas",
        # True de propósito: obriga o fluxo a passar por get_regra_calculo/get_ou_criar.
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


def _contagem_regra_expediente(db: Session, empresa: Empresa) -> int:
    return db.execute(
        text("SELECT count(*) FROM regra_expediente WHERE empresa_id = :eid"), {"eid": empresa.id}
    ).scalar()


def _contagem_demandas(db: Session, empresa: Empresa) -> int:
    return db.execute(
        text("SELECT count(*) FROM demandas WHERE empresa_id = :eid"), {"eid": empresa.id}
    ).scalar()


def _forcar_falha_tardia(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quebra `_publish_event` — chamado por `create_demanda` só DEPOIS que
    `_resolver_e_persistir_sla_snapshot` já rodou por completo. Simula qualquer erro tardio
    real (workflow, vínculo, evento) que aconteça depois do ponto onde o bug se manifestava."""

    def _quebrado(*args, **kwargs):
        raise RuntimeError("falha forçada pelo teste — simula erro tardio na criação")

    monkeypatch.setattr(DemandaService, "_publish_event", _quebrado)


# --------------------------------------------------------------------------------------
# Cenário principal: Empresa sem RegraExpediente + falha tardia
# --------------------------------------------------------------------------------------


def test_falha_tardia_sem_regra_expediente_previa_nao_deixa_demanda_orfa(
    db_session: Session, empresa: Empresa, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _contagem_regra_expediente(db_session, empresa) == 0, "pré-condição: sem RegraExpediente"

    _sla_regra_ativa_com_expediente(db_session, empresa)
    _forcar_falha_tardia(monkeypatch)

    with pytest.raises(RuntimeError):
        DemandaService().create_demanda(
            db_session, DemandaCreate(nome="Demanda que deve falhar"), empresa_id=empresa.id
        )

    # 1. Zero Demanda nova — nenhuma linha órfã, nenhum snapshot parcial.
    assert _contagem_demandas(db_session, empresa) == 0

    # 2. A RegraExpediente PODE existir — sua criação (se aconteceu) rodou ANTES da parte
    # operacional da Demanda, via _garantir_regra_expediente_antes_da_criacao. Ela não faz
    # parte do rollback da criação da Demanda; é bootstrap isolado, documentado como tal.
    assert _contagem_regra_expediente(db_session, empresa) == 1

    # 3. A criação seguinte não deve ter gap de numeração.
    monkeypatch.undo()  # a criação seguinte deve suceder de verdade — sem o evento quebrado
    criada = DemandaService().create_demanda(
        db_session, DemandaCreate(nome="Demanda que deve suceder"), empresa_id=empresa.id
    )
    assert criada.numero_operacional == 1, "a tentativa abortada não pode ter queimado o número 1"
    assert criada.codigo_referencia == "T26000001", "nem a referência"


# --------------------------------------------------------------------------------------
# Singleton já existente
# --------------------------------------------------------------------------------------


def test_falha_tardia_com_regra_expediente_ja_existente_ainda_atomica(
    db_session: Session, empresa: Empresa, monkeypatch: pytest.MonkeyPatch
) -> None:
    # RegraExpediente pré-existente (bootstrap normal, fora do teste de atomicidade).
    RegraExpedienteService().get_ou_criar(db_session, empresa_id=empresa.id)
    assert _contagem_regra_expediente(db_session, empresa) == 1

    _sla_regra_ativa_com_expediente(db_session, empresa)
    _forcar_falha_tardia(monkeypatch)

    with pytest.raises(RuntimeError):
        DemandaService().create_demanda(
            db_session, DemandaCreate(nome="Demanda que deve falhar"), empresa_id=empresa.id
        )

    assert _contagem_demandas(db_session, empresa) == 0
    assert _contagem_regra_expediente(db_session, empresa) == 1  # continua existindo, não duplicou

    monkeypatch.undo()  # a criação seguinte deve suceder de verdade — sem o evento quebrado
    criada = DemandaService().create_demanda(
        db_session, DemandaCreate(nome="Demanda que deve suceder"), empresa_id=empresa.id
    )
    assert criada.numero_operacional == 1
    assert criada.codigo_referencia == "T26000001"


# --------------------------------------------------------------------------------------
# Sem SLA — Alternativa B: RegraExpediente não é criada à toa
# --------------------------------------------------------------------------------------


def test_sem_sla_candidata_criacao_normal_nao_cria_regra_expediente(
    db_session: Session, empresa: Empresa
) -> None:
    assert _contagem_regra_expediente(db_session, empresa) == 0

    criada = DemandaService().create_demanda(
        db_session, DemandaCreate(nome="Demanda sem SLA"), empresa_id=empresa.id
    )

    assert criada.sla_regra_id is None
    assert criada.sla_primeira_resposta_limite_em is None
    # Alternativa B (preferida pelo kickoff): sem nenhuma SlaRegra candidata, a criação nunca
    # chama get_ou_criar — Empresas que não usam SLA não ganham uma RegraExpediente de graça.
    assert _contagem_regra_expediente(db_session, empresa) == 0
