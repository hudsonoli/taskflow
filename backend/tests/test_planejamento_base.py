"""11B.2B-A — janela planejada por etapa (PATCH parcial, estados derivados, CHECK, auditoria, efeitos colaterais) e percentual de capacidade alocável.

Prazo ≠ planejamento: nada aqui toca `prazo_etapa_atual`, `data_inicio`/`data_fim_prevista`, status, sessões nem intervalos operacionais.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.planejamento_etapa import (
    ESTADO_INCOMPLETO,
    ESTADO_NAO_PLANEJADO,
    ESTADO_PLANEJADO,
    JanelaPlanejadaInvalidaError,
    estado_da_janela,
    validar_janela,
)
from app.core.security import create_access_token
from app.models.demanda import Demanda
from app.models.demanda_status_intervalo import DemandaStatusIntervalo
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.evento import Evento
from app.models.regra_expediente import RegraExpediente as RegraModel
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.workflow_modelo_etapa import WorkflowModeloEtapa
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_demanda_workflow import _criar_demanda, _criar_workflow_modelo, _etapa
from tests.test_expediente_fase2_api import _configurar

TIPO_EVENTO = "demanda.workflow_planejamento_alterado"
VAZIO = {"planejadoInicio": None, "planejadoFim": None, "estado": ESTADO_NAO_PLANEJADO}


def _etapa_modelo(nome: str = "Etapa", **kwargs) -> dict:
    return {**_etapa(nome=nome, **kwargs), "quantidadeAntesDeadline": 3, "unidadePrazo": "dias_uteis", "esforcoEstimadoMinutos": 240}


def criar(client, quantidade: int = 2, **kwargs):
    modelo = _criar_workflow_modelo(client, etapas=[_etapa_modelo(f"Etapa {i}", **kwargs) for i in range(quantidade)])
    demanda = _criar_demanda(client, workflowModeloId=modelo["id"]).json()
    return modelo, demanda


def url(demanda: dict, indice: int = 0) -> str:
    return f"/demandas/{demanda['id']}/workflow/etapas/{demanda['workflowEtapas'][indice]['id']}/planejamento"


def planejamento(client, demanda: dict, indice: int = 0) -> dict:
    return client.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"][indice]["planejamento"]


def eventos(db, demanda_id: str) -> list[Evento]:
    db.expire_all()
    return list(db.scalars(select(Evento).where(Evento.entidade_id == demanda_id, Evento.tipo == TIPO_EVENTO).order_by(Evento.created_at)))


# ── regra pura ───────────────────────────────────────────────────────────────────────────────────────────────────


D1, D2, D3 = date(2026, 10, 20), date(2026, 10, 25), date(2026, 10, 30)


@pytest.mark.parametrize(
    ("inicio", "fim", "estado"),
    [
        (None, None, ESTADO_NAO_PLANEJADO),
        (D1, None, ESTADO_INCOMPLETO),
        (D1, D1, ESTADO_PLANEJADO),
        (D1, D3, ESTADO_PLANEJADO),
    ],
)
def test_estado_derivado_do_par(inicio, fim, estado) -> None:
    validar_janela(inicio, fim)
    assert estado_da_janela(inicio, fim) == estado


@pytest.mark.parametrize(("inicio", "fim"), [(None, D3), (D3, D1), (D2, D1)])
def test_pares_invalidos_nao_tem_estado(inicio, fim) -> None:
    with pytest.raises(JanelaPlanejadaInvalidaError):
        validar_janela(inicio, fim)
    with pytest.raises(JanelaPlanejadaInvalidaError):
        estado_da_janela(inicio, fim)


# ── CHECK no banco ───────────────────────────────────────────────────────────────────────────────────────────────


def _gravar(db, etapa_id: str, inicio, fim) -> None:
    db.execute(
        text("UPDATE demanda_workflow_etapas SET planejado_inicio = :i, planejado_fim = :f WHERE id = :id"),
        {"i": inicio, "f": fim, "id": etapa_id},
    )
    db.flush()


@pytest.mark.parametrize(("inicio", "fim"), [(None, None), (D1, None), (D1, D1), (D1, D3)])
def test_banco_aceita_os_estados_validos(client_admin, db_session, inicio, fim) -> None:
    _, demanda = criar(client_admin, 1)
    _gravar(db_session, demanda["workflowEtapas"][0]["id"], inicio, fim)
    db_session.rollback()


@pytest.mark.parametrize(("inicio", "fim"), [(None, D3), (D3, D1)])
def test_banco_recusa_fim_sem_inicio_e_fim_anterior(client_admin, db_session, inicio, fim) -> None:
    _, demanda = criar(client_admin, 1)
    etapa_id = demanda["workflowEtapas"][0]["id"]
    with pytest.raises(IntegrityError, match="ck_demanda_workflow_etapas_janela_planejada"):
        _gravar(db_session, etapa_id, inicio, fim)
    db_session.rollback()


# ── leitura e estados pela API ───────────────────────────────────────────────────────────────────────────────────


def test_etapa_nova_nasce_nao_planejada_sem_backfill_de_prazo_ou_periodo(client_admin) -> None:
    _, demanda = criar(client_admin)
    assert all(etapa["planejamento"] == VAZIO for etapa in demanda["workflowEtapas"])
    assert all(etapa["podeEditarPlanejamento"] for etapa in demanda["workflowEtapas"])
    # o planejamento nunca nasce do prazo, do período da Demanda nem da etapa atual
    assert client_admin.patch(f"/demandas/{demanda['id']}", json={"prazoEtapaAtual": "2026-11-20T12:00:00Z", "dataInicio": "2026-11-01", "dataFimPrevista": "2026-11-20"}).status_code == 200
    assert all(etapa["planejamento"] == VAZIO for etapa in client_admin.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"])


def test_estados_incompleto_e_planejado_pela_api(client_admin) -> None:
    _, demanda = criar(client_admin)
    resposta = client_admin.patch(url(demanda), json={"planejadoInicio": "2026-10-20"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["workflowEtapas"][0]["planejamento"] == {"planejadoInicio": "2026-10-20", "planejadoFim": None, "estado": ESTADO_INCOMPLETO}
    resposta = client_admin.patch(url(demanda), json={"planejadoFim": "2026-10-30"})
    assert resposta.json()["workflowEtapas"][0]["planejamento"] == {"planejadoInicio": "2026-10-20", "planejadoFim": "2026-10-30", "estado": ESTADO_PLANEJADO}
    # a outra etapa não é tocada
    assert resposta.json()["workflowEtapas"][1]["planejamento"] == VAZIO
    assert planejamento(client_admin, demanda)["estado"] == ESTADO_PLANEJADO


# ── PATCH parcial: o PAR RESULTANTE ──────────────────────────────────────────────────────────────────────────────


def test_fluxo_parcial_criar_completar_alterar_um_de_cada_vez_e_limpar(client_admin) -> None:
    _, demanda = criar(client_admin)
    ok = lambda corpo: client_admin.patch(url(demanda), json=corpo)  # noqa: E731
    assert ok({"planejadoInicio": "2026-10-20"}).status_code == 200                      # criar início
    assert ok({"planejadoFim": "2026-10-30"}).status_code == 200                         # completar o fim depois
    assert ok({"planejadoInicio": "2026-10-22"}).status_code == 200                      # só o início, fim válido mantido
    assert planejamento(client_admin, demanda) == {"planejadoInicio": "2026-10-22", "planejadoFim": "2026-10-30", "estado": ESTADO_PLANEJADO}
    assert ok({"planejadoFim": "2026-11-05"}).status_code == 200                         # só o fim, início válido mantido
    assert planejamento(client_admin, demanda) == {"planejadoInicio": "2026-10-22", "planejadoFim": "2026-11-05", "estado": ESTADO_PLANEJADO}
    assert ok({"planejadoFim": "2026-10-22"}).status_code == 200                         # fim == início é válido
    assert ok({"planejadoFim": None}).status_code == 200                                 # limpar só o fim → incompleto
    assert planejamento(client_admin, demanda) == {"planejadoInicio": "2026-10-22", "planejadoFim": None, "estado": ESTADO_INCOMPLETO}
    assert ok({"planejadoFim": "2026-10-30"}).status_code == 200
    assert ok({"planejadoInicio": None, "planejadoFim": None}).status_code == 200        # apagar ambos
    assert planejamento(client_admin, demanda) == VAZIO


def test_422_fim_numa_etapa_sem_inicio(client_admin) -> None:
    _, demanda = criar(client_admin)
    resposta = client_admin.patch(url(demanda), json={"planejadoFim": "2026-10-30"})
    assert resposta.status_code == 422
    assert planejamento(client_admin, demanda) == VAZIO


def test_422_apagar_so_o_inicio_mantendo_o_fim(client_admin) -> None:
    _, demanda = criar(client_admin)
    assert client_admin.patch(url(demanda), json={"planejadoInicio": "2026-10-20", "planejadoFim": "2026-10-30"}).status_code == 200
    assert client_admin.patch(url(demanda), json={"planejadoInicio": None}).status_code == 422
    assert planejamento(client_admin, demanda) == {"planejadoInicio": "2026-10-20", "planejadoFim": "2026-10-30", "estado": ESTADO_PLANEJADO}


@pytest.mark.parametrize(
    "corpo",
    [
        {"planejadoInicio": "2026-10-20", "planejadoFim": "2026-10-19"},   # fim < início (mesmo PATCH)
        {"planejadoInicio": "2026-10-31"},                                 # início passa do fim já gravado
        {"planejadoFim": "2026-10-19"},                                    # fim passa a ser anterior ao início gravado
        {"planejadoInicio": None, "planejadoFim": "2026-10-30"},           # fim sem início no mesmo PATCH
    ],
)
def test_422_pares_resultantes_invalidos_nao_alteram_nada(client_admin, db_session, corpo) -> None:
    _, demanda = criar(client_admin)
    assert client_admin.patch(url(demanda), json={"planejadoInicio": "2026-10-20", "planejadoFim": "2026-10-30"}).status_code == 200
    antes = len(eventos(db_session, demanda["id"]))
    assert client_admin.patch(url(demanda), json=corpo).status_code == 422
    assert planejamento(client_admin, demanda) == {"planejadoInicio": "2026-10-20", "planejadoFim": "2026-10-30", "estado": ESTADO_PLANEJADO}
    assert len(eventos(db_session, demanda["id"])) == antes


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"ordem": 2},
        {"planejadoInicio": "2026-10-20", "status": "concluida"},
        {"planejadoInicio": "2026-10-20T10:00:00Z"},
        {"planejadoInicio": "2026-10-20T00:00:00"},
        {"planejadoInicio": "20/10/2026"},
        {"planejadoInicio": "2026-13-40"},
        {"planejadoInicio": 20261020},
        {"planejadoInicio": True},
        {"planejadoInicio": ["2026-10-20"]},
    ],
)
def test_contrato_recusa_corpo_vazio_campos_extras_e_formatos_invalidos(client_admin, corpo) -> None:
    _, demanda = criar(client_admin)
    assert client_admin.patch(url(demanda), json=corpo).status_code == 422
    assert planejamento(client_admin, demanda) == VAZIO


# ── auditoria ────────────────────────────────────────────────────────────────────────────────────────────────────


def test_evento_com_valores_anteriores_e_novos_e_no_op_sem_evento(client_admin, db_session, usuario_admin) -> None:
    _, demanda = criar(client_admin)
    assert client_admin.patch(url(demanda), json={"planejadoInicio": "2026-10-20"}).status_code == 200
    assert client_admin.patch(url(demanda), json={"planejadoFim": "2026-10-30"}).status_code == 200
    registrados = eventos(db_session, demanda["id"])
    assert len(registrados) == 2
    primeiro, segundo = registrados
    assert primeiro.usuario_id == usuario_admin.id and primeiro.occurred_at is not None
    assert {k: primeiro.payload[k] for k in ("inicioAnterior", "inicioNovo", "fimAnterior", "fimNovo")} == {
        "inicioAnterior": None, "inicioNovo": "2026-10-20", "fimAnterior": None, "fimNovo": None,
    }
    assert {k: segundo.payload[k] for k in ("inicioAnterior", "inicioNovo", "fimAnterior", "fimNovo")} == {
        "inicioAnterior": "2026-10-20", "inicioNovo": "2026-10-20", "fimAnterior": None, "fimNovo": "2026-10-30",
    }
    assert segundo.payload["etapaId"] == demanda["workflowEtapas"][0]["id"] and segundo.payload["etapaNome"] == "Etapa 0"
    # repetir o mesmo valor (campo a campo ou o par inteiro) e limpar o que já está limpo não fabrica evento
    for corpo in ({"planejadoInicio": "2026-10-20"}, {"planejadoFim": "2026-10-30"}, {"planejadoInicio": "2026-10-20", "planejadoFim": "2026-10-30"}):
        assert client_admin.patch(url(demanda), json=corpo).status_code == 200
    assert len(eventos(db_session, demanda["id"])) == 2
    assert client_admin.patch(url(demanda, 1), json={"planejadoInicio": None, "planejadoFim": None}).status_code == 200
    assert len(eventos(db_session, demanda["id"])) == 2
    historico = client_admin.get(f"/demandas/{demanda['id']}/historico").json()
    assert any(item["tipo"] == TIPO_EVENTO for item in historico)


def test_evento_falha_reverte_o_planejamento(client_admin, monkeypatch) -> None:
    from app.api.routes.demandas import workflow_service

    _, demanda = criar(client_admin)

    def falhar(*args, **kwargs):
        raise RuntimeError("falha sintética de auditoria")

    monkeypatch.setattr(workflow_service.demanda_service, "publicar_evento_demanda", falhar)
    with pytest.raises(RuntimeError, match="auditoria"):
        client_admin.patch(url(demanda), json={"planejadoInicio": "2026-10-20"})
    assert planejamento(client_admin, demanda) == VAZIO


# ── efeitos colaterais: prazo, status, etapa atual, sessões e intervalos ────────────────────────────────────────


def test_editar_planejamento_nao_altera_status_prazo_etapa_atual_sessoes_nem_intervalos(client_admin, db_session, usuario_admin) -> None:
    _, demanda = criar(client_admin)
    assert client_admin.patch(f"/demandas/{demanda['id']}", json={"prazoEtapaAtual": "2026-11-20T12:00:00Z", "dataInicio": "2026-11-01", "dataFimPrevista": "2026-11-20"}).status_code == 200
    demanda = client_admin.get(f"/demandas/{demanda['id']}").json()
    db_session.expire_all()
    linha = db_session.get(Demanda, demanda["id"])
    antes = (linha.status, linha.prazo_etapa_atual, linha.data_inicio, linha.data_fim_prevista, linha.pausada_em, linha.pausa_origem)
    contagens = lambda: (  # noqa: E731
        db_session.scalar(select(func.count()).select_from(SessaoTrabalho)),
        db_session.scalar(select(func.count()).select_from(DemandaStatusIntervalo).where(DemandaStatusIntervalo.demanda_id == demanda["id"])),
    )
    sessoes_e_intervalos = contagens()
    etapas_antes = [(e.status, e.ordem, e.iniciada_em, e.concluida_em, e.esforco_estimado_minutos) for e in db_session.scalars(select(DemandaWorkflowEtapa).where(DemandaWorkflowEtapa.demanda_id == demanda["id"]).order_by(DemandaWorkflowEtapa.ordem))]

    resposta = client_admin.patch(url(demanda, 1), json={"planejadoInicio": "2026-10-20", "planejadoFim": "2026-10-30"})
    assert resposta.status_code == 200, resposta.text
    atual = resposta.json()
    for campo in ("status", "prazoEtapaAtual", "dataInicio", "dataFimPrevista", "etapaAtualId", "workflowModeloId", "usuarioResponsavelIds"):
        assert atual[campo] == demanda[campo], campo
    for indice in (0, 1):  # esforço, prazo da etapa e status das etapas intactos
        for campo in ("esforcoEstimadoMinutos", "quantidadeAntesDeadline", "unidadePrazo", "status", "iniciadaEm", "concluidaEm"):
            assert atual["workflowEtapas"][indice][campo] == demanda["workflowEtapas"][indice][campo], campo

    db_session.expire_all()
    linha = db_session.get(Demanda, demanda["id"])
    assert (linha.status, linha.prazo_etapa_atual, linha.data_inicio, linha.data_fim_prevista, linha.pausada_em, linha.pausa_origem) == antes
    assert contagens() == sessoes_e_intervalos
    etapas_depois = [(e.status, e.ordem, e.iniciada_em, e.concluida_em, e.esforco_estimado_minutos) for e in db_session.scalars(select(DemandaWorkflowEtapa).where(DemandaWorkflowEtapa.demanda_id == demanda["id"]).order_by(DemandaWorkflowEtapa.ordem))]
    assert etapas_depois == etapas_antes


def test_etapa_futura_e_concluida_tambem_aceitam_planejamento_sem_transicao(client_admin) -> None:
    _, demanda = criar(client_admin, 3)
    assert client_admin.patch(url(demanda, 2), json={"planejadoInicio": "2026-12-01", "planejadoFim": "2026-12-05"}).status_code == 200
    assert client_admin.post(f"/demandas/{demanda['id']}/workflow/etapas/{demanda['workflowEtapas'][0]['id']}/concluir").status_code == 200
    assert client_admin.patch(url(demanda, 0), json={"planejadoInicio": "2026-10-01"}).status_code == 200
    lido = client_admin.get(f"/demandas/{demanda['id']}").json()
    assert [e["status"] for e in lido["workflowEtapas"]][0] == "concluida"
    assert lido["etapaAtualId"] == demanda["workflowEtapas"][1]["id"]


# ── autoridade (a mesma do esforço) ──────────────────────────────────────────────────────────────────────────────


def test_autoridade_igual_a_do_esforco(client_admin, client_operador, client_gestor, usuario_operador) -> None:
    _, demanda = criar(client_admin, responsavel_ids=[usuario_operador.id])
    assert client_operador.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"][0]["podeEditarPlanejamento"]
    assert client_operador.patch(url(demanda), json={"planejadoInicio": "2026-10-20"}).status_code == 200
    assert client_gestor.patch(url(demanda, 1), json={"planejadoInicio": "2026-10-21"}).status_code == 200


def test_visibilidade_nao_concede_planejamento(client_admin, client_operador, usuario_operador) -> None:
    modelo, _ = criar(client_admin)
    demanda = _criar_demanda(client_admin, workflowModeloId=modelo["id"], usuarioResponsavelIds=[usuario_operador.id]).json()
    leitura = client_operador.get(f"/demandas/{demanda['id']}").json()
    assert not leitura["workflowEtapas"][0]["podeEditarPlanejamento"]
    assert client_operador.patch(url(demanda), json={"planejadoInicio": "2026-10-20"}).status_code == 403


def test_cross_tenant_e_etapa_de_outra_demanda(client_admin, app, db_session, outra_empresa) -> None:
    from fastapi.testclient import TestClient

    _, demanda = criar(client_admin)
    _, outra = criar(client_admin)
    caminho = f"/demandas/{demanda['id']}/workflow/etapas/{outra['workflowEtapas'][0]['id']}/planejamento"
    assert client_admin.patch(caminho, json={"planejadoInicio": "2026-10-20"}).status_code == 404
    usuario = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="outro-plan")
    cliente = TestClient(app)
    cliente.headers["Authorization"] = "Bearer " + create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base="admin")
    assert cliente.patch(url(demanda), json={"planejadoInicio": "2026-10-20"}).status_code == 404


def test_arquivada_recusa_e_nao_oferece_edicao(client_admin) -> None:
    _, demanda = criar(client_admin)
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "Teste"}).status_code == 200
    assert not client_admin.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"][0]["podeEditarPlanejamento"]
    assert client_admin.patch(url(demanda), json={"planejadoInicio": "2026-10-20"}).status_code == 409


def test_token_de_plataforma_nao_edita(app, client_admin, usuario_admin) -> None:
    from fastapi.testclient import TestClient

    from app.core.security import create_platform_token

    _, demanda = criar(client_admin)
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer " + create_platform_token(sub=usuario_admin.id, administrador_id=str(uuid.uuid4()))
    assert client.patch(url(demanda), json={"planejadoInicio": "2026-10-20"}).status_code in (401, 403)


# ── template: sem janela ─────────────────────────────────────────────────────────────────────────────────────────


def test_template_nao_tem_janela_planejada(client_admin) -> None:
    colunas = {coluna.name for coluna in WorkflowModeloEtapa.__table__.columns}
    assert not {"planejado_inicio", "planejado_fim"} & colunas
    modelo, _ = criar(client_admin)
    assert all("planejamento" not in etapa and "planejadoInicio" not in etapa for etapa in modelo["etapas"])
    assert client_admin.post("/workflow-modelos", json={"nome": "Com janela", "etapas": [{**_etapa_modelo(), "planejadoInicio": "2026-10-20"}]}).status_code == 422


# ── percentual de capacidade alocável ────────────────────────────────────────────────────────────────────────────


def test_percentual_default_100_e_aceita_1_75_100(client_admin, db_session, empresa) -> None:
    assert client_admin.get("/regra-expediente").json()["percentualCapacidadeAlocavel"] == 100
    for valor in (1, 75, 100):
        resposta = client_admin.patch("/regra-expediente", json={"percentualCapacidadeAlocavel": valor})
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["percentualCapacidadeAlocavel"] == valor
        assert client_admin.get("/regra-expediente").json()["percentualCapacidadeAlocavel"] == valor
    db_session.expire_all()
    assert db_session.scalar(select(RegraModel.percentual_capacidade_alocavel).where(RegraModel.empresa_id == empresa.id)) == 100


@pytest.mark.parametrize("valor", [0, 101, -1, 150, 75.5, "75", True, False, [75]])
def test_percentual_recusa_fora_do_intervalo_e_tipos_invalidos(client_admin, valor) -> None:
    assert client_admin.patch("/regra-expediente", json={"percentualCapacidadeAlocavel": 80}).status_code == 200
    assert client_admin.patch("/regra-expediente", json={"percentualCapacidadeAlocavel": valor}).status_code == 422
    assert client_admin.get("/regra-expediente").json()["percentualCapacidadeAlocavel"] == 80


@pytest.mark.parametrize("valor", [0, 101])
def test_banco_recusa_percentual_fora_do_intervalo(client_admin, db_session, empresa, valor) -> None:
    client_admin.get("/regra-expediente")
    with pytest.raises(IntegrityError, match="ck_regra_expediente_percentual_capacidade_alocavel"):
        db_session.execute(text("UPDATE regra_expediente SET percentual_capacidade_alocavel = :v WHERE empresa_id = :e"), {"v": valor, "e": empresa.id})
        db_session.flush()
    db_session.rollback()


def test_editar_o_percentual_nao_rearma_a_pausa_automatica_nem_mexe_no_calendario(client_admin, db_session, empresa) -> None:
    antes_regra = _configurar(client_admin, pausarNoFimPeriodo=True, bloquearForaExpediente=True)
    regra = db_session.scalar(select(RegraModel).where(RegraModel.empresa_id == empresa.id))
    armada_em = regra.pausa_automatica_ativada_em
    assert armada_em is not None
    for valor in (75, 100, 50):
        resposta = client_admin.patch("/regra-expediente", json={"percentualCapacidadeAlocavel": valor})
        assert resposta.status_code == 200, resposta.text
        db_session.expire_all()
        regra = db_session.scalar(select(RegraModel).where(RegraModel.empresa_id == empresa.id))
        assert regra.pausa_automatica_ativada_em == armada_em  # carimbo INTACTO — não é calendário
        assert regra.pausar_no_fim_periodo and regra.bloquear_fora_expediente
    depois = client_admin.get("/regra-expediente").json()
    for campo in ("ativo", "dias", "timezone", "antecedenciaAcessoMinutos", "toleranciaRetomadaMinutos", "pausarNoFimPeriodo", "bloquearForaExpediente", "pausaAutomaticaAtivadaEm", "diasEspeciais"):
        assert depois[campo] == antes_regra[campo], campo
    assert depois["percentualCapacidadeAlocavel"] == 50
    # o evento da regra registra só o campo alterado
    evento = db_session.scalars(select(Evento).where(Evento.entidade_id == regra.id, Evento.tipo == "regra_expediente.alterada").order_by(Evento.created_at.desc())).first()
    assert evento is not None and evento.payload["camposAlterados"] == ["percentualCapacidadeAlocavel"]
    # repetir o valor não é alteração
    assert client_admin.patch("/regra-expediente", json={"percentualCapacidadeAlocavel": 50}).status_code == 200
    db_session.expire_all()
    assert db_session.scalar(select(RegraModel.pausa_automatica_ativada_em).where(RegraModel.empresa_id == empresa.id)) == armada_em
