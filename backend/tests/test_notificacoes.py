"""Central de Notificações: notificações = visão tipada dos eventos das demandas do próprio usuário (+ estado "lida"
por usuário) e "Prazos da equipe" derivado de Demandas no escopo real. Cobre auth, tenant, paginação no servidor,
não lidas, marcar uma/todas, categorias (minhas/sistema), escopo dos prazos e quantidade constante de queries."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.demanda import Demanda
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.notificacao_leitura import NotificacaoLeitura
from app.models.usuario import Usuario
from app.services.notificacao_service import JANELA_DIAS, janelas_prazo

NOTIF = "/notificacoes"


def _client_de(app, usuario: Usuario) -> TestClient:
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)}"
    return cliente


def _usuario(db: Session, empresa: Empresa, perfil: str = "operador") -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"n-{sufixo}", nome=f"Pessoa {sufixo}",
        email=f"n-{sufixo}@teste.local", perfil_base=perfil, acesso_sistema=True, status="ativo",
        is_system_account=False, created_at=agora, updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _demanda(client: TestClient, responsaveis: list[str] | None = None, **extra) -> dict:
    corpo = {"nome": f"Tarefa {uuid.uuid4().hex[:6]}", "usuarioResponsavelIds": responsaveis or [], **extra}
    resposta = client.post("/demandas", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _evento(db: Session, demanda_id: str, empresa_id: str, *, tipo: str = "demanda.status_alterado", ator: str | None = None,
            quando: datetime | None = None, payload: dict | None = None, entidade: str = "demanda") -> Evento:
    quando = quando or datetime.now(timezone.utc)
    evento = Evento(
        id=str(uuid.uuid4()), empresa_id=empresa_id, tipo=tipo, entidade_tipo=entidade, entidade_id=demanda_id, usuario_id=ator,
        payload=payload or {"de": "planejada", "para": "em_execucao"}, occurred_at=quando, created_at=quando,
    )
    db.add(evento)
    db.flush()
    return evento


def _resumo(c: TestClient) -> dict:
    r = c.get(f"{NOTIF}/resumo")
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ auth / vazio
def test_exige_autenticacao(app) -> None:
    anonimo = TestClient(app)
    for chamada in (anonimo.get(NOTIF), anonimo.get(f"{NOTIF}/resumo"), anonimo.post(f"{NOTIF}/lidas"),
                    anonimo.get(f"{NOTIF}/prazos-equipe?grupo=hoje"), anonimo.post(f"{NOTIF}/{uuid.uuid4()}/lida")):
        assert chamada.status_code in (401, 403)


def test_sem_nada_tudo_zerado(client_operador: TestClient) -> None:
    assert _resumo(client_operador) == {"naoLidas": {"sistema": 0, "minhas": 0, "total": 0}, "prazos": {"atrasadas": 0, "hoje": 0, "proximas": 0}}
    assert client_operador.get(NOTIF).json() == {"itens": [], "total": 0, "limit": 50, "offset": 0}


# ------------------------------------------------------------------ o que é uma notificação
def test_atribuicao_notifica_so_quem_foi_atribuido(client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id])
    itens = client_operador.get(NOTIF).json()["itens"]
    atribuicoes = [i for i in itens if i["tipo"] == "demanda.responsavel_adicionado"]
    assert len(atribuicoes) == 1
    n = atribuicoes[0]
    assert n["categoria"] == "minhas" and n["lida"] is False
    assert n["titulo"] == "Você foi atribuído a uma tarefa"
    assert n["demandaId"] == demanda["id"] and n["demandaReferencia"] == demanda["codigoReferencia"] and n["demandaNome"] == demanda["nome"]
    assert n["autorNome"]  # quem atribuiu
    # o autor da ação (admin) nunca recebe a própria notificação
    assert client_admin.get(NOTIF).json()["total"] == 0


def test_a_propria_acao_nunca_notifica(db_session: Session, client_operador: TestClient, usuario_operador: Usuario, client_admin: TestClient) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id])
    antes = client_operador.get(NOTIF).json()["total"]
    _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_operador.id)
    assert client_operador.get(NOTIF).json()["total"] == antes


def test_so_demandas_em_que_sou_responsavel(db_session: Session, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario, usuario_admin: Usuario) -> None:
    alheia = _demanda(client_admin, [])
    _evento(db_session, alheia["id"], usuario_operador.empresa_id, ator=usuario_admin.id)
    assert client_operador.get(NOTIF).json()["total"] == 0


def test_categorias_minhas_e_sistema(db_session: Session, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario, usuario_admin: Usuario) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id])
    _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=None)  # sem ator humano = sistema
    _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_admin.id, tipo="demanda.bloqueada", payload={"motivoBloqueio": "Aguardando cliente"})
    sistema = client_operador.get(f"{NOTIF}?categoria=sistema").json()
    minhas = client_operador.get(f"{NOTIF}?categoria=minhas").json()
    assert sistema["total"] == 1 and sistema["itens"][0]["categoria"] == "sistema" and sistema["itens"][0]["autorNome"] is None
    assert {i["tipo"] for i in minhas["itens"]} == {"demanda.responsavel_adicionado", "demanda.bloqueada"}
    assert next(i for i in minhas["itens"] if i["tipo"] == "demanda.bloqueada")["detalhe"] == "Aguardando cliente"
    assert client_operador.get(f"{NOTIF}?categoria=invalida").status_code == 422
    r = _resumo(client_operador)["naoLidas"]
    assert r == {"sistema": 1, "minhas": 2, "total": 3}


def test_detalhe_da_mudanca_de_status_usa_os_rotulos_da_interface(db_session: Session, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario, usuario_admin: Usuario) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id])
    _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_admin.id, payload={"de": "planejada", "para": "em_execucao"})
    status = next(i for i in client_operador.get(NOTIF).json()["itens"] if i["tipo"] == "demanda.status_alterado")
    assert status["detalhe"] == "Planejada → Em execução"


def test_tipos_fora_do_catalogo_e_janela_de_30_dias(db_session: Session, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario, usuario_admin: Usuario) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id])
    base = client_operador.get(NOTIF).json()["total"]
    _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_admin.id, tipo="demanda.alterada")  # ruído: fora do catálogo
    _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_admin.id, tipo="auth.login_sucesso", entidade="auth")
    _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_admin.id, quando=datetime.now(timezone.utc) - timedelta(days=JANELA_DIAS + 1))
    assert client_operador.get(NOTIF).json()["total"] == base


# ------------------------------------------------------------------ paginação no servidor (> 200)
def test_paginacao_no_servidor_sem_repeticao(db_session: Session, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario, usuario_admin: Usuario) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id])
    agora = datetime.now(timezone.utc)
    for i in range(230):
        _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_admin.id, quando=agora - timedelta(seconds=i + 1))
    total = client_operador.get(NOTIF).json()["total"]
    assert total >= 231
    vistos: list[str] = []
    for offset in range(0, total, 50):
        pagina = client_operador.get(f"{NOTIF}?limit=50&offset={offset}").json()
        assert pagina["limit"] == 50 and pagina["offset"] == offset and pagina["total"] == total
        assert len(pagina["itens"]) <= 50
        vistos += [i["id"] for i in pagina["itens"]]
    assert len(vistos) == total and len(set(vistos)) == total
    datas = [i["ocorridaEm"] for i in client_operador.get(f"{NOTIF}?limit=100").json()["itens"]]
    assert datas == sorted(datas, reverse=True)
    assert client_operador.get(f"{NOTIF}?limit=101").status_code == 422  # sem "carregar tudo"
    assert client_operador.get(f"{NOTIF}?limit=0").status_code == 422


def test_quantidade_de_queries_nao_cresce_com_a_pagina(db_session: Session, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario, usuario_admin: Usuario) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id])
    agora = datetime.now(timezone.utc)
    contagem = {"n": 0}

    def contar(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        contagem["n"] += 1

    def medir(limit: int) -> int:
        contagem["n"] = 0
        event.listen(db_session.get_bind(), "before_cursor_execute", contar)
        try:
            assert client_operador.get(f"{NOTIF}?limit={limit}").status_code == 200
        finally:
            event.remove(db_session.get_bind(), "before_cursor_execute", contar)
        return contagem["n"]

    for i in range(5):
        _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_admin.id, quando=agora - timedelta(seconds=i + 1))
    medir(100)  # aquecimento (primeira chamada carrega o usuário/permissões na sessão)
    com_poucos = medir(100)
    for i in range(80):
        _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_admin.id, quando=agora - timedelta(minutes=i + 1))
    assert medir(100) == com_poucos, "N+1: queries crescem com a quantidade de itens"


# ------------------------------------------------------------------ lidas
def test_marcar_uma_como_lida_e_idempotente(client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario) -> None:
    _demanda(client_admin, [usuario_operador.id])
    _demanda(client_admin, [usuario_operador.id])
    antes = _resumo(client_operador)["naoLidas"]["total"]
    assert antes == 2
    primeiro = client_operador.get(NOTIF).json()["itens"][0]["id"]
    r = client_operador.post(f"{NOTIF}/{primeiro}/lida")
    assert r.status_code == 200 and r.json()["naoLidas"]["total"] == 1
    assert client_operador.post(f"{NOTIF}/{primeiro}/lida").json()["naoLidas"]["total"] == 1  # idempotente
    lista = client_operador.get(NOTIF).json()["itens"]
    assert next(i for i in lista if i["id"] == primeiro)["lida"] is True
    nao_lidas = client_operador.get(f"{NOTIF}?apenasNaoLidas=true").json()
    assert nao_lidas["total"] == 1 and all(not i["lida"] for i in nao_lidas["itens"])


def test_marcar_todas_por_categoria_e_geral(db_session: Session, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id])
    _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=None)
    assert _resumo(client_operador)["naoLidas"] == {"sistema": 1, "minhas": 1, "total": 2}
    r = client_operador.post(f"{NOTIF}/lidas", json={"categoria": "sistema"})
    assert r.json()["naoLidas"] == {"sistema": 0, "minhas": 1, "total": 1}
    r = client_operador.post(f"{NOTIF}/lidas")  # sem corpo = todas
    assert r.json()["naoLidas"]["total"] == 0
    assert client_operador.post(f"{NOTIF}/lidas", json={"categoria": "x"}).status_code == 422
    assert client_operador.post(f"{NOTIF}/lidas", json={"outro": 1}).status_code == 422
    assert client_operador.get(f"{NOTIF}?apenasNaoLidas=true").json()["total"] == 0


def test_marcar_todas_lidas_em_massa_e_um_insert(db_session: Session, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario, usuario_admin: Usuario) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id])
    agora = datetime.now(timezone.utc)
    for i in range(250):
        _evento(db_session, demanda["id"], usuario_operador.empresa_id, ator=usuario_admin.id, quando=agora - timedelta(seconds=i + 1))
    instrucoes: list[str] = []

    def capturar(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        if "notificacao_leituras" in statement and statement.lstrip().upper().startswith("INSERT"):
            instrucoes.append(statement)

    event.listen(db_session.get_bind(), "before_cursor_execute", capturar)
    try:
        assert client_operador.post(f"{NOTIF}/lidas").json()["naoLidas"]["total"] == 0
    finally:
        event.remove(db_session.get_bind(), "before_cursor_execute", capturar)
    assert len(instrucoes) == 1
    assert len(db_session.scalars(select(NotificacaoLeitura).where(NotificacaoLeitura.usuario_id == usuario_operador.id)).all()) >= 251


def test_leitura_e_por_usuario(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b = _usuario(db_session, empresa), _usuario(db_session, empresa)
    ca, cb = _client_de(app, a), _client_de(app, b)
    _demanda(client_admin, [a.id, b.id])
    evento = ca.get(NOTIF).json()["itens"][0]["id"]
    ca.post(f"{NOTIF}/{evento}/lida")
    assert _resumo(ca)["naoLidas"]["total"] == 0
    assert _resumo(cb)["naoLidas"]["total"] == 1, "a leitura de um não marca a do outro"


def test_nao_marca_notificacao_de_outro_usuario_nem_de_outra_empresa(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario) -> None:
    alheia = _demanda(client_admin, [])
    ev_alheio = _evento(db_session, alheia["id"], empresa.id, ator=None)
    assert client_operador.post(f"{NOTIF}/{ev_alheio.id}/lida").status_code == 404  # existe, mas não é dele
    assert client_operador.post(f"{NOTIF}/{uuid.uuid4()}/lida").status_code == 404  # nem existe: mesma resposta
    estranho = _client_de(app, _usuario(db_session, outra_empresa))
    _demanda(client_admin, [usuario_operador.id])
    id_dele = client_operador.get(NOTIF).json()["itens"][0]["id"]
    assert estranho.post(f"{NOTIF}/{id_dele}/lida").status_code == 404
    assert estranho.get(NOTIF).json()["total"] == 0  # tenant isolado
    assert db_session.scalars(select(NotificacaoLeitura)).all() == []


# ------------------------------------------------------------------ prazos da equipe
def _prazos(c: TestClient, grupo: str, **q) -> dict:
    r = c.get(f"{NOTIF}/prazos-equipe", params={"grupo": grupo, **q})
    assert r.status_code == 200, r.text
    return r.json()


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).isoformat()


def _com_prazos(client_admin: TestClient, responsavel: str | None):
    agora, fim_hoje, _ = janelas_prazo()
    resp = [responsavel] if responsavel else []
    return {
        "atrasada": _demanda(client_admin, resp, prazoEtapaAtual=_iso(agora - timedelta(days=2))),
        "hoje": _demanda(client_admin, resp, prazoEtapaAtual=_iso(max(agora + timedelta(seconds=30), fim_hoje - timedelta(seconds=1)))),
        "proxima": _demanda(client_admin, resp, prazoEtapaAtual=_iso(fim_hoje + timedelta(days=3))),
        "longe": _demanda(client_admin, resp, prazoEtapaAtual=_iso(fim_hoje + timedelta(days=30))),
        "sem_prazo": _demanda(client_admin, resp),
    }


def test_grupos_de_prazo_atrasada_hoje_proximas(client_admin: TestClient) -> None:
    d = _com_prazos(client_admin, None)
    assert [i["id"] for i in _prazos(client_admin, "atrasadas")["itens"]] == [d["atrasada"]["id"]]
    assert [i["id"] for i in _prazos(client_admin, "hoje")["itens"]] == [d["hoje"]["id"]]
    assert [i["id"] for i in _prazos(client_admin, "proximas")["itens"]] == [d["proxima"]["id"]]
    assert _resumo(client_admin)["prazos"] == {"atrasadas": 1, "hoje": 1, "proximas": 1}


def test_concluida_cancelada_e_arquivada_nao_aparecem(db_session: Session, client_admin: TestClient) -> None:
    d = _com_prazos(client_admin, None)
    for chave, status in (("atrasada", "concluida"), ("hoje", "cancelada"), ("proxima", "arquivada")):
        db_session.get(Demanda, d[chave]["id"]).status = status
    db_session.flush()
    assert _resumo(client_admin)["prazos"] == {"atrasadas": 0, "hoje": 0, "proximas": 0}
    for grupo in ("atrasadas", "hoje", "proximas"):
        assert _prazos(client_admin, grupo)["itens"] == []


def test_conteudo_do_item_de_prazo(client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin, [usuario_operador.id], prazoEtapaAtual=_iso(datetime.now(timezone.utc) - timedelta(days=1)), prioridade="alta")
    item = _prazos(client_admin, "atrasadas")["itens"][0]
    assert item["id"] == demanda["id"] and item["codigoReferencia"] and item["nome"] == demanda["nome"]
    assert item["prazoEtapaAtual"] and item["status"] and item["prioridade"] == "alta"
    assert item["usuarioResponsavelIds"] == [usuario_operador.id]


def test_operador_so_ve_prazos_do_proprio_escopo(app, db_session: Session, empresa: Empresa, client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario) -> None:
    outro = _usuario(db_session, empresa)
    minhas = _com_prazos(client_admin, usuario_operador.id)
    _com_prazos(client_admin, outro.id)  # de outra pessoa: o operador NÃO ganha acesso por existir a página
    assert _resumo(client_operador)["prazos"] == {"atrasadas": 1, "hoje": 1, "proximas": 1}
    assert {i["id"] for i in _prazos(client_operador, "atrasadas")["itens"]} == {minhas["atrasada"]["id"]}
    # admin (visão total) enxerga as duas equipes
    assert _resumo(client_admin)["prazos"] == {"atrasadas": 2, "hoje": 2, "proximas": 2}
    assert len(_prazos(client_admin, "atrasadas")["itens"]) == 2


def test_prazos_isolados_por_empresa(app, db_session: Session, outra_empresa: Empresa, client_admin: TestClient) -> None:
    _com_prazos(client_admin, None)
    estranho = _client_de(app, _usuario(db_session, outra_empresa, "admin"))
    assert _resumo(estranho)["prazos"] == {"atrasadas": 0, "hoje": 0, "proximas": 0}
    assert _prazos(estranho, "atrasadas") == {"itens": [], "total": 0, "limit": 50, "offset": 0}


def test_prazos_paginados_no_servidor(client_admin: TestClient) -> None:
    agora = datetime.now(timezone.utc)
    for i in range(7):
        _demanda(client_admin, [], prazoEtapaAtual=_iso(agora - timedelta(hours=i + 1)))
    p1, p2 = _prazos(client_admin, "atrasadas", limit=3, offset=0), _prazos(client_admin, "atrasadas", limit=3, offset=3)
    assert p1["total"] == p2["total"] == 7 and len(p1["itens"]) == 3 and len(p2["itens"]) == 3
    assert not {i["id"] for i in p1["itens"]} & {i["id"] for i in p2["itens"]}
    datas = [i["prazoEtapaAtual"] for i in p1["itens"] + p2["itens"]]
    assert datas == sorted(datas), "mais atrasadas primeiro (prazo crescente)"
    assert client_admin.get(f"{NOTIF}/prazos-equipe?grupo=hoje&limit=101").status_code == 422
    assert client_admin.get(f"{NOTIF}/prazos-equipe?grupo=nada").status_code == 422


def test_prazos_quantidade_de_queries_constante(db_session: Session, client_admin: TestClient) -> None:
    agora = datetime.now(timezone.utc)
    contagem = {"n": 0}

    def contar(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        contagem["n"] += 1

    def medir() -> int:
        contagem["n"] = 0
        event.listen(db_session.get_bind(), "before_cursor_execute", contar)
        try:
            assert client_admin.get(f"{NOTIF}/prazos-equipe?grupo=atrasadas&limit=100").status_code == 200
        finally:
            event.remove(db_session.get_bind(), "before_cursor_execute", contar)
        return contagem["n"]

    for i in range(3):
        _demanda(client_admin, [], prazoEtapaAtual=_iso(agora - timedelta(hours=i + 1)))
    medir()  # aquecimento
    poucos = medir()
    for i in range(25):
        _demanda(client_admin, [], prazoEtapaAtual=_iso(agora - timedelta(days=i + 1)))
    medios = medir()
    for i in range(60):
        _demanda(client_admin, [], prazoEtapaAtual=_iso(agora - timedelta(days=100 + i)))
    muitos = medir()
    # (poucos → medios pode subir um degrau fixo, quando passam a existir etapas/relacionamentos; de 28 para
    # 88 itens o número de queries NÃO cresce — a página inteira é montada em lote, sem N+1)
    assert medios == muitos
    assert muitos - poucos <= 3
