"""11B.1 — contrato real HTTP, snapshot, autoridade, auditoria e totais."""
import uuid

import pytest
from sqlalchemy import select

from app.models.evento import Evento
from app.core.security import create_access_token
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_demanda_workflow import _criar_workflow_modelo, _criar_demanda, _etapa


def etapa(valor, **kwargs):
    return {**_etapa(**kwargs), "quantidadeAntesDeadline": 3, "unidadePrazo": "dias_uteis", "esforcoEstimadoMinutos": valor}


def criar(client, valores=(240, None, 0), **kwargs):
    modelo = _criar_workflow_modelo(client, etapas=[etapa(v, nome=f"Etapa {i}", **kwargs) for i, v in enumerate(valores)])
    demanda = _criar_demanda(client, workflowModeloId=modelo["id"]).json()
    return modelo, demanda


def url(demanda, indice=0):
    return f"/demandas/{demanda['id']}/workflow/etapas/{demanda['workflowEtapas'][indice]['id']}/esforco"


@pytest.mark.parametrize("valor", [None, 0, 30, 90, 240, 2147483647])
@pytest.mark.parametrize("tipo", ["execucao", "aprovacao"])
def test_template_e_snapshot_aceitam_valores(client_admin, valor, tipo):
    modelo = _criar_workflow_modelo(client_admin, etapas=[{**etapa(valor), "tipo": tipo}])
    assert modelo["etapas"][0]["esforcoEstimadoMinutos"] == valor
    demanda = _criar_demanda(client_admin, workflowModeloId=modelo["id"]).json()
    assert demanda["workflowEtapas"][0]["esforcoEstimadoMinutos"] == valor


@pytest.mark.parametrize("valor", [-1, 1.5, 1.0, "30", "inválido", True, 2147483648, 10**80])
def test_rejeita_contrato_invalido_no_template_e_ajuste(client_admin, valor):
    resposta = client_admin.post("/workflow-modelos", json={"nome": "Inválido", "etapas": [etapa(valor)]})
    assert resposta.status_code == 422
    modelo, demanda = criar(client_admin)
    assert client_admin.patch(f"/workflow-modelos/{modelo['id']}", json={"etapas": [etapa(valor)]}).status_code == 422
    assert client_admin.patch(url(demanda), json={"esforcoEstimadoMinutos": valor}).status_code == 422
    assert client_admin.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"][0]["esforcoEstimadoMinutos"] == 240


def test_snapshot_independente_nova_demanda_ajuste_e_auditoria(client_admin, db_session, usuario_admin):
    modelo, primeira = criar(client_admin)
    alterada = client_admin.patch(f"/workflow-modelos/{modelo['id']}", json={"etapas": [etapa(480), etapa(None), etapa(0)]})
    assert alterada.status_code == 200
    assert client_admin.get(f"/demandas/{primeira['id']}").json()["workflowEtapas"][0]["esforcoEstimadoMinutos"] == 240
    segunda = _criar_demanda(client_admin, workflowModeloId=modelo["id"]).json()
    assert segunda["workflowEtapas"][0]["esforcoEstimadoMinutos"] == 480
    resposta = client_admin.patch(url(primeira), json={"esforcoEstimadoMinutos": 120})
    assert resposta.status_code == 200, resposta.text
    atual = resposta.json()
    assert atual["workflowEtapas"][0] == {**primeira["workflowEtapas"][0], "esforcoEstimadoMinutos": 120}
    assert atual["workflowEtapas"][1:] == primeira["workflowEtapas"][1:]
    for campo in ("prazoEtapaAtual", "dataFimPrevista", "workflowModeloId", "etapaAtualId", "usuarioResponsavelIds", "status"):
        assert atual[campo] == primeira[campo]
    assert client_admin.get(f"/workflow-modelos/{modelo['id']}").json()["etapas"][0]["esforcoEstimadoMinutos"] == 480
    assert client_admin.get(f"/demandas/{segunda['id']}").json()["workflowEtapas"][0]["esforcoEstimadoMinutos"] == 480
    eventos = list(db_session.scalars(select(Evento).where(Evento.entidade_id == primeira["id"], Evento.tipo == "demanda.workflow_esforco_alterado")))
    assert len(eventos) == 1
    ev = eventos[0]
    assert ev.usuario_id == usuario_admin.id and ev.occurred_at is not None
    assert (ev.payload["valorAnteriorMinutos"], ev.payload["valorNovoMinutos"]) == (240, 120)
    historico = client_admin.get(f"/demandas/{primeira['id']}/historico").json()
    assert any(e["tipo"] == ev.tipo for e in historico)
    # Repetição não fabrica evento; null e zero são mudanças distintas.
    for valor in (120, None, 0):
        assert client_admin.patch(url(primeira), json={"esforcoEstimadoMinutos": valor}).status_code == 200
    assert len(list(db_session.scalars(select(Evento).where(Evento.entidade_id == primeira["id"], Evento.tipo == ev.tipo)))) == 3


def test_totais_e_cobertura_sem_duplicar_responsaveis(client_admin, usuario_admin, usuario_gestor):
    _, demanda = criar(client_admin, (240, None, 0, 120), responsavel_ids=[usuario_admin.id, usuario_gestor.id])
    assert (demanda["estimadoConhecidoMinutos"], demanda["etapasEstimadas"], demanda["etapasSemEstimativa"], demanda["estimativaCompleta"]) == (360, 3, 1, False)
    resposta = client_admin.patch(url(demanda, 1), json={"esforcoEstimadoMinutos": 0}).json()
    assert resposta["estimativaCompleta"] and resposta["estimadoConhecidoMinutos"] == 360
    assert client_admin.get(f"/demandas/{demanda['id']}").json()["estimadoConhecidoMinutos"] == 360
    _, desconhecida = criar(client_admin, (None,))
    assert desconhecida["estimadoConhecidoMinutos"] is None
    sem = _criar_demanda(client_admin).json()
    assert sem["workflowEtapas"] == [] and sem["estimadoConhecidoMinutos"] is None
    assert not sem["estimativaCompleta"] and sem["etapasEstimadas"] == sem["etapasSemEstimativa"] == 0


