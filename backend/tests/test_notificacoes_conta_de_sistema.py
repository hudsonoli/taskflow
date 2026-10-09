"""Privacidade da conta de sistema nas NOTIFICAÇÕES (hotfix pré-deploy da Fase 1A).

Achado: `GET /notificacoes` resolvia `autorNome` por JOIN em `usuarios`, então o responsável de uma demanda recebia o
NOME REAL da conta de sistema (o proprietário da plataforma) como autor. Regra: a notificação continua existindo
(não se esconde atividade relevante, não se apaga evento), mas o tenant não recebe nenhuma identidade da conta —
o autor é "Sistema" e, coerentemente, a atividade aparece na categoria "sistema". Decisão por `is_system_account`
(nunca por e-mail/nome), num ponto único do service.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario

from tests.fixtures.usuarios import _criar_usuario_com_credencial

NOTIF = "/notificacoes"
NOME_REAL_SISTEMA = "Proprietário Plataforma Secreto"


def _client_de(app, usuario: Usuario) -> TestClient:
    cliente = TestClient(app)
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


def _conta_de_sistema(db: Session, empresa: Empresa) -> Usuario:
    conta = _criar_usuario_com_credencial(db, empresa=empresa, perfil_base="admin", email_prefixo="sistema-notif")
    conta.nome = NOME_REAL_SISTEMA
    conta.is_system_account = True
    db.flush()
    return conta


def _demanda(client: TestClient, responsaveis: list[str]) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Tarefa {uuid.uuid4().hex[:6]}", "usuarioResponsavelIds": responsaveis})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _evento(db: Session, demanda_id: str, empresa_id: str, *, ator: str | None, tipo: str = "demanda.status_alterado") -> Evento:
    agora = datetime.now(timezone.utc)
    evento = Evento(
        id=str(uuid.uuid4()), empresa_id=empresa_id, tipo=tipo, entidade_tipo="demanda", entidade_id=demanda_id,
        usuario_id=ator, payload={"de": "planejada", "para": "em_execucao"}, occurred_at=agora, created_at=agora,
    )
    db.add(evento)
    db.flush()
    return evento


def _item(client: TestClient, evento: Evento) -> dict | None:
    itens = client.get(NOTIF, params={"limit": 100}).json()["itens"]
    return next((i for i in itens if i["id"] == evento.id), None)


def _setup(app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, client_admin: TestClient):
    sistema = _conta_de_sistema(db_session, empresa)
    demanda = _demanda(client_admin, [usuario_operador.id])
    return sistema, demanda, _client_de(app, usuario_operador)


# --------------------------------------------------------------------------------------
# Tenant normal
# --------------------------------------------------------------------------------------


def test_evento_de_usuario_normal_preserva_o_autor(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_gestor: Usuario, client_admin: TestClient
) -> None:
    _, demanda, client = _setup(app, db_session, empresa, usuario_operador, client_admin)
    evento = _evento(db_session, demanda["id"], empresa.id, ator=usuario_gestor.id)
    item = _item(client, evento)
    assert item is not None
    assert item["autorNome"] == usuario_gestor.nome
    assert item["categoria"] == "minhas"


def test_notificacao_de_conta_de_sistema_continua_existindo(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, client_admin: TestClient
) -> None:
    sistema, demanda, client = _setup(app, db_session, empresa, usuario_operador, client_admin)
    evento = _evento(db_session, demanda["id"], empresa.id, ator=sistema.id)
    item = _item(client, evento)
    assert item is not None, "a atividade da conta de sistema não pode sumir da central"
    assert item["titulo"] == "Status da tarefa alterado"
    assert item["detalhe"] == "Planejada → Em execução"
    assert item["demandaId"] == demanda["id"]
    assert item["lida"] is False


def test_identidade_real_da_conta_de_sistema_nao_aparece(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, client_admin: TestClient
) -> None:
    sistema, demanda, client = _setup(app, db_session, empresa, usuario_operador, client_admin)
    _evento(db_session, demanda["id"], empresa.id, ator=sistema.id)
    _evento(db_session, demanda["id"], empresa.id, ator=sistema.id, tipo="demanda.arquivada")
    for categoria in (None, "sistema", "minhas"):
        params = {"limit": 100, **({"categoria": categoria} if categoria else {})}
        bruto = client.get(NOTIF, params=params).text
        for segredo in (NOME_REAL_SISTEMA, sistema.email, sistema.codigo_interno, sistema.id):
            assert segredo not in bruto, f"vazou {segredo!r} em categoria={categoria}"


def test_autor_exibido_e_sistema_e_vai_para_a_categoria_sistema(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, client_admin: TestClient
) -> None:
    sistema, demanda, client = _setup(app, db_session, empresa, usuario_operador, client_admin)
    evento = _evento(db_session, demanda["id"], empresa.id, ator=sistema.id)
    item = _item(client, evento)
    assert item["autorNome"] == "Sistema"
    assert item["categoria"] == "sistema"
    ids_sistema = {i["id"] for i in client.get(NOTIF, params={"categoria": "sistema", "limit": 100}).json()["itens"]}
    ids_minhas = {i["id"] for i in client.get(NOTIF, params={"categoria": "minhas", "limit": 100}).json()["itens"]}
    assert evento.id in ids_sistema and evento.id not in ids_minhas


def test_evento_automatico_continua_como_antes(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, client_admin: TestClient
) -> None:
    _, demanda, client = _setup(app, db_session, empresa, usuario_operador, client_admin)
    evento = _evento(db_session, demanda["id"], empresa.id, ator=None)
    item = _item(client, evento)
    assert item["categoria"] == "sistema"
    assert item["autorNome"] is None  # sem ator: nada de "por …", exatamente como antes


# --------------------------------------------------------------------------------------
# Resumo e leitura
# --------------------------------------------------------------------------------------


def test_resumo_conta_a_conta_de_sistema_em_sistema(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_gestor: Usuario, client_admin: TestClient
) -> None:
    sistema, demanda, client = _setup(app, db_session, empresa, usuario_operador, client_admin)
    antes = client.get(f"{NOTIF}/resumo").json()["naoLidas"]
    _evento(db_session, demanda["id"], empresa.id, ator=sistema.id)  # conta de sistema → sistema
    _evento(db_session, demanda["id"], empresa.id, ator=None)  # automático → sistema
    _evento(db_session, demanda["id"], empresa.id, ator=usuario_gestor.id)  # pessoa → minhas
    depois = client.get(f"{NOTIF}/resumo").json()["naoLidas"]
    assert depois["sistema"] == antes["sistema"] + 2
    assert depois["minhas"] == antes["minhas"] + 1
    assert depois["total"] == antes["total"] + 3


def test_marcar_como_lida_e_todas_preservados(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, client_admin: TestClient
) -> None:
    sistema, demanda, client = _setup(app, db_session, empresa, usuario_operador, client_admin)
    do_sistema = _evento(db_session, demanda["id"], empresa.id, ator=sistema.id)
    outra = _evento(db_session, demanda["id"], empresa.id, ator=sistema.id, tipo="demanda.arquivada")

    resposta = client.post(f"{NOTIF}/{do_sistema.id}/lida")
    assert resposta.status_code == 200, resposta.text
    assert _item(client, do_sistema)["lida"] is True
    assert _item(client, outra)["lida"] is False

    # "marcar todas" por categoria usa a mesma classificação: a categoria "sistema" inclui a conta de sistema
    sem_lidas = client.post(f"{NOTIF}/lidas", json={"categoria": "sistema"})
    assert sem_lidas.status_code == 200, sem_lidas.text
    assert _item(client, outra)["lida"] is True
    assert sem_lidas.json()["naoLidas"]["sistema"] == 0


# --------------------------------------------------------------------------------------
# A própria conta de sistema
# --------------------------------------------------------------------------------------


def test_conta_de_sistema_consulta_normalmente_e_nao_recebe_a_propria_acao(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_gestor: Usuario, client_admin: TestClient
) -> None:
    sistema = _conta_de_sistema(db_session, empresa)
    # Fase 7A: a API não aceita mais conta de sistema como responsável; o vínculo é criado direto no banco só para montar o cenário
    demanda = _demanda(client_admin, [])
    db_session.add(DemandaResponsavel(demanda_id=demanda["id"], usuario_id=sistema.id, created_at=datetime.now(timezone.utc)))
    db_session.flush()
    cliente_sistema = _client_de(app, sistema)
    propria = _evento(db_session, demanda["id"], empresa.id, ator=sistema.id)
    de_pessoa = _evento(db_session, demanda["id"], empresa.id, ator=usuario_gestor.id)
    itens = {i["id"]: i for i in cliente_sistema.get(NOTIF, params={"limit": 100}).json()["itens"]}
    assert propria.id not in itens  # nunca a própria ação (regra existente)
    assert itens[de_pessoa.id]["autorNome"] == usuario_gestor.nome  # pessoas continuam identificadas para ela
    assert cliente_sistema.get(f"{NOTIF}/resumo").status_code == 200
