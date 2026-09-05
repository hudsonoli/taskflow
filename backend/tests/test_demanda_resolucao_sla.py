"""Resolução do SLA pela primeira transição real para `concluida` (Fase 2G.6D3B).

Definição V1 aprovada no relatório da 2G.6D3A: `sla_resolvido_em` fixado só na primeira
transição real (`status_anterior != concluida AND status_final == concluida`). `cancelada` e
`arquivada` nunca preenchem. Mesmo mecanismo de UPDATE condicional/atomicidade já validado
para `sla_primeira_resposta_em` (2G.6D2B) — ver test_demanda_primeira_resposta.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.expediente import JanelaDia, RegraExpediente
from app.models.demanda import Demanda
from app.models.empresa import Empresa
from app.models.sla_regra import SlaRegra
from app.repositories.demanda_repository import DemandaRepository
from app.schemas.demanda import DemandaUpdate
from app.services.demanda_service import DemandaService

# --------------------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------------------


def _regra_todos_os_dias() -> RegraExpediente:
    """Mesma técnica de `dentro_do_expediente` em test_demanda.py: janela 00:00–23:59 nos 7
    dias, pra estes testes não dependerem nem da hora nem do dia da semana em que a suíte
    rodar (ver Fase 2G.6E2-PRE — os testes G e P transicionam para `em_execucao`, que passa
    pelo gate de expediente, e não usavam nenhum override — falhavam sempre que a suíte
    rodasse fora de 09:00–19:00 num dia útil, e SEMPRE aos sábados/domingos)."""
    janela = JanelaDia(ativo=True, manha_inicio="00:00", manha_fim="12:00", tarde_inicio="12:00", tarde_fim="23:59")
    return RegraExpediente(ativo=True, tolerancia_retomada_minutos=0, dias={dia: janela for dia in range(7)})


@pytest.fixture()
def dentro_do_expediente(app):
    """Equivalente local ao fixture homônimo de test_demanda.py — não importado de lá porque
    não há precedente no projeto de fixture compartilhada entre módulos de teste fora de
    conftest.py, e promover para conftest.py estaria fora do escopo desta correção."""
    from app.api.routes import demandas as rotas

    original = rotas.demanda_service.regra_expediente
    rotas.demanda_service.regra_expediente = _regra_todos_os_dias()
    yield
    rotas.demanda_service.regra_expediente = original


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _ler_demanda(client: TestClient, demanda_id: str) -> dict:
    resposta = client.get(f"/demandas/{demanda_id}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _patch_status(client: TestClient, demanda_id: str, status: str) -> dict:
    resposta = client.patch(f"/demandas/{demanda_id}", json={"status": status})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


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
        considerar_apenas_expediente=False,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    base.update(overrides)
    regra = SlaRegra(**base)
    db.add(regra)
    db.flush()
    return regra


def _parse(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


def _demanda_direta(db: Session, empresa: Empresa, *, status: str = "rascunho", **overrides) -> Demanda:
    agora = datetime.now(timezone.utc)
    base = dict(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_referencia=f"T{uuid.uuid4().hex[:8]}",
        ano_referencia=94,
        sequencial_referencia=1,
        numero_operacional=int(uuid.uuid4().int % 900000) + 100000,
        nome="Demanda",
        status=status,
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    base.update(overrides)
    demanda = Demanda(**base)
    db.add(demanda)
    db.flush()
    return demanda


# --------------------------------------------------------------------------------------
# A-C: indicador derivado
# --------------------------------------------------------------------------------------


def test_a_conclui_antes_do_prazo_e_dentro(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    demanda_dict = _criar_demanda(client_admin)
    demanda = db_session.get(Demanda, demanda_dict["id"])
    demanda.sla_resolucao_limite_em = datetime.now(timezone.utc) + timedelta(hours=10)
    db_session.add(demanda)
    db_session.flush()

    lida = _patch_status(client_admin, demanda_dict["id"], "concluida")
    assert lida["slaResolvidoEm"] is not None
    assert lida["slaResolvidoDentroPrazo"] is True


def test_b_exatamente_no_limite_e_dentro(client_admin: TestClient, db_session: Session) -> None:
    demanda_dict = _criar_demanda(client_admin)
    lida = _patch_status(client_admin, demanda_dict["id"], "concluida")
    resolvido_em = _parse(lida["slaResolvidoEm"])

    demanda = db_session.get(Demanda, demanda_dict["id"])
    demanda.sla_resolucao_limite_em = resolvido_em
    db_session.add(demanda)
    db_session.flush()

    relida = _ler_demanda(client_admin, demanda_dict["id"])
    assert relida["slaResolvidoDentroPrazo"] is True


def test_c_depois_do_prazo_e_fora(client_admin: TestClient, db_session: Session) -> None:
    demanda_dict = _criar_demanda(client_admin)
    demanda = db_session.get(Demanda, demanda_dict["id"])
    demanda.sla_resolucao_limite_em = datetime.now(timezone.utc) - timedelta(hours=10)
    db_session.add(demanda)
    db_session.flush()

    lida = _patch_status(client_admin, demanda_dict["id"], "concluida")
    assert lida["slaResolvidoDentroPrazo"] is False


# --------------------------------------------------------------------------------------
# D-E: sem SLA / Demanda antiga
# --------------------------------------------------------------------------------------


def test_d_sem_sla_grava_resolucao_mesmo_assim(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    assert demanda["slaRegraId"] is None
    lida = _patch_status(client_admin, demanda["id"], "concluida")
    assert lida["slaResolvidoEm"] is not None
    assert lida["slaResolvidoDentroPrazo"] is None


def test_e_demanda_antiga_sem_nenhum_campo_sla_grava_normalmente(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    demanda_antiga = _demanda_direta(db_session, empresa, status="rascunho")

    resposta = client_admin.patch(f"/demandas/{demanda_antiga.id}", json={"status": "concluida"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["slaResolvidoEm"] is not None
    assert resposta.json()["slaResolvidoDentroPrazo"] is None


# --------------------------------------------------------------------------------------
# F-G: idempotência e reabertura
# --------------------------------------------------------------------------------------


def test_f_concluida_para_concluida_nao_sobrescreve(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    primeira = _patch_status(client_admin, demanda["id"], "concluida")["slaResolvidoEm"]

    repetida = _patch_status(client_admin, demanda["id"], "concluida")
    assert repetida["slaResolvidoEm"] == primeira


def test_g_reabre_e_conclui_novamente_preserva_primeira_resolucao(
    client_admin: TestClient, dentro_do_expediente
) -> None:
    demanda = _criar_demanda(client_admin)
    primeira = _patch_status(client_admin, demanda["id"], "concluida")["slaResolvidoEm"]

    reaberta = _patch_status(client_admin, demanda["id"], "em_execucao")
    assert reaberta["slaResolvidoEm"] == primeira  # reabrir não limpa

    concluida_de_novo = _patch_status(client_admin, demanda["id"], "concluida")
    assert concluida_de_novo["slaResolvidoEm"] == primeira  # não sobrescreve


# --------------------------------------------------------------------------------------
# H-I: cancelada / arquivada nunca fixam
# --------------------------------------------------------------------------------------


def test_h_cancelada_nao_fixa_resolucao(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    _sla_regra(db_session, empresa)
    demanda = _criar_demanda(client_admin)
    assert demanda["slaResolucaoLimiteEm"] is not None  # tem deadline de verdade

    cancelada = _patch_status(client_admin, demanda["id"], "cancelada")
    assert cancelada["slaResolvidoEm"] is None


def test_i_arquivar_sem_nunca_ter_concluido_nao_fixa_resolucao(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.post(
        f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "teste"}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["slaResolvidoEm"] is None


# --------------------------------------------------------------------------------------
# J: rollback atômico
# --------------------------------------------------------------------------------------


def test_j_falha_apos_fixar_resolucao_reverte_status_e_campo(
    db_session: Session, empresa: Empresa, monkeypatch: pytest.MonkeyPatch
) -> None:
    demanda = _demanda_direta(db_session, empresa, status="em_execucao")
    db_session.commit()  # checkpoint: sobrevive ao rollback provocado abaixo

    def _publish_event_quebrado(*args, **kwargs):
        raise RuntimeError("falha forçada — simula erro tardio após fixar resolução")

    monkeypatch.setattr(DemandaService, "_publish_event", _publish_event_quebrado)

    demanda_recarregada = db_session.get(Demanda, demanda.id)
    with pytest.raises(RuntimeError):
        DemandaService().update_demanda(
            db_session, demanda_recarregada, DemandaUpdate(status="concluida")
        )

    demanda_pos_rollback = db_session.get(Demanda, demanda.id)
    assert demanda_pos_rollback.status == "em_execucao"  # não avançou
    assert demanda_pos_rollback.sla_resolvido_em is None


# --------------------------------------------------------------------------------------
# K: concorrência — duas conexões reais independentes
# --------------------------------------------------------------------------------------


def test_k_concorrencia_apenas_uma_transacao_fixa_resolucao(test_engine: Engine) -> None:
    """Mesma técnica de test_q em test_demanda_primeira_resposta.py — duas conexões reais e
    independentes, não `db_session` (cujo rollback isolaria as duas)."""
    empresa_id = str(uuid.uuid4())
    demanda_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)

    conexao_setup = test_engine.connect()
    conexao_setup.execute(
        Empresa.__table__.insert().values(
            id=empresa_id, nome="Empresa Concorrencia Resolucao", documento=None,
            codigo_interno=f"CONCR-{uuid.uuid4().hex[:8]}".upper(), status="ativa",
            created_at=agora, updated_at=agora,
        )
    )
    conexao_setup.execute(
        Demanda.__table__.insert().values(
            id=demanda_id, empresa_id=empresa_id, codigo_referencia=f"T{uuid.uuid4().hex[:8]}",
            ano_referencia=93, sequencial_referencia=1, numero_operacional=999906, nome="Demanda",
            status="concluida", prioridade="media", created_at=agora, updated_at=agora,
        )
    )
    conexao_setup.commit()
    conexao_setup.close()

    try:
        timestamp_vencedor = agora.replace(microsecond=333333)
        conexao_a = test_engine.connect()
        resultado_a = conexao_a.execute(
            sa_update(Demanda)
            .where(
                Demanda.id == demanda_id,
                Demanda.empresa_id == empresa_id,
                Demanda.sla_resolvido_em.is_(None),
            )
            .values(sla_resolvido_em=timestamp_vencedor)
        )
        assert resultado_a.rowcount == 1
        conexao_a.commit()
        conexao_a.close()

        timestamp_perdedor = agora.replace(microsecond=444444)
        conexao_b = test_engine.connect()
        resultado_b = conexao_b.execute(
            sa_update(Demanda)
            .where(
                Demanda.id == demanda_id,
                Demanda.empresa_id == empresa_id,
                Demanda.sla_resolvido_em.is_(None),
            )
            .values(sla_resolvido_em=timestamp_perdedor)
        )
        assert resultado_b.rowcount == 0
        conexao_b.commit()
        conexao_b.close()

        conexao_verificacao = test_engine.connect()
        valor_final = conexao_verificacao.execute(
            select(Demanda.sla_resolvido_em).where(Demanda.id == demanda_id)
        ).scalar()
        conexao_verificacao.close()
        assert valor_final == timestamp_vencedor
        assert valor_final != timestamp_perdedor
    finally:
        conexao_limpeza = test_engine.connect()
        conexao_limpeza.execute(sa_delete(Demanda).where(Demanda.id == demanda_id))
        conexao_limpeza.execute(sa_delete(Empresa).where(Empresa.id == empresa_id))
        conexao_limpeza.commit()
        conexao_limpeza.close()


# --------------------------------------------------------------------------------------
# L: cross-tenant
# --------------------------------------------------------------------------------------


def test_l_update_condicional_repository_respeita_empresa_id(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    demanda = _demanda_direta(db_session, empresa, status="concluida")

    fixou = DemandaRepository().fixar_resolucao_sla_se_vazia(
        db_session, demanda_id=demanda.id, empresa_id=outra_empresa.id, timestamp=datetime.now(timezone.utc)
    )
    assert fixou is False
    db_session.refresh(demanda)
    assert demanda.sla_resolvido_em is None


# --------------------------------------------------------------------------------------
# M: write protection
# --------------------------------------------------------------------------------------


def test_m_payload_create_com_sla_resolvido_em_rejeitado_422(client_admin: TestClient) -> None:
    resposta = client_admin.post(
        "/demandas", json={"nome": "x", "slaResolvidoEm": "2030-01-01T00:00:00Z"}
    )
    assert resposta.status_code == 422, resposta.text


def test_m_payload_update_com_dentro_prazo_rejeitado_422(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}", json={"slaResolvidoDentroPrazo": True}
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# N-O: regra SLA alterada/arquivada depois
# --------------------------------------------------------------------------------------


def test_n_regra_alterada_depois_nao_muda_resolucao(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    regra = _sla_regra(db_session, empresa)
    demanda = _criar_demanda(client_admin)
    resolvida = _patch_status(client_admin, demanda["id"], "concluida")

    regra.prazo_resolucao_quantidade = 999
    db_session.add(regra)
    db_session.flush()

    relida = _ler_demanda(client_admin, demanda["id"])
    assert relida["slaResolvidoEm"] == resolvida["slaResolvidoEm"]
    assert relida["slaResolucaoLimiteEm"] == resolvida["slaResolucaoLimiteEm"]


def test_o_regra_arquivada_depois_nao_muda_resolucao(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    regra = _sla_regra(db_session, empresa)
    demanda = _criar_demanda(client_admin)
    resolvida = _patch_status(client_admin, demanda["id"], "concluida")

    regra.status = "arquivado"
    db_session.add(regra)
    db_session.flush()

    relida = _ler_demanda(client_admin, demanda["id"])
    assert relida["slaResolvidoEm"] == resolvida["slaResolvidoEm"]


# --------------------------------------------------------------------------------------
# P: Demanda já concluída antes da fase — sem backfill
# --------------------------------------------------------------------------------------


def test_p_demanda_ja_concluida_antes_da_fase_sem_backfill(
    client_admin: TestClient, db_session: Session, empresa: Empresa, dentro_do_expediente
) -> None:
    """Simula uma Demanda que já estava `concluida` no momento do deploy desta fase —
    `sla_resolvido_em` não é preenchido retroativamente. Só uma transição real POSTERIOR
    (reabrir e concluir de novo) fixa o campo — limitação transitória documentada."""
    demanda_ja_concluida = _demanda_direta(db_session, empresa, status="concluida")

    lida = _ler_demanda(client_admin, demanda_ja_concluida.id)
    assert lida["slaResolvidoEm"] is None  # sem backfill

    _patch_status(client_admin, demanda_ja_concluida.id, "em_execucao")
    reconcluida = _patch_status(client_admin, demanda_ja_concluida.id, "concluida")
    assert reconcluida["slaResolvidoEm"] is not None  # a PRÓXIMA transição real fixa