def test_autoridade_responsavel_e_gestor_sem_permissao_nova(client_admin, client_operador, client_gestor, usuario_operador):
    _, demanda = criar(client_admin, responsavel_ids=[usuario_operador.id])
    assert client_operador.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"][0]["podeEditarEsforco"]
    assert client_operador.patch(url(demanda), json={"esforcoEstimadoMinutos": 60}).status_code == 200
    assert client_gestor.patch(url(demanda, 1), json={"esforcoEstimadoMinutos": 90}).status_code == 200


def test_visibilidade_nao_concede_ajuste(client_admin, client_operador, usuario_operador):
    modelo, _ = criar(client_admin)
    demanda = _criar_demanda(client_admin, workflowModeloId=modelo["id"], usuarioResponsavelIds=[usuario_operador.id]).json()
    leitura = client_operador.get(f"/demandas/{demanda['id']}").json()
    assert not leitura["workflowEtapas"][0]["podeEditarEsforco"]
    assert client_operador.patch(url(demanda), json={"esforcoEstimadoMinutos": 60}).status_code == 403


def test_cross_tenant_e_etapa_de_outra_demanda(client_admin, app, db_session, outra_empresa):
    from fastapi.testclient import TestClient
    _, demanda = criar(client_admin)
    _, outra = criar(client_admin)
    caminho = f"/demandas/{demanda['id']}/workflow/etapas/{outra['workflowEtapas'][0]['id']}/esforco"
    assert client_admin.patch(caminho, json={"esforcoEstimadoMinutos": 1}).status_code == 404
    usuario = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="outro")
    cliente = TestClient(app)
    cliente.headers["Authorization"] = "Bearer " + create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base="admin")
    assert cliente.patch(url(demanda), json={"esforcoEstimadoMinutos": 1}).status_code == 404


def test_patch_exige_campo_e_recusa_estrutura(client_admin):
    _, demanda = criar(client_admin)
    for payload in ({}, {"esforcoEstimadoMinutos": 10, "ordem": 2}, {"esforcoEstimadoMinutos": 10, "tipo": "aprovacao"}):
        assert client_admin.patch(url(demanda), json=payload).status_code == 422


def test_evento_falha_reverte_estimativa(client_admin, monkeypatch):
    from app.api.routes.demandas import workflow_service
    _, demanda = criar(client_admin)
    def falhar(*args, **kwargs):
        raise RuntimeError("falha sintética de auditoria")
    monkeypatch.setattr(workflow_service.demanda_service, "publicar_evento_demanda", falhar)
    with pytest.raises(RuntimeError, match="auditoria"):
        client_admin.patch(url(demanda), json={"esforcoEstimadoMinutos": 120})
    assert client_admin.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"][0]["esforcoEstimadoMinutos"] == 240


def test_head_da_etapa_pode_head_de_outro_departamento_nao(app, db_session, empresa, client_admin):
    from tests.test_d1_criacao_demandas import _client_para, _operador_comum
    from tests.test_demanda import _departamento
    head = _operador_comum(db_session, empresa, sufixo="esforco-head")
    outro = _operador_comum(db_session, empresa, sufixo="esforco-outro")
    depto = _departamento(db_session, empresa, nome="Criação", responsavel_usuario_id=head.id)
    outro_depto = _departamento(db_session, empresa, nome="Social", responsavel_usuario_id=outro.id)
    modelo, _ = criar(client_admin, departamento_ids=[depto.id])
    demanda = _criar_demanda(client_admin, workflowModeloId=modelo["id"], departamentoResponsavelIds=[depto.id, outro_depto.id]).json()
    assert _client_para(app, outro).patch(url(demanda), json={"esforcoEstimadoMinutos": 10}).status_code == 403
    assert _client_para(app, head).patch(url(demanda), json={"esforcoEstimadoMinutos": 10}).status_code == 200


def test_plataforma_nao_edita_esforco(app, client_admin, usuario_admin):
    from app.core.security import create_platform_token
    from fastapi.testclient import TestClient
    _, demanda = criar(client_admin)
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer " + create_platform_token(sub=usuario_admin.id, administrador_id=str(uuid.uuid4()))
    assert client.patch(url(demanda), json={"esforcoEstimadoMinutos": 1}).status_code in (401, 403)


def test_arquivada_recusa_ajuste_e_prazo_independente(client_admin):
    _, demanda = criar(client_admin)
    resposta = client_admin.patch(f"/demandas/{demanda['id']}", json={"prazoEtapaAtual": "2026-11-20T12:00:00Z"})
    assert resposta.status_code == 200
    assert resposta.json()["workflowEtapas"][0]["esforcoEstimadoMinutos"] == 240
    ajustada = client_admin.patch(url(demanda), json={"esforcoEstimadoMinutos": 120}).json()
    assert ajustada["prazoEtapaAtual"] == resposta.json()["prazoEtapaAtual"]
    assert ajustada["workflowEtapas"][0]["quantidadeAntesDeadline"] == 3
    assert ajustada["workflowEtapas"][0]["unidadePrazo"] == "dias_uteis"
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "Teste"}).status_code == 200
    assert not client_admin.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"][0]["podeEditarEsforco"]
    assert client_admin.patch(url(demanda), json={"esforcoEstimadoMinutos": 30}).status_code == 409
