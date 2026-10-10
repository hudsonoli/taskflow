"""Fase 8C.1 — escopo OPERACIONAL da etapa atual: quem é responsável pela ETAPA ATUAL (ou Head do departamento dela) abre a Demanda, lê o
necessário e age no Workflow, SEM virar `DemandaResponsavel` e SEM receber edição geral. O acesso é DERIVADO do snapshot em tempo real
(`resolver_escopo_workflow_atual`): some quando a etapa deixa de ser a atual; etapa futura/concluída, workflow concluído ou sem etapas não concedem nada.

Meu Dia (`escopo=meus`) também passa a incluir a Demanda cuja etapa atual está atribuída AO USUÁRIO individualmente — nunca por liderança nem por autoridade.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _atendimento, _client_para, _operador_comum
from tests.test_demanda import _departamento
from tests.test_fase_8a_workflow_progressao import _demanda_com_workflow, _etapa, _por_ordem, _url
from tests.test_gerenciador_arquivos import PDF_VALIDO, _upload

TIPO_NOTIFICACAO = "demanda.workflow_etapa_atualizada"


def _op(db: Session, empresa: Empresa, nome: str) -> Usuario:
    return _operador_comum(db, empresa, sufixo=f"81-{nome}-{uuid.uuid4().hex[:4]}")


def _meu_dia(client: TestClient, **extra) -> list[dict]:
    resposta = client.get("/demandas", params={"escopo": "meus", "limit": 200, **extra})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _ids(itens: list[dict]) -> list[str]:
    return [i["id"] for i in itens]


def _tres_etapas(client_admin: TestClient, a: Usuario, **extra) -> dict:
    """1 Criação (sem responsável) → 2 Aprovação (a) → 3 Publicação (sem responsável). `a` NÃO é responsável da demanda."""
    return _demanda_com_workflow(client_admin, [_etapa("Criação"), _etapa("Aprovação", "aprovacao", usuarios=[a.id]), _etapa("Publicação")], **extra)


def _leituras(demanda_id: str, arquivo_id: str) -> dict[str, str]:
    return {
        "detalhe": f"/demandas/{demanda_id}",
        "comentarios": f"/demandas/{demanda_id}/comentarios",
        "historico": f"/demandas/{demanda_id}/historico",
        "checklist": f"/demandas/{demanda_id}/checklist",
        "arquivos": f"/demandas/{demanda_id}/arquivos",
        "download": f"/demandas/{demanda_id}/arquivos/{arquivo_id}/download",
    }


def _com_arquivo(client_admin: TestClient, demanda_id: str) -> str:
    resposta = _upload(client_admin, demanda_id, nome="briefing.pdf", conteudo=PDF_VALIDO + uuid.uuid4().hex.encode())
    assert resposta.status_code == 201, resposta.text
    assert client_admin.post(f"/demandas/{demanda_id}/comentarios", json={"texto": "Contexto do trabalho"}).status_code == 201
    assert client_admin.post(f"/demandas/{demanda_id}/checklist", json={"texto": "Revisar"}).status_code == 201
    return resposta.json()["id"]


# ======================================================================================
# responsável da ETAPA ATUAL
# ======================================================================================


def test_responsavel_da_etapa_atual_abre_le_e_age_sem_ser_responsavel_da_demanda(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _tres_etapas(client_admin, a)
    arquivo_id = _com_arquivo(client_admin, demanda["id"])
    e1, e2, e3 = _por_ordem(demanda)
    db_session.commit()
    ca = _client_para(app, a)

    # etapa 1 é a atual: `a` ainda não tem nada
    for nome, url in _leituras(demanda["id"], arquivo_id).items():
        assert ca.get(url).status_code == 404, nome
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200  # a etapa 2 (de `a`) passa a ser a atual

    # leitura necessária liberada: detalhe, workflow, comentários, histórico, checklist, arquivos e download
    for nome, url in _leituras(demanda["id"], arquivo_id).items():
        resposta = ca.get(url)
        assert resposta.status_code == 200, f"{nome}: {resposta.status_code} {resposta.text[:100]}"
    detalhe = ca.get(f"/demandas/{demanda['id']}").json()
    assert detalhe["acessoApenasWorkflow"] is True  # acesso só pelo Workflow (sem edição geral)
    assert detalhe["etapaAtualId"] == e2["id"]
    assert [e["podeAvancar"] for e in sorted(detalhe["workflowEtapas"], key=lambda e: e["ordem"])] == [False, True, False]
    assert ca.get(_leituras(demanda["id"], arquivo_id)["download"]).content.startswith(b"%PDF-")

    # a ação do Workflow funciona
    resposta = ca.post(_url(demanda["id"], e2["id"], "aprovar"))
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["etapaAtualId"] == e3["id"]
    assert resposta.json()["acessoApenasWorkflow"] is True  # a própria resposta da ação ainda carrega o acesso derivado
    # NADA persistido: não virou DemandaResponsavel
    assert db_session.scalar(select(func.count()).select_from(DemandaResponsavel).where(DemandaResponsavel.usuario_id == a.id)) == 0


def test_o_acesso_some_quando_a_etapa_deixa_de_ser_a_atual(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _tres_etapas(client_admin, a)
    e1, e2, e3 = _por_ordem(demanda)
    db_session.commit()
    ca = _client_para(app, a)
    assert ca.get(f"/demandas/{demanda['id']}").status_code == 404  # etapa FUTURA: sem acesso
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert ca.get(f"/demandas/{demanda['id']}").status_code == 200  # virou a atual: acesso automático
    assert ca.post(_url(demanda["id"], e2["id"], "aprovar")).status_code == 200
    assert ca.get(f"/demandas/{demanda['id']}").status_code == 404  # etapa CONCLUÍDA: o acesso especial acabou (e nada foi persistido)
    assert ca.post(_url(demanda["id"], e2["id"], "aprovar")).status_code == 404  # nem a ação (404, sem confirmar existência)


def test_workflow_concluido_e_sem_etapas_nao_concedem_acesso(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    unica = _demanda_com_workflow(client_admin, [_etapa("Única", usuarios=[a.id])])
    sem_etapas = client_admin.post("/demandas", json={"nome": "Sem workflow"}).json()
    db_session.commit()
    ca = _client_para(app, a)
    assert ca.get(f"/demandas/{unica['id']}").status_code == 200
    assert client_admin.post(_url(unica["id"], _por_ordem(unica)[0]["id"], "concluir")).status_code == 200  # workflow concluído
    assert ca.get(f"/demandas/{unica['id']}").status_code == 404
    assert ca.get(f"/demandas/{sem_etapas['id']}").status_code == 404  # sem etapas: nada, e sem 500
    db_session.query(DemandaWorkflowEtapa).filter_by(demanda_id=unica["id"]).delete()
    db_session.commit()
    assert ca.get(f"/demandas/{unica['id']}").status_code == 404


def test_o_escopo_de_workflow_nao_concede_escrita_geral(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id])])
    arquivo_id = _com_arquivo(client_admin, demanda["id"])
    db_session.commit()
    ca = _client_para(app, a)
    assert ca.get(f"/demandas/{demanda['id']}").status_code == 200  # tem a leitura...
    # ...mas nenhuma escrita geral: tudo continua no escopo-base (404 sem confirmar existência)
    assert ca.patch(f"/demandas/{demanda['id']}", json={"nome": "Alterado", "prioridade": "alta"}).status_code == 404
    assert ca.patch(f"/demandas/{demanda['id']}", json={"usuarioResponsavelIds": [a.id]}).status_code == 404
    assert ca.post(f"/demandas/{demanda['id']}/comentarios", json={"texto": "oi"}).status_code == 404
    assert ca.post(f"/demandas/{demanda['id']}/checklist", json={"texto": "x"}).status_code == 404
    assert _upload(ca, demanda["id"], nome="novo.pdf").status_code == 404
    assert ca.delete(f"/demandas/{demanda['id']}/arquivos/{arquivo_id}").status_code == 404
    assert ca.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code in (403, 404)
    assert ca.post(f"/demandas/{demanda['id']}/ajustes", json={"tipo": "ajuste_interno"}).status_code == 404
    # nada mudou
    assert client_admin.get(f"/demandas/{demanda['id']}").json()["nome"] == demanda["nome"]


def test_acesso_a_uma_demanda_nao_vaza_para_outra(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    d1 = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id])])
    d2 = _demanda_com_workflow(client_admin, [_etapa("Outra", usuarios=[])])
    arquivo_d2 = _com_arquivo(client_admin, d2["id"])
    db_session.commit()
    ca = _client_para(app, a)
    assert ca.get(f"/demandas/{d1['id']}").status_code == 200
    assert ca.get(f"/demandas/{d2['id']}").status_code == 404
    assert ca.get(_leituras(d2["id"], arquivo_d2)["download"]).status_code == 404
    assert ca.get(f"/demandas/{d1['id']}/arquivos/{arquivo_d2}/download").status_code == 404  # arquivo de outra demanda pela demanda liberada


def test_pauta_continua_com_regra_propria_e_sem_podeavancar(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id])])
    db_session.commit()
    ca = _client_para(app, a)
    assert ca.get(f"/demandas/{demanda['id']}", params={"escopo": "pauta"}).status_code == 403  # operador não tem Pauta global (não se mistura)
    pauta = client_admin.get(f"/demandas/{demanda['id']}", params={"escopo": "pauta"}).json()
    assert not any(e["podeAvancar"] for e in pauta["workflowEtapas"])  # Pauta: leitura, sem ação


# ======================================================================================
# Head, Atendimento, admin/gestor, plataforma, tenant, pausada
# ======================================================================================


def test_head_do_departamento_da_etapa_atual_abre_e_age_e_head_de_outro_nao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    head, outro = _op(db_session, empresa, "head"), _op(db_session, empresa, "outro")
    criacao = _departamento(db_session, empresa, nome="Criação", responsavel_usuario_id=head.id)
    social = _departamento(db_session, empresa, nome="Social", responsavel_usuario_id=outro.id)
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criar"), _etapa("No departamento", departamentos=[criacao.id]), _etapa("Fim")])
    e1, e2, e3 = _por_ordem(demanda)
    db_session.commit()
    ch, co = _client_para(app, head), _client_para(app, outro)
    assert ch.get(f"/demandas/{demanda['id']}").status_code == 404  # etapa 1 ainda é a atual
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert ch.get(f"/demandas/{demanda['id']}").status_code == 200
    assert co.get(f"/demandas/{demanda['id']}").status_code == 404  # Head de OUTRO departamento
    assert co.post(_url(demanda["id"], e2["id"], "concluir")).status_code == 404
    assert [e["podeAvancar"] for e in sorted(ch.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"], key=lambda e: e["ordem"])] == [False, True, False]
    assert ch.post(_url(demanda["id"], e2["id"], "concluir")).status_code == 200
    assert ch.get(f"/demandas/{demanda['id']}").status_code == 404  # a etapa avançou


def test_atendimento_sem_relacao_nao_ganha_acesso(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    ana = _op(db_session, empresa, "ana")
    _atendimento(db_session, empresa, ana)
    resp = _op(db_session, empresa, "resp")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[resp.id])])
    db_session.commit()
    ca = _client_para(app, ana)
    assert ca.get(f"/demandas/{demanda['id']}").status_code == 404
    assert ca.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "aprovar")).status_code == 404


def test_admin_e_gestor_preservados_com_escopo_base(client_admin: TestClient, client_gestor: TestClient, db_session: Session, empresa: Empresa) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id])])
    db_session.commit()
    for cliente in (client_admin, client_gestor):
        detalhe = cliente.get(f"/demandas/{demanda['id']}")
        assert detalhe.status_code == 200
        assert detalhe.json()["acessoApenasWorkflow"] is False  # veio do escopo-base, com edição geral


def test_cross_tenant_inconsistente_nao_concede_acesso(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient) -> None:
    de_fora = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="81-fora")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao")])
    # relacionamento inconsistente de propósito: um usuário de OUTRA empresa gravado como responsável da etapa atual
    db_session.add(
        DemandaWorkflowEtapaResponsavel(
            demanda_workflow_etapa_id=_por_ordem(demanda)[0]["id"], usuario_id=de_fora.id, created_at=datetime.now(timezone.utc)
        )
    )
    db_session.commit()
    cf = _client_para(app, de_fora)
    assert cf.get(f"/demandas/{demanda['id']}").status_code == 404
    assert cf.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "aprovar")).status_code == 404
    assert _meu_dia(cf) == []


def test_etapa_atual_pausada_le_mas_nao_avanca(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id]), _etapa("Depois")])
    e1 = _por_ordem(demanda)[0]
    db_session.query(DemandaWorkflowEtapa).filter_by(id=e1["id"]).update({"status": "pausada"})
    db_session.commit()
    ca = _client_para(app, a)
    detalhe = ca.get(f"/demandas/{demanda['id']}")
    assert detalhe.status_code == 200  # continua sendo a etapa operacional atual
    assert not any(e["podeAvancar"] for e in detalhe.json()["workflowEtapas"])
    resposta = ca.post(_url(demanda["id"], e1["id"], "aprovar"))
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "ETAPA_PAUSADA"


def test_sem_autoridade_na_etapa_continua_403_mesmo_com_acesso_de_workflow(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    """Acesso derivado ≠ autoridade: quem só tem a leitura pelo Workflow (ex.: Head não responsável) não age em etapa de outro."""
    a, b = _op(db_session, empresa, "a"), _op(db_session, empresa, "b")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id])], usuarioResponsavelIds=[b.id])
    db_session.commit()
    cb = _client_para(app, b)  # `b` vê a demanda pelo escopo-base, mas não é responsável da etapa
    assert cb.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "aprovar")).status_code == 403
    ca = _client_para(app, a)
    assert ca.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "aprovar")).status_code == 200


# ======================================================================================
# notificação acionável (fecha o ciclo da 8C)
# ======================================================================================


def test_notificacao_da_etapa_leva_a_demanda_e_a_acao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _tres_etapas(client_admin, a)
    e1, e2, _ = _por_ordem(demanda)
    db_session.commit()
    ca = _client_para(app, a)
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    (notificacao,) = [n for n in ca.get("/notificacoes", params={"limit": 50}).json()["itens"] if n["tipo"] == TIPO_NOTIFICACAO]
    assert notificacao["demandaId"] == demanda["id"]
    detalhe = ca.get(f"/demandas/{notificacao['demandaId']}")  # o clique: antes da 8C.1 era 404
    assert detalhe.status_code == 200
    assert ca.get(f"/demandas/{demanda['id']}/historico").status_code == 200
    assert ca.post(_url(demanda["id"], e2["id"], "aprovar")).status_code == 200  # e a ação executa


# ======================================================================================
# Meu Dia (escopo=meus)
# ======================================================================================


def test_meu_dia_inclui_a_demanda_da_etapa_atual_e_nao_a_futura_nem_a_concluida(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _tres_etapas(client_admin, a)
    e1, e2, e3 = _por_ordem(demanda)
    db_session.commit()
    ca = _client_para(app, a)
    assert demanda["id"] not in _ids(_meu_dia(ca))  # etapa 2 é FUTURA
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    meus = _meu_dia(ca)
    assert _ids(meus).count(demanda["id"]) == 1  # a etapa 2 é a atual: entra (sem ser DemandaResponsavel)
    assert ca.post(_url(demanda["id"], e2["id"], "aprovar")).status_code == 200
    assert demanda["id"] not in _ids(_meu_dia(ca))  # etapa CONCLUÍDA: responsabilidade histórica não conta


def test_meu_dia_nao_inclui_head_por_lideranca_nem_gestor_por_autoridade(app, db_session: Session, empresa: Empresa, client_admin: TestClient, client_gestor: TestClient) -> None:
    head = _op(db_session, empresa, "head")
    dep = _departamento(db_session, empresa, nome="Criação", responsavel_usuario_id=head.id)
    demanda = _demanda_com_workflow(client_admin, [_etapa("No departamento", departamentos=[dep.id])])
    db_session.commit()
    ch = _client_para(app, head)
    assert ch.get(f"/demandas/{demanda['id']}").status_code == 200  # Head abre...
    assert demanda["id"] not in _ids(_meu_dia(ch))  # ...mas NÃO vê no Meu Dia só por liderar
    assert demanda["id"] not in _ids(_meu_dia(client_gestor)) and demanda["id"] not in _ids(_meu_dia(client_admin))  # nem gestor/admin por autoridade


def test_meu_dia_sem_duplicar_quando_tambem_e_responsavel_da_demanda(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id])], usuarioResponsavelIds=[a.id])
    db_session.commit()
    ids = _ids(_meu_dia(_client_para(app, a)))
    assert ids.count(demanda["id"]) == 1


def test_resumo_do_meu_dia_inclui_a_etapa_atual(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id])])
    db_session.commit()
    agora = datetime.now(timezone.utc)
    params = {
        "agora": agora.isoformat(), "hojeInicio": agora.replace(hour=0, minute=0).isoformat(), "hojeFim": agora.replace(hour=23, minute=59).isoformat(),
        "semanaInicio": agora.replace(hour=0, minute=0).isoformat(), "semanaFim": agora.replace(hour=23, minute=59).isoformat(),
        "ontemInicio": agora.replace(hour=0, minute=0).isoformat(), "ontemFim": agora.replace(hour=23, minute=59).isoformat(),
    }
    resumo = _client_para(app, a).get("/demandas/minha-home/resumo", params=params)
    assert resumo.status_code == 200, resumo.text
    assert resumo.json()["ativas"] == 1


def test_meu_dia_sem_n_mais_um(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    for _ in range(2):
        _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id])])
    db_session.commit()
    ca = _client_para(app, a)
    contagem = {"n": 0}

    def contar(conn, cursor, statement, parameters, context, executemany):
        contagem["n"] += 1

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", contar)
    try:
        assert len(_meu_dia(ca)) == 2  # aquece (resolução do usuário/permissões) antes de medir
        contagem["n"] = 0
        assert len(_meu_dia(ca)) == 2
        pequena = contagem["n"]
        for _ in range(8):
            _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[a.id])])
        db_session.commit()
        assert len(_meu_dia(ca)) == 10  # aquece de novo após o commit (objetos expirados)
        contagem["n"] = 0
        assert len(_meu_dia(ca)) == 10
        grande = contagem["n"]
    finally:
        event.remove(engine, "before_cursor_execute", contar)
    assert grande == pequena  # a regra é UM EXISTS no SQL, não uma consulta por demanda
