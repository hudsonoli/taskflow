"""Fase 8A — progressão do snapshot de Workflow da Demanda: concluir (execução) / aprovar (aprovação) a etapa ATUAL e ativar a próxima.

Provas: materialização (primeira etapa iniciada); percurso completo Execução → Execução → Aprovação → Execução; a última etapa encerra o
workflow SEM concluir a Demanda; autoridade (responsável, admin/gestor do tenant, Head; Atendimento/operador alheio → 403; etapa sem
responsável só gestão; token de plataforma recusado); tenant; etapa errada/futura/anterior/de outra demanda; workflow ausente/vazio/
concluído; retry; concorrência REAL (duas sessões, locks do Postgres); um único evento por ação; sem salto de etapa; `podeAvancar`
calculado no servidor (inclusive zerado na leitura da Pauta).
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import create_platform_token
from app.models.demanda import Demanda
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _atendimento, _client_para, _operador_comum
from tests.test_demanda import _departamento

EVENTO_CONCLUIDA = "demanda.workflow_etapa_concluida"
EVENTO_APROVADA = "demanda.workflow_etapa_aprovada"


# ======================================================================================
# helpers
# ======================================================================================


def _etapa(nome: str, tipo: str = "execucao", usuarios: list[str] | None = None, departamentos: list[str] | None = None) -> dict:
    return {
        "nome": nome,
        "tipo": tipo,
        "quantidadeAntesDeadline": 1,
        "unidadePrazo": "dias_corridos",
        "usuarioResponsavelIds": usuarios or [],
        "departamentoResponsavelIds": departamentos or [],
    }


def _demanda_com_workflow(client: TestClient, etapas: list[dict], **extra) -> dict:
    modelo = client.post("/workflow-modelos", json={"nome": f"WF {uuid.uuid4().hex[:8]}", "etapas": etapas})
    assert modelo.status_code == 201, modelo.text
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", "workflowModeloId": modelo.json()["id"], **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _por_ordem(demanda: dict) -> list[dict]:
    return sorted(demanda["workflowEtapas"], key=lambda e: e["ordem"])


def _url(demanda_id: str, etapa_id: str, acao: str) -> str:
    return f"/demandas/{demanda_id}/workflow/etapas/{etapa_id}/{acao}"


def _estado(client: TestClient, demanda_id: str) -> dict:
    resposta = client.get(f"/demandas/{demanda_id}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _eventos(db: Session, demanda_id: str, tipo: str | None = None) -> list[Evento]:
    consulta = select(Evento).where(Evento.entidade_tipo == "demanda", Evento.entidade_id == demanda_id)
    if tipo:
        consulta = consulta.where(Evento.tipo == tipo)
    return list(db.scalars(consulta.order_by(Evento.occurred_at.asc())).all())


def _quatro_etapas(client: TestClient, **extra) -> dict:
    """Briefing(exec) → Criação(exec) → Aprovação(aprov) → Publicação(exec)."""
    return _demanda_com_workflow(
        client,
        [_etapa("Briefing"), _etapa("Criação"), _etapa("Aprovação", "aprovacao"), _etapa("Publicação")],
        **extra,
    )


# ======================================================================================
# materialização
# ======================================================================================


def test_nova_demanda_primeira_etapa_iniciada_e_demais_nao(client_admin: TestClient) -> None:
    demanda = _quatro_etapas(client_admin)
    etapas = _por_ordem(demanda)
    assert demanda["etapaAtualId"] == etapas[0]["id"]
    assert etapas[0]["iniciadaEm"] is not None
    assert all(e["iniciadaEm"] is None for e in etapas[1:])
    assert all(e["status"] == "pendente" for e in etapas)  # INITIAL_STEP_STATUS: sem regressão para consumidores
    assert all(e["concluidaEm"] is None and e["concluidaPorUsuarioId"] is None for e in etapas)


# ======================================================================================
# percurso completo
# ======================================================================================


def test_percurso_completo_e_demanda_nao_e_concluida(client_admin: TestClient, usuario_admin: Usuario, db_session: Session) -> None:
    demanda = _quatro_etapas(client_admin)
    e1, e2, e3, e4 = _por_ordem(demanda)

    r = client_admin.post(_url(demanda["id"], e1["id"], "concluir"))
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["etapaAtualId"] == e2["id"]
    por_id = {e["id"]: e for e in corpo["workflowEtapas"]}
    assert por_id[e1["id"]]["status"] == "concluida"
    assert por_id[e1["id"]]["concluidaPorUsuarioId"] == usuario_admin.id
    assert por_id[e1["id"]]["concluidaEm"] is not None
    assert por_id[e2["id"]]["iniciadaEm"] is not None  # a próxima passa a ter início
    assert por_id[e3["id"]]["iniciadaEm"] is None and por_id[e4["id"]]["iniciadaEm"] is None

    assert client_admin.post(_url(demanda["id"], e2["id"], "concluir")).json()["etapaAtualId"] == e3["id"]
    assert client_admin.post(_url(demanda["id"], e3["id"], "aprovar")).json()["etapaAtualId"] == e4["id"]

    final = client_admin.post(_url(demanda["id"], e4["id"], "concluir"))
    assert final.status_code == 200, final.text
    corpo = final.json()
    assert corpo["etapaAtualId"] is None  # workflow concluído (derivado: todas concluídas)
    assert all(e["status"] == "concluida" for e in corpo["workflowEtapas"])
    assert all(e["concluidaPorUsuarioId"] == usuario_admin.id for e in corpo["workflowEtapas"])
    assert not any(e["podeAvancar"] for e in corpo["workflowEtapas"])
    # FINAL_WORKFLOW_EFFECT_ON_DEMAND = NENHUM: a Demanda não é concluída sozinha
    assert corpo["status"] == demanda["status"] != "concluida"
    assert corpo["prazoEtapaAtual"] == demanda["prazoEtapaAtual"]  # STEP_DEADLINE_AUTO_UPDATE = NÃO

    # um evento por ação, do tipo certo (execução → concluída; aprovação → aprovada), com os IDs estruturados
    concluidas = _eventos(db_session, demanda["id"], EVENTO_CONCLUIDA)
    aprovadas = _eventos(db_session, demanda["id"], EVENTO_APROVADA)
    assert len(concluidas) == 3 and len(aprovadas) == 1
    assert aprovadas[0].usuario_id == usuario_admin.id
    payload = aprovadas[0].payload
    assert payload["etapaId"] == e3["id"] and payload["etapaNome"] == "Aprovação" and payload["etapaOrdem"] == e3["ordem"]
    assert payload["etapaTipo"] == "aprovacao" and payload["atorUsuarioId"] == usuario_admin.id
    assert payload["proximaEtapaId"] == e4["id"] and payload["proximaEtapaNome"] == "Publicação"
    assert payload["workflowConcluido"] is False
    ultimo = concluidas[-1].payload
    assert ultimo["proximaEtapaId"] is None and ultimo["workflowConcluido"] is True
    assert "email" not in str(payload).lower()


def test_evento_aparece_na_timeline_da_demanda(client_admin: TestClient) -> None:
    demanda = _quatro_etapas(client_admin)
    e1 = _por_ordem(demanda)[0]
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    tipos = [item["tipo"] for item in client_admin.get(f"/demandas/{demanda['id']}/historico").json()]
    assert EVENTO_CONCLUIDA in tipos


def test_snapshot_nao_acompanha_edicao_do_template(client_admin: TestClient) -> None:
    demanda = _quatro_etapas(client_admin)
    modelo_id = demanda["workflowModeloId"]
    edicao = client_admin.patch(f"/workflow-modelos/{modelo_id}", json={"etapas": [_etapa("Só uma")]})
    assert edicao.status_code == 200, edicao.text
    e1 = _por_ordem(demanda)[0]
    r = client_admin.post(_url(demanda["id"], e1["id"], "concluir"))
    assert r.status_code == 200
    assert [e["nome"] for e in _por_ordem(r.json())] == ["Briefing", "Criação", "Aprovação", "Publicação"]


# ======================================================================================
# ação × tipo
# ======================================================================================


def test_acao_incompativel_com_o_tipo_da_etapa_422(client_admin: TestClient, db_session: Session) -> None:
    demanda = _quatro_etapas(client_admin)
    e1, e2, e3, _ = _por_ordem(demanda)
    assert client_admin.post(_url(demanda["id"], e1["id"], "aprovar")).status_code == 422  # execução não é aprovada
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert client_admin.post(_url(demanda["id"], e2["id"], "concluir")).status_code == 200
    assert client_admin.post(_url(demanda["id"], e3["id"], "concluir")).status_code == 422  # aprovação não é "concluída"
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e3["id"]
    assert len(_eventos(db_session, demanda["id"], EVENTO_APROVADA)) == 0


def test_cliente_nao_escolhe_o_destino_payload_e_ignorado(client_admin: TestClient) -> None:
    demanda = _quatro_etapas(client_admin)
    e1, e2, e3, e4 = _por_ordem(demanda)
    r = client_admin.post(_url(demanda["id"], e1["id"], "concluir"), json={"nextStepId": e4["id"], "proximaEtapaId": e4["id"]})
    assert r.status_code == 200
    assert r.json()["etapaAtualId"] == e2["id"]  # o servidor decide: ordem seguinte, nunca a pedida


# ======================================================================================
# etapa errada
# ======================================================================================


def test_etapa_futura_e_etapa_anterior_409_sem_efeito(client_admin: TestClient, db_session: Session) -> None:
    demanda = _quatro_etapas(client_admin)
    e1, e2, e3, e4 = _por_ordem(demanda)
    futura = client_admin.post(_url(demanda["id"], e2["id"], "concluir"))  # pula a 1
    assert futura.status_code == 409 and futura.json()["detail"]["code"] == "ETAPA_NAO_ATUAL"
    assert client_admin.post(_url(demanda["id"], e4["id"], "concluir")).status_code == 409
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e1["id"]
    assert _eventos(db_session, demanda["id"], EVENTO_CONCLUIDA) == []

    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    anterior = client_admin.post(_url(demanda["id"], e1["id"], "concluir"))
    assert anterior.status_code == 409 and anterior.json()["detail"]["code"] == "ETAPA_JA_CONCLUIDA"
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e2["id"]  # não avançou de novo
    assert len(_eventos(db_session, demanda["id"], EVENTO_CONCLUIDA)) == 1


def test_etapa_de_outra_demanda_404(client_admin: TestClient) -> None:
    a = _quatro_etapas(client_admin)
    b = _quatro_etapas(client_admin)
    etapa_de_b = _por_ordem(b)[0]
    assert client_admin.post(_url(a["id"], etapa_de_b["id"], "concluir")).status_code == 404
    assert _estado(client_admin, b["id"])["etapaAtualId"] == etapa_de_b["id"]
    assert client_admin.post(_url(a["id"], str(uuid.uuid4()), "concluir")).status_code == 404


def test_retry_da_mesma_acao_nao_avanca_duas_vezes(client_admin: TestClient, db_session: Session) -> None:
    demanda = _quatro_etapas(client_admin)
    e1, e2, *_ = _por_ordem(demanda)
    primeira = client_admin.post(_url(demanda["id"], e1["id"], "concluir"))
    segunda = client_admin.post(_url(demanda["id"], e1["id"], "concluir"))
    assert (primeira.status_code, segunda.status_code) == (200, 409)
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e2["id"]
    assert len(_eventos(db_session, demanda["id"], EVENTO_CONCLUIDA)) == 1


# ======================================================================================
# estados do workflow
# ======================================================================================


def test_demanda_sem_workflow_409_e_nao_cria_workflow(client_admin: TestClient, db_session: Session) -> None:
    demanda = client_admin.post("/demandas", json={"nome": "Sem workflow"}).json()
    r = client_admin.post(_url(demanda["id"], str(uuid.uuid4()), "concluir"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "SEM_WORKFLOW"
    assert _estado(client_admin, demanda["id"])["workflowEtapas"] == []


def test_workflow_sem_etapas_409_controlado(client_admin: TestClient, db_session: Session) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Única")])
    db_session.query(DemandaWorkflowEtapa).filter_by(demanda_id=demanda["id"]).delete()
    db_session.commit()
    r = client_admin.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "concluir"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "WORKFLOW_SEM_ETAPAS"


def test_workflow_concluido_409_sem_alteracao(client_admin: TestClient, db_session: Session) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Única")])
    unica = _por_ordem(demanda)[0]
    assert client_admin.post(_url(demanda["id"], unica["id"], "concluir")).status_code == 200
    antes = _estado(client_admin, demanda["id"])
    r = client_admin.post(_url(demanda["id"], unica["id"], "concluir"))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] in {"WORKFLOW_CONCLUIDO", "ETAPA_JA_CONCLUIDA"}
    assert _estado(client_admin, demanda["id"])["workflowEtapas"] == antes["workflowEtapas"]
    assert len(_eventos(db_session, demanda["id"], EVENTO_CONCLUIDA)) == 1


def test_demanda_arquivada_409(client_admin: TestClient) -> None:
    demanda = _quatro_etapas(client_admin)
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "teste"}).status_code == 200
    e1 = _por_ordem(demanda)[0]
    r = client_admin.post(_url(demanda["id"], e1["id"], "concluir"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "DEMANDA_ARQUIVADA"
    assert not any(e["podeAvancar"] for e in _estado(client_admin, demanda["id"])["workflowEtapas"])


def test_etapa_atual_pausada_legada_nao_avanca(client_admin: TestClient, db_session: Session) -> None:
    demanda = _quatro_etapas(client_admin)
    e1 = _por_ordem(demanda)[0]
    db_session.query(DemandaWorkflowEtapa).filter_by(id=e1["id"]).update({"status": "pausada"})
    db_session.commit()
    r = client_admin.post(_url(demanda["id"], e1["id"], "concluir"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "ETAPA_PAUSADA"
    assert not any(e["podeAvancar"] for e in _estado(client_admin, demanda["id"])["workflowEtapas"])


def test_snapshot_historico_sem_iniciada_em_avanca_sem_inventar_inicio(client_admin: TestClient, db_session: Session) -> None:
    demanda = _quatro_etapas(client_admin)
    e1, e2, *_ = _por_ordem(demanda)
    db_session.query(DemandaWorkflowEtapa).filter_by(id=e1["id"]).update({"iniciada_em": None})  # como um snapshot pré-8A
    db_session.commit()
    r = client_admin.post(_url(demanda["id"], e1["id"], "concluir"))
    assert r.status_code == 200
    por_id = {e["id"]: e for e in r.json()["workflowEtapas"]}
    assert por_id[e1["id"]]["iniciadaEm"] is None  # início histórico desconhecido continua desconhecido
    assert por_id[e1["id"]]["concluidaEm"] is not None
    assert por_id[e2["id"]]["iniciadaEm"] is not None


# ======================================================================================
# autoridade
# ======================================================================================


def test_responsavel_individual_pode_operador_alheio_nao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    resp = _operador_comum(db_session, empresa, sufixo="wf-resp")
    alheio = _operador_comum(db_session, empresa, sufixo="wf-alheio")
    demanda = _demanda_com_workflow(
        client_admin,
        [_etapa("Briefing", usuarios=[resp.id]), _etapa("Aprovar", "aprovacao", usuarios=[resp.id])],
        usuarioResponsavelIds=[resp.id, alheio.id],  # o alheio VÊ a demanda (visibilidade ≠ autoridade)
    )
    e1, e2 = _por_ordem(demanda)
    cliente_alheio = _client_para(app, alheio)
    assert cliente_alheio.get(f"/demandas/{demanda['id']}").status_code == 200
    assert cliente_alheio.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 403
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e1["id"]

    cliente_resp = _client_para(app, resp)
    r = cliente_resp.post(_url(demanda["id"], e1["id"], "concluir"))
    assert r.status_code == 200, r.text
    assert {e["id"]: e for e in r.json()["workflowEtapas"]}[e1["id"]]["concluidaPorUsuarioId"] == resp.id
    assert cliente_alheio.post(_url(demanda["id"], e2["id"], "aprovar")).status_code == 403
    assert cliente_resp.post(_url(demanda["id"], e2["id"], "aprovar")).status_code == 200


def test_admin_e_gestor_do_tenant_avancam_qualquer_etapa(app, client_admin: TestClient, client_gestor: TestClient, usuario_gestor: Usuario, usuario_admin: Usuario) -> None:
    demanda = _quatro_etapas(client_admin)
    e1, e2, *_ = _por_ordem(demanda)
    r1 = client_gestor.post(_url(demanda["id"], e1["id"], "concluir"))
    assert r1.status_code == 200
    r2 = client_admin.post(_url(demanda["id"], e2["id"], "concluir"))
    assert r2.status_code == 200
    por_id = {e["id"]: e for e in r2.json()["workflowEtapas"]}
    assert por_id[e1["id"]]["concluidaPorUsuarioId"] == usuario_gestor.id
    assert por_id[e2["id"]]["concluidaPorUsuarioId"] == usuario_admin.id


def test_head_do_departamento_da_etapa_pode_e_head_de_outro_nao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    maria = _operador_comum(db_session, empresa, sufixo="wf-head")
    criacao = _departamento(db_session, empresa, nome="Criação", responsavel_usuario_id=maria.id)
    lider_de_outro = _operador_comum(db_session, empresa, sufixo="wf-head-outro")
    social = _departamento(db_session, empresa, nome="Social", responsavel_usuario_id=lider_de_outro.id)
    demanda = _demanda_com_workflow(
        client_admin,
        [_etapa("Criar", departamentos=[criacao.id]), _etapa("Fim")],
        departamentoResponsavelIds=[criacao.id, social.id],  # ambos os Heads enxergam a demanda
    )
    e1 = _por_ordem(demanda)[0]
    assert _client_para(app, lider_de_outro).post(_url(demanda["id"], e1["id"], "concluir")).status_code == 403
    r = _client_para(app, maria).post(_url(demanda["id"], e1["id"], "concluir"))
    assert r.status_code == 200, r.text
    assert {e["id"]: e for e in r.json()["workflowEtapas"]}[e1["id"]]["concluidaPorUsuarioId"] == maria.id


def test_atendimento_sem_outra_autoridade_403(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    ana = _operador_comum(db_session, empresa, sufixo="wf-ana")
    atendimento = _atendimento(db_session, empresa, ana)
    resp = _operador_comum(db_session, empresa, sufixo="wf-resp2")
    demanda = _demanda_com_workflow(
        client_admin, [_etapa("Briefing", usuarios=[resp.id])], departamentoResponsavelIds=[atendimento.id]
    )
    cliente_ana = _client_para(app, ana)
    assert cliente_ana.get(f"/demandas/{demanda['id']}").status_code == 200  # Atendimento enxerga
    r = cliente_ana.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "concluir"))
    assert r.status_code == 403
    assert not _estado(cliente_ana, demanda["id"])["workflowEtapas"][0]["podeAvancar"]


def test_atendimento_que_e_responsavel_explicito_pode(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    ana = _operador_comum(db_session, empresa, sufixo="wf-ana2")
    atendimento = _atendimento(db_session, empresa, ana)
    demanda = _demanda_com_workflow(client_admin, [_etapa("Briefing", usuarios=[ana.id])], departamentoResponsavelIds=[atendimento.id])
    assert _client_para(app, ana).post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "concluir")).status_code == 200


def test_etapa_sem_responsavel_so_admin_gestor(app, db_session: Session, empresa: Empresa, client_admin: TestClient, client_gestor: TestClient) -> None:
    op = _operador_comum(db_session, empresa, sufixo="wf-sem-resp")
    demanda = _demanda_com_workflow(client_admin, [_etapa("A"), _etapa("B")], usuarioResponsavelIds=[op.id])
    e1, e2 = _por_ordem(demanda)
    assert _client_para(app, op).post(_url(demanda["id"], e1["id"], "concluir")).status_code == 403
    assert client_gestor.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert client_admin.post(_url(demanda["id"], e2["id"], "concluir")).status_code == 200


def test_etapa_com_responsavel_e_departamento_autoridade_aditiva(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    resp = _operador_comum(db_session, empresa, sufixo="wf-adit-resp")
    head = _operador_comum(db_session, empresa, sufixo="wf-adit-head")
    depto = _departamento(db_session, empresa, nome="Mídia", responsavel_usuario_id=head.id)
    demanda = _demanda_com_workflow(
        client_admin,
        [_etapa("Usuário ou depto", usuarios=[resp.id], departamentos=[depto.id]), _etapa("Depois")],
        usuarioResponsavelIds=[resp.id],
        departamentoResponsavelIds=[depto.id],
    )
    e1, _ = _por_ordem(demanda)
    # qualquer UMA das fontes basta: o Head (sem ser o responsável individual) age...
    assert _client_para(app, head).post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200


def test_token_de_plataforma_nao_tem_autoridade_de_tenant(app, client_admin: TestClient, usuario_admin: Usuario) -> None:
    demanda = _quatro_etapas(client_admin)
    e1 = _por_ordem(demanda)[0]
    token = create_platform_token(sub=usuario_admin.id, administrador_id=str(uuid.uuid4()))
    plataforma = TestClient(app)
    plataforma.headers["Authorization"] = f"Bearer {token}"
    r = plataforma.post(_url(demanda["id"], e1["id"], "concluir"))
    assert r.status_code in (401, 403)
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e1["id"]


# ======================================================================================
# tenant
# ======================================================================================


def test_cross_tenant_404_sem_efeito(app, db_session: Session, outra_empresa: Empresa, client_admin: TestClient) -> None:
    demanda = _quatro_etapas(client_admin)
    e1 = _por_ordem(demanda)[0]
    intruso = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="wf-intruso")
    cliente_b = _client_para(app, intruso)
    for acao in ("concluir", "aprovar"):
        assert cliente_b.post(_url(demanda["id"], e1["id"], acao)).status_code == 404
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e1["id"]


# ======================================================================================
# podeAvancar (read model calculado no servidor)
# ======================================================================================


def test_pode_avancar_so_na_etapa_atual_para_quem_tem_autoridade(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    resp = _operador_comum(db_session, empresa, sufixo="wf-pa-resp")
    alheio = _operador_comum(db_session, empresa, sufixo="wf-pa-alheio")
    demanda = _demanda_com_workflow(
        client_admin,
        [_etapa("A", usuarios=[resp.id]), _etapa("B", usuarios=[resp.id])],
        usuarioResponsavelIds=[resp.id, alheio.id],
    )
    e1, e2 = _por_ordem(demanda)

    def pode(client: TestClient) -> list[bool]:
        return [e["podeAvancar"] for e in _por_ordem(_estado(client, demanda["id"]))]

    assert pode(client_admin) == [True, False]  # só a atual
    assert pode(_client_para(app, resp)) == [True, False]
    assert pode(_client_para(app, alheio)) == [False, False]
    # a listagem usa o mesmo cálculo
    lista = _client_para(app, resp).get("/demandas", params={"limit": 50}).json()
    item = next(d for d in lista if d["id"] == demanda["id"])
    assert [e["podeAvancar"] for e in _por_ordem(item)] == [True, False]
    client_admin.post(_url(demanda["id"], e1["id"], "concluir"))
    assert pode(_client_para(app, resp)) == [False, True]


def test_leitura_pela_pauta_global_nunca_oferece_acao(app, client_admin: TestClient) -> None:
    demanda = _quatro_etapas(client_admin)
    assert any(e["podeAvancar"] for e in _estado(client_admin, demanda["id"])["workflowEtapas"])
    pauta = client_admin.get(f"/demandas/{demanda['id']}", params={"escopo": "pauta"})
    assert pauta.status_code == 200
    assert not any(e["podeAvancar"] for e in pauta.json()["workflowEtapas"])
    lista = client_admin.get("/demandas", params={"escopo": "pauta", "limit": 200}).json()
    item = next(d for d in lista if d["id"] == demanda["id"])
    assert not any(e["podeAvancar"] for e in item["workflowEtapas"])


def test_escrita_ignora_o_parametro_da_pauta(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    """Quem VÊ a demanda pela Pauta (Atendimento) mas está fora do escopo-base não age: 404 e nada muda."""
    ana = _operador_comum(db_session, empresa, sufixo="wf-pauta-ana")
    _atendimento(db_session, empresa, ana)
    outro = _departamento(db_session, empresa, nome="Digital")
    demanda = _demanda_com_workflow(client_admin, [_etapa("A")], departamentoResponsavelIds=[outro.id])
    cliente_ana = _client_para(app, ana)
    assert cliente_ana.get(f"/demandas/{demanda['id']}", params={"escopo": "pauta"}).status_code == 200
    e1 = _por_ordem(demanda)[0]
    r = cliente_ana.post(_url(demanda["id"], e1["id"], "concluir"), params={"escopo": "pauta"})
    assert r.status_code == 404
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e1["id"]


def test_sem_n_mais_um_na_listagem(client_admin: TestClient, db_session: Session) -> None:
    from sqlalchemy import event

    for _ in range(6):
        _quatro_etapas(client_admin)
    contagem = {"n": 0}

    def contar(conn, cursor, statement, parameters, context, executemany):
        contagem["n"] += 1

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", contar)
    try:
        assert client_admin.get("/demandas", params={"limit": 50}).status_code == 200
        pequena = contagem["n"]
        contagem["n"] = 0
        for _ in range(6):
            _quatro_etapas(client_admin)
        contagem["n"] = 0
        assert client_admin.get("/demandas", params={"limit": 50}).status_code == 200
        grande = contagem["n"]
    finally:
        event.remove(engine, "before_cursor_execute", contar)
    assert grande == pequena  # número de queries não cresce com o número de demandas/etapas


# ======================================================================================
# concorrência REAL (sessões separadas, dados commitados, locks do Postgres)
# ======================================================================================


@pytest.fixture()
def cenario_commitado(test_engine):
    """Dados REAIS (commit) para duas sessões independentes disputarem a mesma etapa; removidos no fim."""
    Fabrica = sessionmaker(bind=test_engine)
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(timezone.utc)
    ids: dict[str, str | list[str]] = {}
    with Fabrica() as db:
        empresa = Empresa(id=str(uuid.uuid4()), nome="Empresa Conc", codigo_interno=f"CONC-{sufixo}".upper(), status="ativa", created_at=agora, updated_at=agora)
        db.add(empresa)
        db.flush()
        usuario = Usuario(
            id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"conc-{sufixo}", nome="Gestor Conc",
            email=f"conc-{sufixo}@teste.taskfloww.local", perfil_base="gestor", acesso_sistema=True, status="ativo",
            created_at=agora, updated_at=agora,
        )
        db.add(usuario)
        db.flush()
        demanda = Demanda(
            id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"T26{sufixo[:6]}", ano_referencia=26,
            sequencial_referencia=1, numero_operacional=1, identificador="#1", nome="Concorrência", status="planejada",
            prioridade="media", sinalizada=False, created_at=agora, updated_at=agora,
        )
        db.add(demanda)
        db.flush()
        etapas = [
            DemandaWorkflowEtapa(
                id=str(uuid.uuid4()), demanda_id=demanda.id, ordem=i, nome=f"Etapa {i}", tipo="aprovacao" if i == 2 else "execucao",
                quantidade_antes_deadline=1, unidade_prazo="dias_corridos", status="pendente",
                iniciada_em=agora if i == 1 else None, created_at=agora, updated_at=agora,
            )
            for i in (1, 2, 3, 4)
        ]
        db.add_all(etapas)
        db.commit()
        ids = {"empresa": empresa.id, "usuario": usuario.id, "demanda": demanda.id, "etapas": [e.id for e in etapas]}
    try:
        yield Fabrica, ids
    finally:
        with Fabrica() as db:
            db.query(Evento).filter(Evento.entidade_id == ids["demanda"]).delete()
            db.query(Demanda).filter(Demanda.id == ids["demanda"]).delete()  # etapas caem por CASCADE
            db.query(Usuario).filter(Usuario.id == ids["usuario"]).delete()
            db.query(Empresa).filter(Empresa.id == ids["empresa"]).delete()
            db.commit()


def _disputar(Fabrica, ids, etapa_id: str, acao: str, tentativas: int = 2) -> list[str]:
    from app.services.demanda_workflow_service import DemandaWorkflowConflitoError, DemandaWorkflowService

    barreira = threading.Barrier(tentativas)
    resultados: list[str] = []
    trava = threading.Lock()

    def tentar() -> None:
        with Fabrica() as db:
            servico = DemandaWorkflowService()
            ator = db.get(Usuario, ids["usuario"])
            demanda = db.get(Demanda, ids["demanda"])
            barreira.wait(timeout=10)
            try:
                getattr(servico, f"{acao}_etapa")(db, demanda, etapa_id=etapa_id, actor=ator)
                saida = "ok"
            except DemandaWorkflowConflitoError as exc:
                saida = f"conflito:{exc.codigo}"
            with trava:
                resultados.append(saida)

    threads = [threading.Thread(target=tentar) for _ in range(tentativas)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return resultados


def test_duas_aprovacoes_simultaneas_uma_vence_a_outra_conflita(cenario_commitado) -> None:
    Fabrica, ids = cenario_commitado
    e1, e2, e3, e4 = ids["etapas"]
    assert _disputar(Fabrica, ids, e1, "concluir", tentativas=1) == ["ok"]  # chega à etapa de aprovação (2)

    resultados = _disputar(Fabrica, ids, e2, "aprovar", tentativas=4)
    assert sorted(resultados) == ["conflito:ETAPA_JA_CONCLUIDA"] * 3 + ["ok"], resultados

    with Fabrica() as db:
        etapas = {e.ordem: e for e in db.scalars(select(DemandaWorkflowEtapa).where(DemandaWorkflowEtapa.demanda_id == ids["demanda"])).all()}
        assert [etapas[o].status for o in (1, 2, 3, 4)] == ["concluida", "concluida", "pendente", "pendente"]  # NÃO pulou a 3
        assert etapas[3].iniciada_em is not None and etapas[4].iniciada_em is None
        total = db.scalar(select(func.count()).select_from(Evento).where(Evento.entidade_id == ids["demanda"], Evento.tipo == EVENTO_APROVADA))
        assert total == 1  # um único evento
        assert db.scalar(select(func.count()).select_from(Evento).where(Evento.entidade_id == ids["demanda"], Evento.tipo == EVENTO_CONCLUIDA)) == 1
