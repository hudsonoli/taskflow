"""Projetos para o Atendimento (P1_ATENDIMENTO_PROJETOS).

O Atendimento (perfil Usuário no departamento Atendimento) demanda as tarefas dos clientes para os departamentos da agência e organiza essas tarefas em Projetos: precisa VER e CRIAR projetos
sem virar gestor. O acesso vem da RELAÇÃO (`eh_atendimento`), como `require_demandas_criar`; o alcance é a carteira (clientes sob sua responsabilidade comercial) mais os projetos internos
(sem cliente) — a mesma regra do diretório (D1.2E). Editar/arquivar/restaurar e os modelos de campanha NÃO são abertos. Override `negar` sempre vence.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from tests.test_d1_2a_cliente_projeto import _projeto
from tests.test_d1_criacao_demandas import _atendimento, _client_para, _head_por_lider, _operador_comum, _override
from tests.test_demanda import _cliente


def _atendimento_operador(db: Session, empresa: Empresa, sufixo: str):
    ator = _operador_comum(db, empresa, sufixo=sufixo)
    _atendimento(db, empresa, ator)
    return ator


def _novo(client: TestClient, **extra):
    return client.post("/projetos", json={"nome": f"Projeto {uuid.uuid4().hex[:8]}", **extra})


# ------------------------------------------------------------------ quem passa


def test_atendimento_operador_lista_e_cria_projeto(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-1")
    cliente = _client_para(app, ator)
    assert cliente.get("/projetos").status_code == 200
    criado = _novo(cliente)
    assert criado.status_code == 201, criado.text
    assert criado.json()["id"] in [p["id"] for p in cliente.get("/projetos").json()]


def test_operador_comum_continua_sem_acesso(client_operador: TestClient) -> None:
    assert client_operador.get("/projetos").status_code == 403
    assert _novo(client_operador).status_code == 403


def test_head_puro_operador_continua_sem_acesso(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-proj")
    _head_por_lider(db_session, empresa, head)  # Head NÃO é Atendimento: continua como antes
    assert _client_para(app, head).get("/projetos").status_code == 403


def test_override_negar_bloqueia_ate_o_atendimento(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-negar")
    _override(db_session, usuario=ator, permissao="projetos.criar", efeito="negar")
    _override(db_session, usuario=ator, permissao="projetos.visualizar", efeito="negar")
    cliente = _client_para(app, ator)
    assert _novo(cliente).status_code == 403
    assert cliente.get("/projetos").status_code == 403


def test_override_negar_so_de_criar_mantem_a_leitura(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-negar-criar")
    _override(db_session, usuario=ator, permissao="projetos.criar", efeito="negar")
    cliente = _client_para(app, ator)
    assert cliente.get("/projetos").status_code == 200
    assert _novo(cliente).status_code == 403


def test_admin_e_gestor_inalterados(client_admin: TestClient, client_gestor: TestClient) -> None:
    assert client_admin.get("/projetos").status_code == 200
    assert client_gestor.get("/projetos").status_code == 200
    assert _novo(client_gestor).status_code == 201


def test_gestor_no_atendimento_nao_e_restringido_a_carteira(app, db_session: Session, empresa: Empresa, usuario_gestor) -> None:
    _atendimento(db_session, empresa, usuario_gestor)  # gestor continua com visão total
    de_outro = _projeto(db_session, empresa, cliente_id=_cliente(db_session, empresa).id)
    ids = {p["id"] for p in _client_para(app, usuario_gestor).get("/projetos").json()}
    assert de_outro.id in ids


# ------------------------------------------------------------------ alcance: carteira + internos


def test_lista_so_carteira_e_projetos_internos(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-lista")
    meu_cliente = _cliente(db_session, empresa, responsavel_comercial_id=ator.id)
    outro_cliente = _cliente(db_session, empresa)
    do_meu = _projeto(db_session, empresa, cliente_id=meu_cliente.id)
    interno = _projeto(db_session, empresa, cliente_id=None)
    do_outro = _projeto(db_session, empresa, cliente_id=outro_cliente.id)

    cliente = _client_para(app, ator)
    ids = {p["id"] for p in cliente.get("/projetos").json()}
    assert {do_meu.id, interno.id} <= ids
    assert do_outro.id not in ids
    assert cliente.get(f"/projetos?clienteId={outro_cliente.id}").json() == []  # nem pelo filtro de cliente


def test_detalhe_fora_da_carteira_e_404_e_na_carteira_e_200(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-detalhe")
    meu_cliente = _cliente(db_session, empresa, responsavel_comercial_id=ator.id)
    do_meu = _projeto(db_session, empresa, cliente_id=meu_cliente.id)
    interno = _projeto(db_session, empresa, cliente_id=None)
    do_outro = _projeto(db_session, empresa, cliente_id=_cliente(db_session, empresa).id)
    cliente = _client_para(app, ator)
    assert cliente.get(f"/projetos/{do_meu.id}").status_code == 200
    assert cliente.get(f"/projetos/{interno.id}").status_code == 200
    assert cliente.get(f"/projetos/{do_outro.id}").status_code == 404


def test_carteira_vazia_ve_so_internos(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-vazia")
    interno = _projeto(db_session, empresa, cliente_id=None)
    do_outro = _projeto(db_session, empresa, cliente_id=_cliente(db_session, empresa).id)
    ids = {p["id"] for p in _client_para(app, ator).get("/projetos").json()}
    assert interno.id in ids and do_outro.id not in ids


def test_cria_para_cliente_da_carteira_e_interno_mas_nao_para_cliente_alheio(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-criar")
    meu_cliente = _cliente(db_session, empresa, responsavel_comercial_id=ator.id)
    alheio = _cliente(db_session, empresa)
    cliente = _client_para(app, ator)
    assert _novo(cliente, clienteId=meu_cliente.id).status_code == 201
    assert _novo(cliente).status_code == 201  # interno (sem cliente)
    recusado = _novo(cliente, clienteId=alheio.id)
    assert recusado.status_code == 422, recusado.text
    ids_clientes = {p["clienteId"] for p in cliente.get("/projetos").json()}
    assert alheio.id not in ids_clientes  # nada foi criado


def test_nunca_vaza_outro_tenant(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-tenant")
    de_fora = _projeto(db_session, outra_empresa, cliente_id=None)
    cliente = _client_para(app, ator)
    assert de_fora.id not in {p["id"] for p in cliente.get("/projetos").json()}
    assert cliente.get(f"/projetos/{de_fora.id}").status_code == 404
    cliente_de_fora = _cliente(db_session, outra_empresa)
    assert _novo(cliente, clienteId=cliente_de_fora.id).status_code == 422


# ------------------------------------------------------------------ o que NÃO foi aberto


def test_atendimento_nao_edita_nem_arquiva_nem_restaura(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-fechado")
    cliente = _client_para(app, ator)
    projeto = _novo(cliente).json()
    assert cliente.patch(f"/projetos/{projeto['id']}", json={"nome": "Outro nome"}).status_code == 403
    assert cliente.post(f"/projetos/{projeto['id']}/arquivar", json={"motivoArquivamento": "teste"}).status_code == 403
    assert cliente.post(f"/projetos/{projeto['id']}/restaurar").status_code == 403


def test_atendimento_nao_acessa_modelos_de_campanha_do_projeto(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-modelo")
    cliente = _client_para(app, ator)
    projeto = _novo(cliente).json()
    assert cliente.get(f"/projetos/{projeto['id']}/modelo-campanha").status_code == 403


def test_projeto_criado_registra_o_atendimento_como_autor(app, db_session: Session, empresa: Empresa) -> None:
    ator = _atendimento_operador(db_session, empresa, "atend-proj-evento")
    cliente = _client_para(app, ator)
    criado = _novo(cliente).json()
    historico = cliente.get(f"/projetos/{criado['id']}")
    assert historico.status_code == 200 and historico.json()["id"] == criado["id"]
