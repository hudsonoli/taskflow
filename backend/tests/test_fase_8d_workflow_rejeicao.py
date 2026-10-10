"""Fase 8D — rejeição/devolução de etapa do Workflow.

Só a etapa ATUAL de APROVAÇÃO pode ser rejeitada, com MOTIVO obrigatório, e o workflow volta para a etapa IMEDIATAMENTE anterior (o servidor decide).
A aprovação rejeitada volta a `pendente` (sem início/conclusão/ator); a anterior é reaberta (`pendente`, `iniciada_em` = agora, conclusão zerada). O
histórico é append-only (um evento de rejeição com o retorno e o motivo; nada é apagado). A etapa reaberta notifica seus responsáveis (mecanismo da 8C) e
o escopo derivado/Meu Dia (8C.1) acompanha sozinho. Aprovar × rejeitar e rejeitar × rejeitar são serializados pelo mesmo lock da 8A.
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
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _atendimento, _client_para, _operador_comum
from tests.test_demanda import _departamento
from tests.test_fase_8a_workflow_progressao import _demanda_com_workflow, _etapa, _por_ordem, _url

REJEITADA = "demanda.workflow_etapa_rejeitada"
ATUALIZADA = "demanda.workflow_etapa_atualizada"
MOTIVO = "A arte não segue o manual de marca"


def _op(db: Session, empresa: Empresa, nome: str) -> Usuario:
    return _operador_comum(db, empresa, sufixo=f"8d-{nome}-{uuid.uuid4().hex[:4]}")


def _rejeitar(client: TestClient, demanda: dict, etapa_id: str, motivo: str | None = MOTIVO, **extra):
    corpo = {**({"motivo": motivo} if motivo is not None else {}), **extra}
    return client.post(_url(demanda["id"], etapa_id, "rejeitar"), json=corpo)


def _eventos(db: Session, demanda_id: str, tipo: str) -> list[Evento]:
    return list(db.scalars(select(Evento).where(Evento.entidade_id == demanda_id, Evento.tipo == tipo).order_by(Evento.occurred_at.asc())).all())


def _estado(client: TestClient, demanda_id: str) -> dict:
    resposta = client.get(f"/demandas/{demanda_id}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _por_id(demanda: dict) -> dict[str, dict]:
    return {e["id"]: e for e in demanda["workflowEtapas"]}


def _central(client: TestClient) -> list[dict]:
    return client.get("/notificacoes", params={"limit": 100}).json()["itens"]


def _cenario(app, db: Session, empresa: Empresa, client_admin: TestClient, **extra):
    """1 Criação (a) → 2 Aprovação (b) → 3 Publicação. `a`/`b` NÃO são responsáveis da demanda (o escopo derivado da 8C.1 cuida do acesso)."""
    a, b = _op(db, empresa, "a"), _op(db, empresa, "b")
    demanda = _demanda_com_workflow(
        client_admin, [_etapa("Criação", usuarios=[a.id]), _etapa("Aprovação", "aprovacao", usuarios=[b.id]), _etapa("Publicação")], **extra
    )
    db.commit()
    return a, b, demanda, _por_ordem(demanda), _client_para(app, a), _client_para(app, b)


# ======================================================================================
# fluxo principal e estado
# ======================================================================================


def test_rejeitar_devolve_para_a_anterior_e_ajusta_o_estado(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200  # a aprovação (2) passa a ser a atual
    antes = _estado(client_admin, demanda["id"])

    resposta = _rejeitar(cb, demanda, e2["id"])
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    por = _por_id(corpo)
    assert corpo["etapaAtualId"] == e1["id"]  # voltou para a imediatamente anterior
    # a aprovação rejeitada: pendente, sem início/conclusão/ator (será feita de novo)
    assert (por[e2["id"]]["status"], por[e2["id"]]["iniciadaEm"], por[e2["id"]]["concluidaEm"], por[e2["id"]]["concluidaPorUsuarioId"]) == ("pendente", None, None, None)
    # a anterior: reaberta (pendente, recomeça agora, conclusão e ator zerados)
    assert por[e1["id"]]["status"] == "pendente" and por[e1["id"]]["iniciadaEm"] is not None
    assert por[e1["id"]]["concluidaEm"] is None and por[e1["id"]]["concluidaPorUsuarioId"] is None
    assert por[e3["id"]]["status"] == "pendente" and por[e3["id"]]["iniciadaEm"] is None  # a seguinte não é tocada
    # a DEMANDA não muda
    for campo in ("status", "prioridade", "prazoEtapaAtual", "clienteId", "projetoId", "usuarioResponsavelIds", "departamentoResponsavelIds", "nome"):
        assert corpo[campo] == antes[campo], campo
    assert corpo["acessoApenasWorkflow"] is True  # b ainda recebe a resposta da ação (escopo derivado)


def test_evento_de_rejeicao_com_motivo_e_retorno_e_eventos_anteriores_preservados(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert _rejeitar(cb, demanda, e2["id"]).status_code == 200
    (evento,) = _eventos(db_session, demanda["id"], REJEITADA)
    assert evento.usuario_id == b.id
    p = evento.payload
    assert p["etapaId"] == e2["id"] and p["etapaNome"] == "Aprovação" and p["etapaOrdem"] == 2
    assert p["motivo"] == MOTIVO and p["atorUsuarioId"] == b.id
    assert p["etapaRetornoId"] == e1["id"] and p["etapaRetornoNome"] == "Criação" and p["etapaRetornoOrdem"] == 1
    assert "@" not in str(p)
    # append-only: a conclusão anterior continua lá
    assert len(_eventos(db_session, demanda["id"], "demanda.workflow_etapa_concluida")) == 1
    tipos = [h["tipo"] for h in client_admin.get(f"/demandas/{demanda['id']}/historico").json()]
    assert "demanda.workflow_etapa_concluida" in tipos and REJEITADA in tipos
    assert ATUALIZADA not in tipos  # o evento de notificação segue fora da timeline


def test_ciclo_completo_rejeita_refaz_e_aprova_com_historico_inteiro(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).json()["etapaAtualId"] == e2["id"]
    assert _rejeitar(cb, demanda, e2["id"]).json()["etapaAtualId"] == e1["id"]
    r = ca.post(_url(demanda["id"], e1["id"], "concluir"))  # refaz a Criação
    assert r.status_code == 200 and r.json()["etapaAtualId"] == e2["id"]
    por = _por_id(r.json())
    assert por[e1["id"]]["concluidaPorUsuarioId"] == a.id and por[e1["id"]]["concluidaEm"] is not None  # nova conclusão
    aprovada = cb.post(_url(demanda["id"], e2["id"], "aprovar"))
    assert aprovada.status_code == 200 and aprovada.json()["etapaAtualId"] == e3["id"]  # a 3 é a atual

    eventos = [h["tipo"] for h in reversed(client_admin.get(f"/demandas/{demanda['id']}/historico").json()) if h["tipo"].startswith("demanda.workflow_etapa_")]
    assert eventos == [
        "demanda.workflow_etapa_concluida",  # Criação
        "demanda.workflow_etapa_rejeitada",  # Aprovação rejeitada → Criação reaberta
        "demanda.workflow_etapa_concluida",  # Criação concluída novamente
        "demanda.workflow_etapa_aprovada",  # Aprovação
    ]


def test_rejeicoes_repetidas_preservam_todos_os_ciclos(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    for ciclo in range(3):
        assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
        assert _rejeitar(cb, demanda, e2["id"], f"Motivo do ciclo {ciclo + 1}").status_code == 200
        assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e1["id"]
    rejeicoes = _eventos(db_session, demanda["id"], REJEITADA)
    assert [e.payload["motivo"] for e in rejeicoes] == ["Motivo do ciclo 1", "Motivo do ciclo 2", "Motivo do ciclo 3"]
    assert len(_eventos(db_session, demanda["id"], "demanda.workflow_etapa_concluida")) == 3
    assert len(_eventos(db_session, demanda["id"], ATUALIZADA)) == 6  # 3 ativações da aprovação + 3 devoluções


# ======================================================================================
# motivo e contrato
# ======================================================================================


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"motivo": ""},
        {"motivo": "   "},
        {"motivo": "ab"},
        {"motivo": "x" * 1001},
        {"motivo": "<script>alert(1)</script>"},
        {"motivo": MOTIVO, "targetStepId": "qualquer"},
        {"motivo": MOTIVO, "previousStepId": "qualquer"},
        {"motivo": MOTIVO, "status": "pendente"},
        {"motivo": 123},
    ],
)
def test_motivo_obrigatorio_e_contrato_estrito_422_sem_efeito(app, db_session: Session, empresa: Empresa, client_admin: TestClient, corpo: dict) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    resposta = cb.post(_url(demanda["id"], e2["id"], "rejeitar"), json=corpo)
    assert resposta.status_code == 422, (corpo, resposta.status_code)
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e2["id"]  # nada mudou
    assert _eventos(db_session, demanda["id"], REJEITADA) == []


def test_motivo_e_normalizado_e_aceita_o_limite(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert _rejeitar(cb, demanda, e2["id"], "  Ajustar   o\n logotipo  ").status_code == 200
    assert _eventos(db_session, demanda["id"], REJEITADA)[0].payload["motivo"] == "Ajustar o logotipo"
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert _rejeitar(cb, demanda, e2["id"], "y" * 1000).status_code == 200  # no limite


# ======================================================================================
# regras de elegibilidade
# ======================================================================================


def test_execucao_futura_anterior_e_primeira_etapa_nao_rejeitam(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar já", "aprovacao"), _etapa("Executar"), _etapa("Aprovar depois", "aprovacao")])
    e1, e2, e3 = _por_ordem(demanda)
    primeira = _rejeitar(client_admin, demanda, e1["id"])  # atual, aprovação, mas SEM etapa anterior
    assert primeira.status_code == 409 and primeira.json()["detail"]["code"] == "SEM_ETAPA_ANTERIOR"
    assert client_admin.post(_url(demanda["id"], e1["id"], "aprovar")).status_code == 200  # agora a 2 (execução) é a atual
    assert _rejeitar(client_admin, demanda, e2["id"]).status_code == 422  # execução não rejeita
    assert _rejeitar(client_admin, demanda, e3["id"]).status_code == 409  # futura
    assert _rejeitar(client_admin, demanda, e1["id"]).status_code == 409  # anterior (concluída)
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e2["id"]
    assert _eventos(db_session, demanda["id"], REJEITADA) == []


def test_workflow_concluido_demanda_arquivada_e_pausada(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    concluido = _demanda_com_workflow(client_admin, [_etapa("A"), _etapa("Aprovar", "aprovacao")])
    c1, c2 = _por_ordem(concluido)
    assert client_admin.post(_url(concluido["id"], c1["id"], "concluir")).status_code == 200
    assert client_admin.post(_url(concluido["id"], c2["id"], "aprovar")).status_code == 200  # workflow concluído
    r = _rejeitar(client_admin, concluido, c2["id"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "WORKFLOW_CONCLUIDO"

    arquivada = _demanda_com_workflow(client_admin, [_etapa("A"), _etapa("Aprovar", "aprovacao")])
    a1, a2 = _por_ordem(arquivada)
    assert client_admin.post(_url(arquivada["id"], a1["id"], "concluir")).status_code == 200
    assert client_admin.post(f"/demandas/{arquivada['id']}/arquivar", json={"motivoArquivamento": "teste"}).status_code == 200
    r = _rejeitar(client_admin, arquivada, a2["id"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "DEMANDA_ARQUIVADA"

    pausada = _demanda_com_workflow(client_admin, [_etapa("A"), _etapa("Aprovar", "aprovacao")])
    p1, p2 = _por_ordem(pausada)
    assert client_admin.post(_url(pausada["id"], p1["id"], "concluir")).status_code == 200
    db_session.query(DemandaWorkflowEtapa).filter_by(id=p2["id"]).update({"status": "pausada"})
    db_session.commit()
    r = _rejeitar(client_admin, pausada, p2["id"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "ETAPA_PAUSADA"


def test_retry_da_rejeicao_409_sem_novo_efeito(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert _rejeitar(cb, demanda, e2["id"]).status_code == 200
    # retry de quem rejeitou: `b` perdeu o escopo derivado (a etapa 2 deixou de ser a atual) → 404, sem efeito nenhum
    assert _rejeitar(cb, demanda, e2["id"]).status_code == 404
    # retry/corrida de quem ainda tem acesso (autoridade total): 409 claro, sem voltar mais uma etapa
    segunda = _rejeitar(client_admin, demanda, e2["id"])
    assert segunda.status_code == 409 and segunda.json()["detail"]["code"] == "ETAPA_NAO_ATUAL"
    assert len(_eventos(db_session, demanda["id"], REJEITADA)) == 1
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e1["id"]  # não voltou duas etapas
    assert cb.post(_url(demanda["id"], e2["id"], "aprovar")).status_code == 404  # nem aprova a etapa que acabou de rejeitar


def test_aprovar_apos_rejeitar_com_autoridade_total_e_409(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert _rejeitar(cb, demanda, e2["id"]).status_code == 200
    r = client_admin.post(_url(demanda["id"], e2["id"], "aprovar"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "ETAPA_NAO_ATUAL"  # nunca aprova e rejeita ao mesmo tempo


# ======================================================================================
# autoridade e tenant
# ======================================================================================


def test_quem_pode_rejeitar_responsavel_head_gestor_admin(app, db_session: Session, empresa: Empresa, client_admin: TestClient, client_gestor: TestClient) -> None:
    head = _op(db_session, empresa, "head")
    dep = _departamento(db_session, empresa, nome="Aprovadores", responsavel_usuario_id=head.id)
    quatro = []
    for _ in range(4):
        d = _demanda_com_workflow(client_admin, [_etapa("Criar"), _etapa("Aprovar", "aprovacao", departamentos=[dep.id])])
        quatro.append(d)
    resp = _op(db_session, empresa, "resp")
    d_resp = _demanda_com_workflow(client_admin, [_etapa("Criar"), _etapa("Aprovar", "aprovacao", usuarios=[resp.id])])
    db_session.commit()
    for d, cliente in zip(quatro[:3] + [d_resp], (_client_para(app, head), client_gestor, client_admin, _client_para(app, resp))):
        e1, e2 = _por_ordem(d)
        assert client_admin.post(_url(d["id"], e1["id"], "concluir")).status_code == 200
        r = _rejeitar(cliente, d, e2["id"])
        assert r.status_code == 200, (cliente, r.text)
        assert r.json()["etapaAtualId"] == e1["id"]


def test_sem_autoridade_403_atendimento_e_alheio_cross_tenant_e_plataforma(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient, usuario_admin: Usuario) -> None:
    b = _op(db_session, empresa, "b")
    alheio, ana = _op(db_session, empresa, "alheio"), _op(db_session, empresa, "ana")
    _atendimento(db_session, empresa, ana)
    demanda = _demanda_com_workflow(
        client_admin, [_etapa("Criar"), _etapa("Aprovar", "aprovacao", usuarios=[b.id])], usuarioResponsavelIds=[alheio.id, ana.id]
    )  # alheio e Atendimento VEEM a demanda, mas não são responsáveis da etapa
    e1, e2 = _por_ordem(demanda)
    intruso = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="8d-intruso")
    db_session.commit()
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert _rejeitar(_client_para(app, alheio), demanda, e2["id"]).status_code == 403
    assert _rejeitar(_client_para(app, ana), demanda, e2["id"]).status_code == 403
    assert _rejeitar(_client_para(app, intruso), demanda, e2["id"]).status_code == 404  # cross-tenant: sem vazamento
    plataforma = TestClient(app)
    plataforma.headers["Authorization"] = "Bearer " + create_platform_token(sub=usuario_admin.id, administrador_id=str(uuid.uuid4()))
    assert _rejeitar(plataforma, demanda, e2["id"]).status_code in (401, 403)
    assert _estado(client_admin, demanda["id"])["etapaAtualId"] == e2["id"]
    assert _eventos(db_session, demanda["id"], REJEITADA) == []


# ======================================================================================
# notificação, Meu Dia e escopo derivado
# ======================================================================================


def test_devolucao_notifica_a_etapa_reaberta_e_acompanha_meu_dia_e_escopo(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    meu_dia = lambda c: [d["id"] for d in c.get("/demandas", params={"escopo": "meus", "limit": 200}).json()]  # noqa: E731
    assert demanda["id"] in meu_dia(ca) and demanda["id"] not in meu_dia(cb)  # etapa 1 é a atual: de `a`
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert demanda["id"] in meu_dia(cb) and demanda["id"] not in meu_dia(ca)  # a aprovação é de `b`
    assert ca.get(f"/demandas/{demanda['id']}").status_code == 404 and cb.get(f"/demandas/{demanda['id']}").status_code == 200

    assert _rejeitar(cb, demanda, e2["id"]).status_code == 200
    # `a` volta a ver e a abrir; `b` perde a atribuição atual (e o escopo derivado)
    assert demanda["id"] in meu_dia(ca) and demanda["id"] not in meu_dia(cb)
    assert ca.get(f"/demandas/{demanda['id']}").status_code == 200 and cb.get(f"/demandas/{demanda['id']}").status_code == 404
    devolvidas = [n for n in _central(ca) if n["tipo"] == ATUALIZADA and n["titulo"] == "Etapa devolvida para ajustes"]
    assert len(devolvidas) == 1
    n = devolvidas[0]
    assert n["detalhe"] == "Etapa 1: Criação" and n["demandaId"] == demanda["id"] and n["lida"] is False
    assert MOTIVO not in str(n)  # o motivo fica só no histórico
    assert not [x for x in _central(cb) if x["titulo"] == "Etapa devolvida para ajustes"]  # `b` não é notificado da devolução
    # refazer → `b` recebe a nova notificação de aprovação
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    aprovacoes = [x for x in _central(cb) if x["titulo"] == "Uma etapa de aprovação está aguardando você"]
    assert len(aprovacoes) == 2  # a primeira ativação e a de depois do retrabalho


def test_destinatarios_da_devolucao_sem_duplicata_e_so_ativos(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a1, a2, inativo = _op(db_session, empresa, "a1"), _op(db_session, empresa, "a2"), _op(db_session, empresa, "inat")
    dep = _departamento(db_session, empresa, nome="Criação", responsavel_usuario_id=a1.id)  # a1 também é Head do departamento da etapa
    b = _op(db_session, empresa, "b")
    demanda = _demanda_com_workflow(
        client_admin,
        [_etapa("Criar", usuarios=[a1.id, a2.id, inativo.id], departamentos=[dep.id]), _etapa("Aprovar", "aprovacao", usuarios=[b.id])],
    )
    inativo.status = "inativo"
    db_session.commit()
    e1, e2 = _por_ordem(demanda)
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert _rejeitar(_client_para(app, b), demanda, e2["id"]).status_code == 200
    ev = [e for e in _eventos(db_session, demanda["id"], ATUALIZADA) if e.payload.get("devolvida")]
    assert len(ev) == 1 and sorted(ev[0].payload["destinatarioUsuarioIds"]) == sorted([a1.id, a2.id])  # sem duplicata, sem inativo


# ======================================================================================
# read model
# ======================================================================================


def test_pode_rejeitar_calculado_no_servidor(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b, demanda, (e1, e2, e3), ca, cb = _cenario(app, db_session, empresa, client_admin)
    pode = lambda c: [e["podeRejeitar"] for e in sorted(_estado(c, demanda["id"])["workflowEtapas"], key=lambda x: x["ordem"])]  # noqa: E731
    assert pode(client_admin) == [False, False, False]  # etapa 1 é de execução e atual
    assert ca.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert pode(client_admin) == [False, True, False]  # só a aprovação ATUAL (com etapa anterior)
    assert pode(cb) == [False, True, False]
    alheio = _op(db_session, empresa, "alheio")
    d2 = _demanda_com_workflow(client_admin, [_etapa("X"), _etapa("Aprovar", "aprovacao")], usuarioResponsavelIds=[alheio.id])
    db_session.commit()
    assert client_admin.post(_url(d2["id"], _por_ordem(d2)[0]["id"], "concluir")).status_code == 200
    assert not any(e["podeRejeitar"] for e in _estado(_client_para(app, alheio), d2["id"])["workflowEtapas"])  # sem autoridade: nada
    pauta = client_admin.get(f"/demandas/{demanda['id']}", params={"escopo": "pauta"}).json()
    assert not any(e["podeRejeitar"] or e["podeAvancar"] for e in pauta["workflowEtapas"])  # leitura da Pauta: nenhuma ação
    # aprovação como PRIMEIRA etapa: sem etapa anterior → sem botão
    d3 = _demanda_com_workflow(client_admin, [_etapa("Aprovar já", "aprovacao"), _etapa("Depois")])
    assert not any(e["podeRejeitar"] for e in _estado(client_admin, d3["id"])["workflowEtapas"])


# ======================================================================================
# concorrência REAL (sessões separadas, locks do Postgres)
# ======================================================================================


@pytest.fixture()
def cenario_8d(test_engine):
    """Dados REAIS (commit): demanda com 1 Criação (concluída) → 2 Aprovação (atual, com responsável) → 3 Publicação. Reinicia o estado sob demanda."""
    Fabrica = sessionmaker(bind=test_engine)
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(timezone.utc)
    with Fabrica() as db:
        empresa = Empresa(id=str(uuid.uuid4()), nome="Empresa 8D", codigo_interno=f"D8-{sufixo}".upper(), status="ativa", created_at=agora, updated_at=agora)
        db.add(empresa)
        db.flush()

        def usuario(perfil: str, nome: str) -> Usuario:
            u = Usuario(
                id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"{nome}-{sufixo}", nome=nome, email=f"{nome}-{sufixo}@teste.taskfloww.local",
                perfil_base=perfil, acesso_sistema=True, status="ativo", created_at=agora, updated_at=agora,
            )
            db.add(u)
            db.flush()
            return u

        gestor, a, b = usuario("gestor", "gestor8d"), usuario("operador", "criador8d"), usuario("operador", "aprovador8d")
        demanda = Demanda(
            id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"T26{sufixo[:6]}", ano_referencia=26, sequencial_referencia=1,
            numero_operacional=1, identificador="#1", nome="Concorrência 8D", status="planejada", prioridade="media", sinalizada=False,
            created_at=agora, updated_at=agora,
        )
        db.add(demanda)
        db.flush()
        etapas = [
            DemandaWorkflowEtapa(
                id=str(uuid.uuid4()), demanda_id=demanda.id, ordem=i, nome=n, tipo=t, quantidade_antes_deadline=1, unidade_prazo="dias_corridos",
                status="concluida" if i == 1 else "pendente", iniciada_em=agora if i <= 2 else None, concluida_em=agora if i == 1 else None,
                concluida_por_usuario_id=gestor.id if i == 1 else None, created_at=agora, updated_at=agora,
            )
            for i, n, t in ((1, "Criação", "execucao"), (2, "Aprovação", "aprovacao"), (3, "Publicação", "execucao"))
        ]
        db.add_all(etapas)
        db.flush()
        db.add(DemandaWorkflowEtapaResponsavel(demanda_workflow_etapa_id=etapas[0].id, usuario_id=a.id, created_at=agora))
        db.add(DemandaWorkflowEtapaResponsavel(demanda_workflow_etapa_id=etapas[1].id, usuario_id=b.id, created_at=agora))
        db.commit()
        ids = {"empresa": empresa.id, "gestor": gestor.id, "a": a.id, "b": b.id, "demanda": demanda.id, "etapas": [e.id for e in etapas]}
    try:
        yield Fabrica, ids
    finally:
        with Fabrica() as db:
            db.query(Evento).filter(Evento.entidade_id == ids["demanda"]).delete()
            db.query(Demanda).filter(Demanda.id == ids["demanda"]).delete()
            db.query(Usuario).filter(Usuario.empresa_id == ids["empresa"]).delete()
            db.query(Empresa).filter(Empresa.id == ids["empresa"]).delete()
            db.commit()


def _disputar(Fabrica, ids, acoes: list[str]) -> list[str]:
    """Dispara uma thread por ação ("aprovar"/"rejeitar") sobre a etapa 2, todas ao mesmo tempo."""
    from app.services.demanda_workflow_service import DemandaWorkflowConflitoError, DemandaWorkflowService

    barreira = threading.Barrier(len(acoes))
    resultados: list[str] = []
    trava = threading.Lock()

    def tentar(acao: str) -> None:
        with Fabrica() as db:
            ator = db.get(Usuario, ids["gestor"])
            demanda = db.get(Demanda, ids["demanda"])
            servico = DemandaWorkflowService()
            barreira.wait(timeout=10)
            try:
                if acao == "rejeitar":
                    servico.rejeitar_etapa(db, demanda, etapa_id=ids["etapas"][1], motivo=MOTIVO, actor=ator)
                else:
                    servico.aprovar_etapa(db, demanda, etapa_id=ids["etapas"][1], actor=ator)
                saida = f"ok:{acao}"
            except DemandaWorkflowConflitoError:
                saida = "conflito"
            with trava:
                resultados.append(saida)

    threads = [threading.Thread(target=tentar, args=(a,)) for a in acoes]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return resultados


def _contar(Fabrica, demanda_id: str, tipo: str) -> int:
    with Fabrica() as db:
        return db.scalar(select(func.count()).select_from(Evento).where(Evento.entidade_id == demanda_id, Evento.tipo == tipo)) or 0


def test_concorrencia_aprovar_x_rejeitar_uma_vence_a_outra_conflita(cenario_8d) -> None:
    Fabrica, ids = cenario_8d
    resultados = _disputar(Fabrica, ids, ["aprovar", "rejeitar"])
    assert sorted(r.split(":")[0] for r in resultados) == ["conflito", "ok"], resultados
    aprovadas, rejeitadas = _contar(Fabrica, ids["demanda"], "demanda.workflow_etapa_aprovada"), _contar(Fabrica, ids["demanda"], REJEITADA)
    assert aprovadas + rejeitadas == 1  # nunca os dois
    with Fabrica() as db:
        etapas = {e.ordem: e for e in db.scalars(select(DemandaWorkflowEtapa).where(DemandaWorkflowEtapa.demanda_id == ids["demanda"])).all()}
        if rejeitadas:
            assert (etapas[1].status, etapas[2].status, etapas[3].status) == ("pendente", "pendente", "pendente") and etapas[1].concluida_em is None
        else:
            assert (etapas[1].status, etapas[2].status, etapas[3].status) == ("concluida", "concluida", "pendente")  # a 3 não foi pulada


def test_concorrencia_seis_rejeicoes_um_unico_efeito(cenario_8d) -> None:
    Fabrica, ids = cenario_8d
    resultados = _disputar(Fabrica, ids, ["rejeitar"] * 6)
    assert sorted(resultados) == ["conflito"] * 5 + ["ok:rejeitar"], resultados
    assert _contar(Fabrica, ids["demanda"], REJEITADA) == 1  # um evento
    with Fabrica() as db:
        notificacoes = list(db.scalars(select(Evento).where(Evento.entidade_id == ids["demanda"], Evento.tipo == ATUALIZADA)).all())
        assert len(notificacoes) == 1 and notificacoes[0].payload["devolvida"] is True  # um conjunto de notificações
        assert notificacoes[0].payload["destinatarioUsuarioIds"] == [ids["a"]]
        etapas = {e.ordem: e for e in db.scalars(select(DemandaWorkflowEtapa).where(DemandaWorkflowEtapa.demanda_id == ids["demanda"])).all()}
        assert etapas[1].status == "pendente" and etapas[2].status == "pendente"  # voltou UMA etapa, não duas
