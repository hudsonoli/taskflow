"""Fase 7C.1 — fechamento das visões: universo da Pauta (sem prazo incluído) e DETALHE somente-leitura pela Pauta global.

- Pauta global = toda demanda ATIVA da empresa, com ou sem prazo (prazo não é condição de pertencer à operação); atrasadas incluídas;
  concluída, cancelada e arquivada nunca;
- `?escopo=pauta` nos GET do detalhe (demanda, comentários, histórico, checklist, arquivos e download) dá LEITURA a Atendimento, Head e
  Gestão, só dentro da empresa; operador comum recebe 403;
- ler pela Pauta global NÃO dá escrita: PATCH/POST/DELETE seguem no escopo-base (404 fora dele) e ignoram o parâmetro.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from tests.test_demanda import _criar
from tests.test_fase_7c_visoes_lideranca import _cenario, _client_para, _ids, _lista
from tests.test_gerenciador_arquivos import PNG_VALIDO, _link, _upload

PAUTA = {"escopo": "pauta"}


def _definir_status(db: Session, demanda: dict, status: str) -> None:
    db.get(Demanda, demanda["id"]).status = status
    db.commit()


# ======================================================================================
# UNIVERSO DA PAUTA — o prazo NÃO decide quem pertence à operação
# ======================================================================================


def test_pauta_inclui_com_prazo_atrasada_e_sem_prazo(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    depto = c["criacao"].id
    agora = datetime.now(timezone.utc)
    com_prazo = _criar(client_admin, departamentoResponsavelIds=[depto], prazoEtapaAtual=(agora + timedelta(days=5)).isoformat())
    atrasada = _criar(client_admin, departamentoResponsavelIds=[depto], prazoEtapaAtual=(agora - timedelta(days=5)).isoformat())
    sem_prazo = _criar(client_admin, departamentoResponsavelIds=[depto], nome="Post institucional")
    assert sem_prazo["prazoEtapaAtual"] is None
    pauta = _ids(_lista(_client_para(app, c["ana"]), "pauta"))
    assert {com_prazo["id"], atrasada["id"], sem_prazo["id"]} <= pauta


@pytest.mark.parametrize("status", ["concluida", "cancelada", "arquivada"])
def test_pauta_nunca_mostra_demanda_finalizada_nem_sem_o_cliente_pedir(app, db_session, empresa, client_admin, status) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    finalizada = _criar(client_admin, departamentoResponsavelIds=[c["criacao"].id])
    _definir_status(db_session, finalizada, status)
    ana = _client_para(app, c["ana"])
    # nem sem `naoFinalizada` (o servidor garante), nem pedindo explicitamente o status
    assert finalizada["id"] not in _ids(_lista(ana, "pauta"))
    assert finalizada["id"] not in _ids(_lista(ana, "pauta", naoFinalizada="true"))
    if status != "arquivada":
        assert _lista(ana, "pauta", status=status) == []  # filtro de status finalizado + Pauta (só em aberto) = vazio


def test_estados_operacionais_reais_aparecem_na_pauta(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    estados = ["planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"]
    criadas = {}
    for estado in estados:
        d = _criar(client_admin, departamentoResponsavelIds=[c["outros"]["Digital"].id])
        _definir_status(db_session, d, estado)
        criadas[estado] = d["id"]
    pauta = _ids(_lista(_client_para(app, c["ana"]), "pauta"))
    assert set(criadas.values()) <= pauta


def test_pauta_sem_prazo_pagina_no_servidor(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    sem_prazo = [_criar(client_admin, departamentoResponsavelIds=[c["outros"]["Mídia"].id]) for _ in range(3)]
    ana = _client_para(app, c["ana"])
    total = len(_lista(ana, "pauta"))
    paginas = _lista(ana, "pauta", limit=10, offset=0) + _lista(ana, "pauta", limit=10, offset=10) + _lista(ana, "pauta", limit=10, offset=20)
    assert len(paginas) == total == len({d["id"] for d in paginas})
    assert {d["id"] for d in sem_prazo} <= {d["id"] for d in paginas}


# ======================================================================================
# DETALHE SOMENTE-LEITURA PELA PAUTA GLOBAL
# ======================================================================================


def _demanda_completa(client_admin: TestClient, departamento_id: str) -> dict:
    """Demanda com comentário, item de checklist, link e arquivo físico — o que o drawer lê."""
    demanda = _criar(client_admin, departamentoResponsavelIds=[departamento_id], briefing="Briefing do post")
    assert client_admin.post(f"/demandas/{demanda['id']}/comentarios", json={"texto": "Primeira nota"}).status_code == 201
    assert client_admin.post(f"/demandas/{demanda['id']}/checklist", json={"texto": "Revisar texto"}).status_code == 201
    link = _link(client_admin, demanda["id"], titulo="Referência").json()
    arquivo = _upload(client_admin, demanda["id"], nome="arte.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout").json()
    return {**demanda, "link_id": link["id"], "arquivo_id": arquivo["id"]}


def _leituras(d: dict) -> dict[str, str]:
    i = d["id"]
    return {
        "detalhe": f"/demandas/{i}",
        "comentarios": f"/demandas/{i}/comentarios",
        "historico": f"/demandas/{i}/historico",
        "checklist": f"/demandas/{i}/checklist",
        "arquivos": f"/demandas/{i}/arquivos",
        "download": f"/demandas/{i}/arquivos/{d['arquivo_id']}/download",
    }


@pytest.mark.parametrize("quem", ["ana", "maria", "carlos"])
def test_quem_tem_pauta_global_le_o_detalhe_de_demanda_de_outro_departamento(app, db_session, empresa, client_admin, quem) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    alvo = _demanda_completa(client_admin, c["outros"]["Digital"].id)  # Digital: fora do escopo-base de Ana e de Maria (Head de Criação)
    cliente = _client_para(app, c[quem])
    if quem in ("ana", "maria"):  # sem o parâmetro continua 404: o escopo-base não mudou
        for nome, url in _leituras(alvo).items():
            assert cliente.get(url).status_code == 404, f"{quem}/{nome} sem escopo=pauta"
    for nome, url in _leituras(alvo).items():
        resposta = cliente.get(url, params=PAUTA)
        assert resposta.status_code == 200, f"{quem}/{nome}: {resposta.status_code} {resposta.text[:120]}"
    detalhe = cliente.get(_leituras(alvo)["detalhe"], params=PAUTA).json()
    assert detalhe["briefing"] == "Briefing do post"
    assert [c_["texto"] for c_ in cliente.get(_leituras(alvo)["comentarios"], params=PAUTA).json()] == ["Primeira nota"]
    assert [i_["texto"] for i_ in cliente.get(_leituras(alvo)["checklist"], params=PAUTA).json()] == ["Revisar texto"]
    assert len(cliente.get(_leituras(alvo)["arquivos"], params=PAUTA).json()) == 2  # link + arquivo
    download = cliente.get(_leituras(alvo)["download"], params=PAUTA)
    assert download.content == PNG_VALIDO


def test_atendimento_le_demanda_de_criacao_pela_pauta(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    alvo = _demanda_completa(client_admin, c["criacao"].id)
    ana = _client_para(app, c["ana"])
    assert ana.get(f"/demandas/{alvo['id']}").status_code == 404  # fora do escopo-base
    assert ana.get(f"/demandas/{alvo['id']}", params=PAUTA).status_code == 200


def test_operador_comum_nao_le_pela_pauta_403_em_todas_as_leituras(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    alvo = _demanda_completa(client_admin, c["criacao"].id)  # do próprio departamento do João: ele a vê no escopo-base...
    joao = _client_para(app, c["joao"])
    for nome, url in _leituras(alvo).items():
        assert joao.get(url).status_code == 200, f"{nome} no escopo-base"
        assert joao.get(url, params=PAUTA).status_code == 403, f"{nome} com escopo=pauta"  # ...mas escopo=pauta é negado
    assert joao.get("/demandas", params=PAUTA).status_code == 403


@pytest.mark.parametrize("valor", ["meus", "meu-departamento", "atendimento", "qualquer"])
def test_detalhe_so_aceita_escopo_pauta(app, db_session, empresa, client_admin, valor) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    alvo = c["todas"][0]
    assert _client_para(app, c["ana"]).get(f"/demandas/{alvo['id']}", params={"escopo": valor}).status_code == 422


def test_leitura_pela_pauta_nao_atravessa_tenant(app, db_session, empresa, outra_empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    agora = datetime.now(timezone.utc)
    alheia = Demanda(
        id=str(uuid.uuid4()), empresa_id=outra_empresa.id, codigo_referencia="T26996001", ano_referencia=26, sequencial_referencia=1,
        numero_operacional=996001, nome="Demanda de outra empresa", status="planejada", prioridade="media", created_at=agora, updated_at=agora,
    )
    db_session.add(alheia)
    db_session.commit()
    for quem in ("ana", "maria", "carlos"):
        cliente = _client_para(app, c[quem])
        assert cliente.get(f"/demandas/{alheia.id}", params=PAUTA).status_code == 404, quem
        for sub in ("comentarios", "historico", "checklist", "arquivos"):
            assert cliente.get(f"/demandas/{alheia.id}/{sub}", params=PAUTA).status_code == 404, f"{quem}/{sub}"


# ======================================================================================
# LEITURA ≠ ESCRITA — o novo escopo não concede nenhuma escrita
# ======================================================================================


@pytest.mark.parametrize("quem", ["ana", "maria"])
def test_pauta_global_nao_concede_escrita(app, db_session, empresa, client_admin, quem) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    alvo = _demanda_completa(client_admin, c["outros"]["Digital"].id)
    cliente = _client_para(app, c[quem])
    i = alvo["id"]
    escritas = [
        ("patch", f"/demandas/{i}", {"json": {"nome": "mudou"}}),
        ("patch", f"/demandas/{i}", {"json": {"departamentoResponsavelIds": [c["criacao"].id]}}),
        ("post", f"/demandas/{i}/arquivar", {"json": {"motivoArquivamento": "x"}}),
        ("post", f"/demandas/{i}/comentarios", {"json": {"texto": "intruso"}}),
        ("post", f"/demandas/{i}/checklist", {"json": {"texto": "intruso"}}),
        ("post", f"/demandas/{i}/arquivos/link", {"json": {"titulo": "x", "url": "https://exemplo.com/x"}}),
        ("patch", f"/demandas/{i}/arquivos/{alvo['arquivo_id']}", {"json": {"statusLayout": "aprovado"}}),
        ("delete", f"/demandas/{i}/arquivos/{alvo['arquivo_id']}", {}),
        ("post", f"/demandas/{i}/ajustes", {"json": {"tipo": "ajuste_interno"}}),
    ]
    for metodo, url, extra in escritas:
        # com e sem o parâmetro: a escrita ignora `escopo=pauta` e continua no escopo-base (404 fora dele)
        for params in (None, PAUTA):
            resposta = getattr(cliente, metodo)(url, params=params, **extra)
            assert resposta.status_code in (403, 404), f"{quem} {metodo.upper()} {url} {params}: {resposta.status_code}"
    # nada mudou
    lido = client_admin.get(f"/demandas/{i}").json()
    assert lido["nome"] == alvo["nome"] and lido["departamentoResponsavelIds"] == [c["outros"]["Digital"].id]
    assert [x["texto"] for x in client_admin.get(f"/demandas/{i}/comentarios").json()] == ["Primeira nota"]
    assert [x["texto"] for x in client_admin.get(f"/demandas/{i}/checklist").json()] == ["Revisar texto"]


def test_gestor_continua_editando_como_sempre_sem_bypass_novo(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    alvo = _criar(client_admin, departamentoResponsavelIds=[c["outros"]["Digital"].id])
    carlos = _client_para(app, c["carlos"])
    # a autoridade de edição do Gestor é a de sempre (escopo-base com visão total) — com ou sem o parâmetro
    assert carlos.patch(f"/demandas/{alvo['id']}", json={"nome": "editada pelo gestor"}).status_code == 200


def test_head_so_edita_o_que_ja_podia(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    maria = _client_para(app, c["maria"])
    de_digital = c["digital"][0]
    de_criacao = c["soltas"][0]
    assert maria.get(f"/demandas/{de_digital['id']}", params=PAUTA).status_code == 200  # lê pela Pauta
    assert maria.patch(f"/demandas/{de_digital['id']}", json={"nome": "x"}).status_code == 404  # não edita fora do escopo
    assert maria.patch(f"/demandas/{de_criacao['id']}", json={"nome": "editada pela head"}).status_code == 200  # no dela, como sempre
