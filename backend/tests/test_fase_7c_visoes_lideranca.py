"""Fase 7C — as três visões operacionais têm escopos DIFERENTES e a autorização é do servidor.

- MEU DIA (`escopo=meus`)            = o que está designado a mim;
- MEU DEPARTAMENTO (`escopo=meu-departamento`) = o departamento que EU lidero (Head é relação, não perfil);
- PAUTA (`escopo=pauta`)            = todos os departamentos da PRÓPRIA empresa, para Atendimento, Head e Gestor/Admin.

Provas: matriz João/Maria/Ana/Carlos; os três universos não coincidem; filtros não ampliam; pauta global é global DENTRO do tenant;
quem está trabalhando agora vem da sessão real (Head do departamento); operador comum não recebe nada global.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_2d_operador_contexto import _com_departamento
from tests.test_d1_criacao_demandas import _atendimento, _client_para, _head_por_responsavel, _operador_comum
from tests.test_demanda import _criar, _departamento
from tests.test_trafego_carga import _sessao

NOMES = ["Criação", "Social", "Digital", "Redação", "Mídia"]


def _ids(itens: list[dict]) -> set[str]:
    return {item["id"] for item in itens}


def _lista(client: TestClient, escopo: str, **extra) -> list[dict]:
    resposta = client.get("/demandas", params={"escopo": escopo, "limit": 200, **extra})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _cenario(app, db: Session, empresa: Empresa, client_admin: TestClient) -> dict:
    """João (operador, Criação), Maria (Head de Criação), Ana (Atendimento), Carlos (gestor, SEM liderança).

    Demandas: Maria tem 3 designadas a ela (todas em Criação) + 5 outras em Criação (de João e de ninguém); Social 4, Digital 3,
    Redação 2, Mídia 2, Atendimento 2 → Criação = 8, empresa inteira = 21."""
    criacao = _departamento(db, empresa, nome="Criação")
    outros = {nome: _departamento(db, empresa, nome=nome) for nome in NOMES[1:]}
    joao = _operador_comum(db, empresa, sufixo="c7-joao")
    _com_departamento(db, joao, criacao)
    maria = _operador_comum(db, empresa, sufixo="c7-maria")
    criacao.responsavel_usuario_id = maria.id  # Head formal de Criação
    ana = _operador_comum(db, empresa, sufixo="c7-ana")
    atendimento = _atendimento(db, empresa, ana)
    carlos = _criar_usuario_com_credencial(db, empresa=empresa, perfil_base="gestor", email_prefixo="c7-carlos")
    db.commit()

    def demandas(qtd: int, depto, resp=None):
        return [
            _criar(client_admin, departamentoResponsavelIds=[depto.id], **({"usuarioResponsavelIds": [resp.id]} if resp else {}))
            for _ in range(qtd)
        ]

    da_maria = demandas(3, criacao, maria)
    da_joao = demandas(3, criacao, joao)
    soltas = demandas(2, criacao)
    social, digital, redacao, midia = (demandas(q, outros[n]) for q, n in ((4, "Social"), (3, "Digital"), (2, "Redação"), (2, "Mídia")))
    de_atendimento = demandas(2, atendimento)
    todas = da_maria + da_joao + soltas + social + digital + redacao + midia + de_atendimento
    return {
        "criacao": criacao, "outros": outros, "atendimento": atendimento,
        "joao": joao, "maria": maria, "ana": ana, "carlos": carlos,
        "da_maria": da_maria, "da_joao": da_joao, "soltas": soltas, "todas": todas,
        "social": social, "midia": midia, "digital": digital, "redacao": redacao,
        "criacao_todas": da_maria + da_joao + soltas,
    }


# ======================================================================================
# OS TRÊS UNIVERSOS NÃO COINCIDEM (mesmo usuário: Maria, Head)
# ======================================================================================


def test_tres_universos_distintos_para_o_mesmo_head(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    maria = _client_para(app, c["maria"])
    meu_dia = _ids(_lista(maria, "meus"))
    meu_departamento = _ids(_lista(maria, "meu-departamento"))
    pauta = _ids(_lista(maria, "pauta"))

    assert meu_dia == {d["id"] for d in c["da_maria"]}  # 3
    assert meu_departamento == {d["id"] for d in c["criacao_todas"]}  # 8: só Criação
    assert pauta == {d["id"] for d in c["todas"]}  # 21: a empresa toda
    assert (len(meu_dia), len(meu_departamento), len(pauta)) == (3, 8, 21)
    assert meu_dia < meu_departamento < pauta  # estritamente contidos: cada visão é maior que a anterior


# ======================================================================================
# MATRIZ DE PAPÉIS
# ======================================================================================


def test_joao_operador_so_tem_meu_dia(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    joao = _client_para(app, c["joao"])
    assert _ids(_lista(joao, "meus")) == {d["id"] for d in c["da_joao"]}
    assert joao.get("/demandas", params={"escopo": "meu-departamento"}).status_code == 403  # não é Head
    assert joao.get("/demandas", params={"escopo": "pauta"}).status_code == 403  # sem pauta global


def test_maria_head_tem_meu_dia_meu_departamento_e_pauta(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    maria = _client_para(app, c["maria"])
    assert len(_lista(maria, "meus")) == 3
    assert len(_lista(maria, "meu-departamento")) == 8
    assert len(_lista(maria, "pauta")) == 21


def test_ana_atendimento_tem_pauta_mas_meu_departamento_so_se_for_head(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    ana = _client_para(app, c["ana"])
    assert _lista(ana, "meus") == []  # nada designado a ela
    assert ana.get("/demandas", params={"escopo": "meu-departamento"}).status_code == 403
    assert _ids(_lista(ana, "pauta")) == {d["id"] for d in c["todas"]}  # Atendimento acompanha a agência inteira


def test_carlos_gestor_tem_pauta_e_meu_departamento_so_com_lideranca(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    carlos = _client_para(app, c["carlos"])
    assert _lista(carlos, "meus") == []
    assert carlos.get("/demandas", params={"escopo": "meu-departamento"}).status_code == 403  # gestor SEM vínculo de liderança
    assert _ids(_lista(carlos, "pauta")) == {d["id"] for d in c["todas"]}
    # com vínculo de liderança, passa a ter também o Meu Departamento daquele setor (e só daquele)
    c["outros"]["Social"].responsavel_usuario_id = c["carlos"].id
    db_session.commit()
    assert _ids(_lista(carlos, "meu-departamento")) == {d["id"] for d in c["social"]}


def test_admin_tambem_tem_pauta_global(client_admin: TestClient, app, db_session, empresa) -> None:
    _cenario(app, db_session, empresa, client_admin)
    assert len(_lista(client_admin, "pauta")) == 21


def test_head_de_social_tem_pauta_global_mas_meu_departamento_so_de_social(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    head_social = _operador_comum(db_session, empresa, sufixo="c7-head-social")
    c["outros"]["Social"].responsavel_usuario_id = head_social.id
    db_session.commit()
    cliente = _client_para(app, head_social)
    assert _ids(_lista(cliente, "meu-departamento")) == {d["id"] for d in c["social"]}
    assert len(_lista(cliente, "pauta")) == 21


# ======================================================================================
# FILTROS REFINAM, NUNCA AMPLIAM
# ======================================================================================


def test_filtros_nao_ampliam_meu_departamento_e_refinam_a_pauta(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    maria = _client_para(app, c["maria"])
    # Meu Departamento: pedir outro departamento não amplia (continua dentro de Criação → vazio)
    social_id = c["outros"]["Social"].id
    assert _lista(maria, "meu-departamento", departamentoId=social_id) == []
    # ...e "não é Social" não abre nada fora de Criação
    assert _ids(_lista(maria, "meu-departamento")) == {d["id"] for d in c["criacao_todas"]}
    # Pauta: aqui o departamento É um filtro (OR entre valores)
    assert _ids(_lista(maria, "pauta", departamentoId=social_id)) == {d["id"] for d in c["social"]}
    dois = f"{social_id},{c['outros']['Mídia'].id}"
    assert _ids(_lista(maria, "pauta", departamentoId=dois)) == {d["id"] for d in c["social"] + c["midia"]}


def test_pauta_pagina_no_servidor_antes_de_limit_offset(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    ana = _client_para(app, c["ana"])
    pagina1 = _lista(ana, "pauta", limit=10, offset=0)
    pagina2 = _lista(ana, "pauta", limit=10, offset=10)
    pagina3 = _lista(ana, "pauta", limit=10, offset=20)
    todos = _ids(pagina1) | _ids(pagina2) | _ids(pagina3)
    assert (len(pagina1), len(pagina2), len(pagina3)) == (10, 10, 1)
    assert todos == {d["id"] for d in c["todas"]}  # nada fica de fora por causa de página; sem repetição


# ======================================================================================
# GLOBAL = DENTRO DO TENANT
# ======================================================================================


def test_pauta_global_nunca_mostra_outra_empresa(app, db_session, empresa, outra_empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    agora = datetime.now(timezone.utc)
    intrusa = Demanda(
        id=str(uuid.uuid4()), empresa_id=outra_empresa.id, codigo_referencia="T26997001", ano_referencia=26, sequencial_referencia=1,
        numero_operacional=997001, nome="Demanda de outra empresa", status="planejada", prioridade="media", created_at=agora, updated_at=agora,
    )
    db_session.add(intrusa)
    db_session.commit()
    for quem in ("maria", "ana", "carlos"):
        assert intrusa.id not in _ids(_lista(_client_para(app, c[quem]), "pauta")), quem
    assert intrusa.id not in _ids(_lista(client_admin, "pauta"))
    assert _lista(_client_para(app, c["maria"]), "pauta", departamentoId=str(uuid.uuid4())) == []


# ======================================================================================
# QUEM ESTÁ TRABALHANDO AGORA (Meu Departamento) — sessão real, só o Head DO departamento
# ======================================================================================


def test_head_ve_quem_esta_trabalhando_e_em_que_tarefa(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    tarefa = c["da_joao"][0]
    _sessao(db_session, empresa, decorrido=300, usuario=c["joao"], departamento=c["criacao"], demanda_id=tarefa["id"])
    db_session.commit()

    resposta = _client_para(app, c["maria"]).get("/sessoes-trabalho/meu-departamento/agora", params={"departamentoId": c["criacao"].id})
    assert resposta.status_code == 200, resposta.text
    membros = {m["usuarioId"]: m for m in resposta.json()["membros"]}
    assert c["joao"].id in membros
    assert [e["demandaId"] for e in membros[c["joao"].id]["emExecucao"]] == [tarefa["id"]]
    assert membros[c["joao"].id]["emExecucao"][0]["nome"] == tarefa["nome"]
    # quem não tem sessão aparece como "sem atividade em execução" (lista vazia), não como "online"
    assert all(m["emExecucao"] == [] for uid, m in membros.items() if uid != c["joao"].id)
    # sem horário nem duração
    assert set(membros[c["joao"].id]) == {"usuarioId", "nome", "corIdentificacao", "fotoUrl", "emExecucao"}
    assert set(membros[c["joao"].id]["emExecucao"][0]) == {"demandaId", "numeroOperacional", "identificador", "nome"}


def test_status_em_execucao_sem_sessao_nao_conta_como_trabalhando(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    db_session.get(Demanda, c["da_joao"][0]["id"]).status = "em_execucao"
    db_session.commit()
    resposta = _client_para(app, c["maria"]).get("/sessoes-trabalho/meu-departamento/agora", params={"departamentoId": c["criacao"].id})
    assert all(m["emExecucao"] == [] for m in resposta.json()["membros"])


def test_sessao_encerrada_ou_de_outro_departamento_nao_aparece(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    social = c["outros"]["Social"]
    de_social = _operador_comum(db_session, empresa, sufixo="c7-de-social")
    _com_departamento(db_session, de_social, social)
    _sessao(db_session, empresa, status="encerrada", usuario=c["joao"], demanda_id=c["da_joao"][0]["id"])
    _sessao(db_session, empresa, decorrido=100, usuario=de_social, departamento=social, demanda_id=c["social"][0]["id"])
    db_session.commit()
    membros = _client_para(app, c["maria"]).get("/sessoes-trabalho/meu-departamento/agora", params={"departamentoId": c["criacao"].id}).json()["membros"]
    assert all(m["emExecucao"] == [] for m in membros)  # encerrada não conta; gente de Social não é da equipe de Criação
    assert de_social.id not in {m["usuarioId"] for m in membros}


@pytest.mark.parametrize("quem", ["joao", "ana", "carlos"])
def test_quem_nao_e_head_do_departamento_nao_ve_a_equipe_agora(app, db_session, empresa, client_admin, quem) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    resposta = _client_para(app, c[quem]).get("/sessoes-trabalho/meu-departamento/agora", params={"departamentoId": c["criacao"].id})
    assert resposta.status_code == 403, f"{quem}: {resposta.text}"  # nem o gestor sem liderança escolhe um setor qualquer


def test_head_de_criacao_nao_ve_a_equipe_de_outro_departamento(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    resposta = _client_para(app, c["maria"]).get(
        "/sessoes-trabalho/meu-departamento/agora", params={"departamentoId": c["outros"]["Social"].id}
    )
    assert resposta.status_code == 403


def test_equipe_agora_exige_login_e_uuid_valido(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    assert TestClient(app).get("/sessoes-trabalho/meu-departamento/agora", params={"departamentoId": c["criacao"].id}).status_code == 401
    assert _client_para(app, c["maria"]).get("/sessoes-trabalho/meu-departamento/agora", params={"departamentoId": "x"}).status_code == 422
    assert _client_para(app, c["maria"]).get("/sessoes-trabalho/meu-departamento/agora").status_code == 422


def test_equipe_agora_nao_atravessa_tenant(app, db_session, empresa, outra_empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    alheio = _operador_comum(db_session, outra_empresa, sufixo="c7-alheio")
    _sessao(db_session, outra_empresa, decorrido=60, usuario=alheio)
    db_session.commit()
    membros = _client_para(app, c["maria"]).get("/sessoes-trabalho/meu-departamento/agora", params={"departamentoId": c["criacao"].id}).json()["membros"]
    assert alheio.id not in {m["usuarioId"] for m in membros}


# ======================================================================================
# PAUTA — selo discreto "em execução agora" (só ids, só para quem tem a Pauta global)
# ======================================================================================


def test_pauta_mostra_quais_demandas_estao_em_execucao_sem_pessoa_nem_tempo(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    _sessao(db_session, empresa, decorrido=60, usuario=c["joao"], demanda_id=c["da_joao"][0]["id"])
    db_session.commit()
    for quem in ("maria", "ana", "carlos"):
        resposta = _client_para(app, c[quem]).get("/sessoes-trabalho/pauta/em-execucao")
        assert resposta.status_code == 200, quem
        assert resposta.json() == {"demandaIds": [c["da_joao"][0]["id"]]}
    assert _client_para(app, c["joao"]).get("/sessoes-trabalho/pauta/em-execucao").status_code == 403
    assert TestClient(app).get("/sessoes-trabalho/pauta/em-execucao").status_code == 401


def test_pauta_em_execucao_nao_mostra_outro_tenant(app, db_session, empresa, outra_empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    alheio = _operador_comum(db_session, outra_empresa, sufixo="c7-alheio-2")
    _sessao(db_session, outra_empresa, decorrido=60, usuario=alheio)
    db_session.commit()
    assert _client_para(app, c["ana"]).get("/sessoes-trabalho/pauta/em-execucao").json() == {"demandaIds": []}


# ======================================================================================
# COMPATIBILIDADE — escopo padrão (sem `escopo`) não mudou
# ======================================================================================


def test_sem_escopo_o_operador_continua_com_o_escopo_base_de_sempre(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    base = _ids(_client_para(app, c["joao"]).get("/demandas", params={"limit": 200}).json())
    # escopo-base do operador = o que lhe é designado + o próprio departamento (Criação inteira), nada de outros setores
    assert base == {d["id"] for d in c["criacao_todas"]}
    assert not (base & {d["id"] for d in c["social"] + c["midia"]})
