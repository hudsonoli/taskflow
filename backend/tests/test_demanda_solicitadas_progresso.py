"""Acompanhamento da solicitação: quem CRIOU uma Demanda continua LENDO-a durante todo o ciclo (escopo de autoria, só leitura), a visão "Solicitadas por mim"
(`GET /demandas?escopo=solicitadas`) e o progresso autoritativo do workflow (`progresso`, calculado no servidor).

Autoria concede acompanhamento, não gestão: editar, comentar, avançar etapa e mudar status continuam seguindo o escopo-base (que NÃO inclui autoria para quem não é Atendimento).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_permissao import UsuarioPermissao
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _atendimento, _client_para, _operador_comum
from tests.test_demanda import _departamento, dentro_do_expediente  # noqa: F401  (fixture)
from tests.test_fase_8a_workflow_progressao import _demanda_com_workflow, _estado, _etapa, _por_ordem, _url


@pytest.fixture(autouse=True)
def _expediente_aberto(dentro_do_expediente) -> None:  # noqa: F811
    """Mudanças de status respeitam o expediente — a janela é fixada para o teste não depender da hora."""


def _conceder(db: Session, usuario: Usuario, permissao: str) -> None:
    agora = datetime.now(timezone.utc)
    db.add(
        UsuarioPermissao(
            id=str(uuid.uuid4()), empresa_id=usuario.empresa_id, usuario_id=usuario.id, permissao=permissao, efeito="conceder", created_at=agora, updated_at=agora
        )
    )
    db.flush()


def _solicitadas(client: TestClient, empresa: Empresa, **params) -> list[dict]:
    resposta = client.get("/demandas", params={"escopo": "solicitadas", "limit": 200, **params})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _ids(itens: list[dict]) -> set[str]:
    return {item["id"] for item in itens}


@pytest.fixture()
def cenario(app, db_session: Session, empresa: Empresa, client_admin: TestClient):
    """Atendimento cria a Demanda; depois da 1ª etapa ela segue para Criação (designer): o criador deixa de ser responsável e de pertencer ao departamento atual."""
    atendimento = _operador_comum(db_session, empresa, sufixo="atend")
    _atendimento(db_session, empresa, atendimento)
    colega = _operador_comum(db_session, empresa, sufixo="colega")
    colega.departamento_id = atendimento.departamento_id
    criacao = _departamento(db_session, empresa, nome="Criação")
    designer = _operador_comum(db_session, empresa, sufixo="designer")
    designer.departamento_id = criacao.id
    db_session.flush()

    cliente_atendimento = _client_para(app, atendimento)
    demanda = _demanda_com_workflow(
        client_admin,
        [_etapa("Briefing", departamentos=[atendimento.departamento_id]), _etapa("Criação", usuarios=[designer.id], departamentos=[criacao.id]), _etapa("Revisão")],
        usuarioResponsavelIds=[designer.id],
        departamentoResponsavelIds=[criacao.id],
    )
    # autoria real: o POST é do Atendimento
    modelo_id = demanda["workflowModeloId"]
    criada = cliente_atendimento.post("/demandas", json={"nome": f"Solicitação {uuid.uuid4().hex[:6]}", "workflowModeloId": modelo_id})
    assert criada.status_code == 201, criada.text
    demanda = criada.json()
    assert demanda["criadoPorUsuarioId"] == atendimento.id
    # a Demanda segue para Criação: troca de responsáveis e conclusão da 1ª etapa (feitas pelo admin)
    assert client_admin.patch(
        f"/demandas/{demanda['id']}", json={"usuarioResponsavelIds": [designer.id], "departamentoResponsavelIds": [criacao.id]}
    ).status_code == 200
    primeira = _por_ordem(demanda)[0]
    assert client_admin.post(_url(demanda["id"], primeira["id"], "concluir")).status_code == 200
    return {"demanda": demanda, "atendimento": atendimento, "colega": colega, "designer": designer, "criacao": criacao}


def test_criador_continua_lendo_a_demanda_depois_do_handoff_e_so_em_modo_acompanhamento(
    app, db_session: Session, empresa: Empresa, client_admin: TestClient
) -> None:
    """Operador comum (com permissão explícita de criar) NÃO é Atendimento: o escopo-base não inclui autoria — só o novo escopo de leitura inclui."""
    criador = _operador_comum(db_session, empresa, sufixo="criador")
    _conceder(db_session, criador, "demandas.criar")
    designer = _operador_comum(db_session, empresa, sufixo="design")
    cliente = _client_para(app, criador)
    modelo = client_admin.post(
        "/workflow-modelos", json={"nome": f"WF {uuid.uuid4().hex[:6]}", "etapas": [_etapa("Briefing"), _etapa("Criação", usuarios=[designer.id])]}
    ).json()
    demanda = cliente.post("/demandas", json={"nome": "Pedido do criador", "workflowModeloId": modelo["id"]}).json()
    assert demanda["criadoPorUsuarioId"] == criador.id
    # handoff: o criador sai dos responsáveis
    assert client_admin.patch(f"/demandas/{demanda['id']}", json={"usuarioResponsavelIds": [designer.id]}).status_code == 200
    assert client_admin.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "concluir")).status_code == 200

    # ---- leitura: detalhe + subrecursos + visão "Solicitadas por mim"
    detalhe = cliente.get(f"/demandas/{demanda['id']}")
    assert detalhe.status_code == 200, detalhe.text
    corpo = detalhe.json()
    assert corpo["acessoSomenteAcompanhamento"] is True and corpo["acessoApenasWorkflow"] is False
    assert corpo["etapaAtualId"] is not None and len(corpo["workflowEtapas"]) == 2
    assert not any(e["podeAvancar"] or e["podeRejeitar"] or e["podeEditarEsforco"] or e["podeEditarPlanejamento"] for e in corpo["workflowEtapas"])
    for sub in ("historico", "comentarios", "checklist", "arquivos"):
        assert cliente.get(f"/demandas/{demanda['id']}/{sub}").status_code == 200, sub
    assert demanda["id"] in _ids(_solicitadas(cliente, empresa))

    # ---- NÃO é gestão: nenhuma escrita funciona (escopo-base não inclui autoria)
    assert cliente.patch(f"/demandas/{demanda['id']}", json={"nome": "Mudei"}).status_code in (403, 404)
    assert cliente.patch(f"/demandas/{demanda['id']}", json={"status": "pausada"}).status_code in (403, 404)
    assert cliente.post(f"/demandas/{demanda['id']}/comentarios", json={"texto": "oi"}).status_code in (403, 404)
    atual = _por_ordem(client_admin.get(f"/demandas/{demanda['id']}").json())[1]
    assert cliente.post(_url(demanda["id"], atual["id"], "concluir")).status_code in (403, 404)
    assert cliente.patch(f"/demandas/{demanda['id']}/workflow/etapas/{atual['id']}/esforco", json={"esforcoEstimadoMinutos": 30}).status_code in (403, 404)
    assert cliente.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code in (403, 404)
    assert client_admin.get(f"/demandas/{demanda['id']}").json()["nome"] == "Pedido do criador"

    # ---- sem a autoria o escopo-base (lista padrão, Meu Dia) continua sem a Demanda: as visões não se misturam
    assert demanda["id"] not in _ids(cliente.get("/demandas", params={"limit": 200}).json())
    assert demanda["id"] not in _ids(cliente.get("/demandas", params={"limit": 200, "escopo": "meus"}).json())


def test_atendimento_criador_ve_em_solicitadas_sem_perder_o_que_ja_tinha(cenario, app, client_admin: TestClient) -> None:
    demanda, atendimento = cenario["demanda"], cenario["atendimento"]
    cliente = _client_para(app, atendimento)
    assert cliente.get(f"/demandas/{demanda['id']}").status_code == 200
    assert demanda["id"] in _ids(_solicitadas(cliente, None))
    # Meu Dia (escopo=meus) = ação individual agora: o Atendimento que já passou a bola não vê a Demanda ali
    assert demanda["id"] not in _ids(cliente.get("/demandas", params={"escopo": "meus", "limit": 200}).json())


def test_escopo_acompanhamento_explicito_le_detalhe_e_subrecursos_so_para_o_criador(cenario, app) -> None:
    """A interface pede `?escopo=acompanhamento` (mesmo mecanismo da Pauta): só a AUTORIA vale, em modo leitura, mesmo para quem também teria acesso pelo escopo-base."""
    demanda, atendimento, colega = cenario["demanda"], cenario["atendimento"], cenario["colega"]
    criador = _client_para(app, atendimento)
    detalhe = criador.get(f"/demandas/{demanda['id']}", params={"escopo": "acompanhamento"})
    assert detalhe.status_code == 200, detalhe.text
    corpo = detalhe.json()
    assert corpo["acessoSomenteAcompanhamento"] is True
    assert not any(e["podeAvancar"] or e["podeRejeitar"] or e["podeEditarEsforco"] for e in corpo["workflowEtapas"])
    for sub in ("historico", "comentarios", "checklist", "arquivos"):
        assert criador.get(f"/demandas/{demanda['id']}/{sub}", params={"escopo": "acompanhamento"}).status_code == 200, sub
    # quem NÃO criou não ganha nada por pedir o escopo
    outro = _client_para(app, colega)
    assert outro.get(f"/demandas/{demanda['id']}", params={"escopo": "acompanhamento"}).status_code == 404
    assert outro.get(f"/demandas/{demanda['id']}/historico", params={"escopo": "acompanhamento"}).status_code == 404


def test_autoria_e_individual_colega_nao_herda(cenario, app) -> None:
    demanda, colega, designer = cenario["demanda"], cenario["colega"], cenario["designer"]
    cliente_colega = _client_para(app, colega)
    assert demanda["id"] not in _ids(_solicitadas(cliente_colega, None))
    assert cliente_colega.get(f"/demandas/{demanda['id']}").status_code == 404  # colega do mesmo departamento de origem não herda a autoria
    # quem executa não "solicitou": não aparece em Solicitadas por mim
    assert demanda["id"] not in _ids(_solicitadas(_client_para(app, designer), None))


def test_outra_empresa_nunca_atravessa(cenario, app, db_session: Session, outra_empresa: Empresa) -> None:
    demanda = cenario["demanda"]
    estranho = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="estranho")
    cliente = _client_para(app, estranho)
    assert cliente.get(f"/demandas/{demanda['id']}").status_code == 404
    assert demanda["id"] not in _ids(_solicitadas(cliente, None))


def test_gestor_nao_perde_escopo_e_nao_vira_somente_acompanhamento(cenario, client_gestor: TestClient) -> None:
    demanda = cenario["demanda"]
    corpo = client_gestor.get(f"/demandas/{demanda['id']}").json()
    assert corpo["acessoSomenteAcompanhamento"] is False
    # "Solicitadas por mim" do Gestor = o que ELE criou (nada), não a empresa inteira
    assert demanda["id"] not in _ids(_solicitadas(client_gestor, None))


def test_solicitadas_mostra_concluidas_e_oculta_arquivadas(cenario, app, client_admin: TestClient) -> None:
    demanda, atendimento = cenario["demanda"], cenario["atendimento"]
    cliente = _client_para(app, atendimento)
    assert client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "concluida"}).status_code == 200
    concluidas = _solicitadas(cliente, None, status="concluida")
    assert demanda["id"] in _ids(concluidas)  # a solicitação não some quando o job termina
    assert demanda["id"] in _ids(_solicitadas(cliente, None))  # e aparece sem filtro de status
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "limpeza"}).status_code == 200
    assert demanda["id"] not in _ids(_solicitadas(cliente, None))  # arquivadas seguem a semântica normal da listagem


def test_escopo_solicitadas_ignora_qualquer_usuario_enviado_pelo_cliente(cenario, app, db_session: Session, empresa: Empresa) -> None:
    demanda, atendimento = cenario["demanda"], cenario["atendimento"]
    outro = _operador_comum(db_session, empresa, sufixo="curioso")
    cliente = _client_para(app, outro)
    for extra in ({"criadoPorUsuarioId": atendimento.id}, {"criadorUsuarioId": atendimento.id}, {"usuarioId": atendimento.id}):
        assert demanda["id"] not in _ids(_solicitadas(cliente, None, **extra))


# --------------------------------------------------------------------------------------
# Progresso (autoritativo, derivado só do workflow)
# --------------------------------------------------------------------------------------


def _wf5(client: TestClient) -> dict:
    return _demanda_com_workflow(client, [_etapa(f"Etapa {i}") for i in range(1, 6)])


@pytest.mark.parametrize("concluir,esperado", [(0, 0), (2, 40), (4, 80), (5, 100)])
def test_progresso_e_etapas_concluidas_sobre_total(client_admin: TestClient, concluir: int, esperado: int) -> None:
    demanda = _wf5(client_admin)
    assert demanda["progresso"]["etapasTotal"] == 5 and demanda["progresso"]["percentual"] == 0
    for etapa in _por_ordem(demanda)[:concluir]:
        assert client_admin.post(_url(demanda["id"], etapa["id"], "concluir")).status_code == 200
    progresso = _estado(client_admin, demanda["id"])["progresso"]
    assert progresso["etapasConcluidas"] == concluir and progresso["percentual"] == esperado and progresso["semFluxo"] is False


def test_etapa_atual_em_execucao_nao_ganha_fracao(client_admin: TestClient, db_session: Session) -> None:
    demanda = _wf5(client_admin)
    etapas = _por_ordem(demanda)
    for etapa in etapas[:2]:
        client_admin.post(_url(demanda["id"], etapa["id"], "concluir"))
    db_session.execute(text("UPDATE demanda_workflow_etapas SET status='em_execucao' WHERE id=:e"), {"e": etapas[2]["id"]})
    db_session.flush()
    progresso = _estado(client_admin, demanda["id"])["progresso"]
    assert progresso["percentual"] == 40 and progresso["etapaAtualNome"] == "Etapa 3" and progresso["etapaAtualId"] == etapas[2]["id"]


def test_progresso_arredonda_para_o_inteiro_mais_proximo(client_admin: TestClient) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa(f"E{i}") for i in range(1, 4)])
    client_admin.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "concluir"))
    assert _estado(client_admin, demanda["id"])["progresso"]["percentual"] == 33


def test_sem_workflow_e_sem_fluxo_e_nao_zero_por_cento(client_admin: TestClient) -> None:
    resposta = client_admin.post("/demandas", json={"nome": "Sem fluxo"})
    progresso = resposta.json()["progresso"]
    assert progresso["semFluxo"] is True and progresso["percentual"] is None and progresso["etapasTotal"] == 0 and progresso["etapaAtualNome"] is None


def test_cancelada_nao_vira_cem_por_cento(client_admin: TestClient) -> None:
    demanda = _wf5(client_admin)
    client_admin.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "concluir"))
    assert client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "cancelada"}).status_code == 200
    estado = _estado(client_admin, demanda["id"])
    assert estado["status"] == "cancelada" and estado["progresso"]["percentual"] == 20  # histórico preservado; o rótulo "Cancelada" é da interface


def test_demanda_concluida_e_cem_por_cento(client_admin: TestClient) -> None:
    demanda = _wf5(client_admin)
    assert client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "concluida"}).status_code == 200
    assert _estado(client_admin, demanda["id"])["progresso"]["percentual"] == 100


def test_etapa_rejeitada_volta_a_nao_contar(client_admin: TestClient) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criar"), _etapa("Aprovar", "aprovacao"), _etapa("Publicar")])
    etapas = _por_ordem(demanda)
    client_admin.post(_url(demanda["id"], etapas[0]["id"], "concluir"))
    assert _estado(client_admin, demanda["id"])["progresso"]["percentual"] == 33
    rejeicao = client_admin.post(_url(demanda["id"], etapas[1]["id"], "rejeitar"), json={"motivo": "refazer"})
    assert rejeicao.status_code == 200, rejeicao.text
    progresso = _estado(client_admin, demanda["id"])["progresso"]
    assert progresso["etapasConcluidas"] == 0 and progresso["percentual"] == 0  # a etapa devolvida deixou de estar concluída


def test_listagem_traz_o_progresso_sem_consulta_extra_por_item(client_admin: TestClient, db_session: Session) -> None:
    from sqlalchemy import event

    for _ in range(3):
        _wf5(client_admin)
    comandos: list[str] = []

    def capturar(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", capturar)
    try:
        itens = client_admin.get("/demandas", params={"limit": 200}).json()
    finally:
        event.remove(engine, "before_cursor_execute", capturar)
    base = len(comandos)
    assert all("progresso" in item for item in itens)

    for _ in range(6):
        _wf5(client_admin)
    comandos.clear()
    event.listen(engine, "before_cursor_execute", capturar)
    try:
        client_admin.get("/demandas", params={"limit": 200})
    finally:
        event.remove(engine, "before_cursor_execute", capturar)
    assert len(comandos) == base  # custo constante: o progresso sai dos dados que a listagem já carrega
