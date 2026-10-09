"""D2-D3C3 — `GET /sessoes-trabalho/trafego/agora`: "Quem está trabalhando agora" paginado no
servidor, com usuário/departamento/Demanda já resolvidos, sem o cap de 100 da listagem.

Reaproveita as fixtures de `test_trafego_carga` (relógio-base = `NOW()` da transação, então os
tempos são exatos) e porta `filterSessoes` + a ordenação da tabela para provar paridade.
"""

from __future__ import annotations

import math
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from tests.helpers.api import get
from tests.test_trafego_carga import _agora_db, _departamento, _sessao, _usuario


def _url(**params: str | int | None) -> str:
    consulta = {chave: valor for chave, valor in params.items() if valor is not None}
    return "/sessoes-trabalho/trafego/agora" + (f"?{urlencode(consulta)}" if consulta else "")


def _agora(app, token: str, **params: str | int | None) -> dict:
    resposta = get(TestClient(app), _url(**params), token=token)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _ids(corpo: dict) -> list[str]:
    return [item["sessaoId"] for item in corpo["items"]]


# --------------------------------------------------------------------------------------
# RBAC / tenant / validação
# --------------------------------------------------------------------------------------

def test_admin_e_gestor_acessam(app, token_admin: str, token_gestor: str) -> None:
    assert get(TestClient(app), _url(), token=token_admin).status_code == 200
    assert get(TestClient(app), _url(), token=token_gestor).status_code == 200


def test_operador_e_403(app, token_operador: str) -> None:
    assert get(TestClient(app), _url(), token=token_operador).status_code == 403


def test_sem_token_e_401(app) -> None:
    assert get(TestClient(app), _url()).status_code == 401


def test_tenant_isolado(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, token_admin: str) -> None:
    alheio = _usuario(db_session, outra_empresa)
    _sessao(db_session, outra_empresa, decorrido=500, usuario=alheio)
    corpo = _agora(app, token_admin)
    assert corpo["items"] == [] and corpo["total"] == 0


@pytest.mark.parametrize("parametros", [{"limit": 0}, {"limit": 201}, {"offset": -1}])
def test_paginacao_invalida_e_422(app, token_admin: str, parametros: dict) -> None:
    assert get(TestClient(app), _url(**parametros), token=token_admin).status_code == 422


def test_ids_invalidos_sao_422(app, token_admin: str) -> None:
    assert get(TestClient(app), _url(usuarioIds="nao-uuid"), token=token_admin).status_code == 422
    assert get(TestClient(app), _url(departamentoIds="x"), token=token_admin).status_code == 422


# --------------------------------------------------------------------------------------
# Universo e conteúdo
# --------------------------------------------------------------------------------------

def test_vazio(app, token_admin: str) -> None:
    assert _agora(app, token_admin) == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_uma_ativa_traz_tudo_resolvido(app, db_session: Session, empresa: Empresa, token_admin: str, client_admin: TestClient) -> None:
    demanda = client_admin.post("/demandas", json={"nome": "Campanha de Verão"}).json()
    usuario, depto = _usuario(db_session, empresa, "Ana Souza"), _departamento(db_session, empresa, "Criação")
    sessao = _sessao(db_session, empresa, decorrido=125, usuario=usuario, departamento=depto, demanda_id=demanda["id"])

    corpo = _agora(app, token_admin)
    assert corpo["total"] == 1
    item = corpo["items"][0]
    assert item["sessaoId"] == sessao.id
    assert item["decorridoSegundos"] == 125
    assert item["demandaId"] == demanda["id"]
    assert (item["demandaNumero"], item["demandaNome"]) == (demanda["numeroOperacional"], "Campanha de Verão")
    assert (item["usuarioId"], item["usuarioNome"]) == (usuario.id, "Ana Souza")
    assert (item["departamentoId"], item["departamentoNome"]) == (depto.id, "Criação")
    assert datetime.fromisoformat(item["inicioEm"].replace("Z", "+00:00")) == sessao.inicio_em
    assert set(item) == {
        "sessaoId", "inicioEm", "decorridoSegundos", "demandaId", "demandaNumero", "demandaIdentificador", "demandaNome",
        "usuarioId", "usuarioNome", "departamentoId", "departamentoNome",
    }


def test_so_ativas_aparecem(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    usuario = _usuario(db_session, empresa)
    ativa = _sessao(db_session, empresa, decorrido=10, usuario=usuario)
    _sessao(db_session, empresa, status="encerrada", usuario=usuario)
    _sessao(db_session, empresa, status="cancelada", usuario=usuario)
    corpo = _agora(app, token_admin)
    assert _ids(corpo) == [ativa.id] and corpo["total"] == 1


def test_status_e_periodo_da_tela_nao_afetam_a_tabela(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, decorrido=10, usuario=_usuario(db_session, empresa))
    base = _agora(app, token_admin)
    assert _agora(app, token_admin, status="encerrada", periodoInicio="2030-01-01T00:00:00Z") == base


def test_sessao_antiga_aparece_sem_filtro_de_periodo(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    antiga = _sessao(db_session, empresa, decorrido=5 * 24 * 3600, usuario=_usuario(db_session, empresa))
    assert _agora(app, token_admin)["items"][0]["sessaoId"] == antiga.id


# --------------------------------------------------------------------------------------
# NULLs e vínculos ausentes
# --------------------------------------------------------------------------------------

def test_sessao_sem_usuario_nem_departamento(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, decorrido=30)
    item = _agora(app, token_admin)["items"][0]
    assert item["usuarioId"] is None and item["usuarioNome"] is None
    assert item["departamentoId"] is None and item["departamentoNome"] is None


def test_demanda_inexistente_mantem_o_id_e_nao_traz_nome(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    demanda_id = str(uuid.uuid4())
    _sessao(db_session, empresa, decorrido=30, usuario=_usuario(db_session, empresa), demanda_id=demanda_id)
    item = _agora(app, token_admin)["items"][0]
    assert item["demandaId"] == demanda_id
    assert item["demandaNumero"] is None and item["demandaNome"] is None


def test_usuario_inativo_continua_com_nome(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, decorrido=30, usuario=_usuario(db_session, empresa, "Ex Colaborador", status="inativo"))
    assert _agora(app, token_admin)["items"][0]["usuarioNome"] == "Ex Colaborador"


# --------------------------------------------------------------------------------------
# Ordenação
# --------------------------------------------------------------------------------------

def test_ordem_maior_tempo_em_execucao_primeiro(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    ids = {
        valor: _sessao(db_session, empresa, decorrido=valor, usuario=_usuario(db_session, empresa)).id
        for valor in (100, 5000, 900, 30)
    }
    corpo = _agora(app, token_admin)
    assert _ids(corpo) == [ids[5000], ids[900], ids[100], ids[30]]
    assert [i["decorridoSegundos"] for i in corpo["items"]] == [5000, 900, 100, 30]


def test_empate_created_at_desc_depois_id(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """Mesmo início: a ordem que a API entregava ao cliente (`created_at DESC`) e, em último
    caso, o id — determinístico entre execuções."""
    inicio = _agora_db(db_session) - timedelta(seconds=300)
    cedo = datetime(2026, 1, 1, tzinfo=timezone.utc)
    antigo = _sessao(db_session, empresa, inicio_em=inicio, created_at=cedo, usuario=_usuario(db_session, empresa))
    novo = _sessao(db_session, empresa, inicio_em=inicio, created_at=cedo + timedelta(hours=1), usuario=_usuario(db_session, empresa))
    assert _ids(_agora(app, token_admin)) == [novo.id, antigo.id]

    a = _sessao(db_session, empresa, inicio_em=inicio - timedelta(days=1), created_at=cedo, usuario=_usuario(db_session, empresa))
    b = _sessao(db_session, empresa, inicio_em=inicio - timedelta(days=1), created_at=cedo, usuario=_usuario(db_session, empresa))
    primeiro_par = _ids(_agora(app, token_admin))[:2]
    assert primeiro_par == sorted([a.id, b.id])
    assert _ids(_agora(app, token_admin)) == _ids(_agora(app, token_admin))


# --------------------------------------------------------------------------------------
# Filtros (mesmos de D3C1/D3C2)
# --------------------------------------------------------------------------------------

def test_filtros_usuario_departamento_e_combinacao(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    u1, u2 = _usuario(db_session, empresa, "Um"), _usuario(db_session, empresa, "Dois")
    d1, d2 = _departamento(db_session, empresa, "D1"), _departamento(db_session, empresa, "D2")
    s11 = _sessao(db_session, empresa, decorrido=400, usuario=u1, departamento=d1)
    s12 = _sessao(db_session, empresa, decorrido=300, usuario=u1, departamento=d2)
    s21 = _sessao(db_session, empresa, decorrido=200, usuario=u2, departamento=d1)
    _sessao(db_session, empresa, decorrido=100)  # sem vínculo: nunca casa com filtro ativo

    assert _ids(_agora(app, token_admin, usuarioIds=u1.id)) == [s11.id, s12.id]
    assert _ids(_agora(app, token_admin, departamentoIds=d1.id)) == [s11.id, s21.id]
    assert _ids(_agora(app, token_admin, usuarioIds=f"{u1.id},{u2.id}", departamentoIds=d1.id)) == [s11.id, s21.id]
    combinado = _agora(app, token_admin, usuarioIds=u1.id, departamentoIds=d2.id)
    assert _ids(combinado) == [s12.id] and combinado["total"] == 1


def test_filtro_de_demanda_com_acento_caixa_e_numero(app, db_session: Session, empresa: Empresa, token_admin: str, client_admin: TestClient) -> None:
    demanda = client_admin.post("/demandas", json={"nome": "Relatório Ação Social"}).json()
    casa = _sessao(db_session, empresa, decorrido=50, usuario=_usuario(db_session, empresa), demanda_id=demanda["id"])
    _sessao(db_session, empresa, decorrido=900, usuario=_usuario(db_session, empresa))

    assert _ids(_agora(app, token_admin, demandaQuery="ACAO social")) == [casa.id]
    assert _ids(_agora(app, token_admin, demandaQuery=f"#{demanda['numeroOperacional']}")) == [casa.id]
    assert _agora(app, token_admin, demandaQuery="inexistente-zzz")["total"] == 0
    assert _agora(app, token_admin, demandaQuery="   ")["total"] == 2  # só espaços = sem filtro
    # a consulta não é aparada (D3C1): "acao " (com espaço) casa "ação social", "social " (espaço no fim) não
    assert _agora(app, token_admin, demandaQuery="acao ")["total"] == 1
    assert _agora(app, token_admin, demandaQuery="social ")["total"] == 0


# --------------------------------------------------------------------------------------
# Paginação e dataset > 100
# --------------------------------------------------------------------------------------

def _criar_150(db_session: Session, empresa: Empresa) -> list[str]:
    """150 ativas com tempos distintos (1000s … 1149s): ordem global conhecida (maior primeiro)."""
    usuario = _usuario(db_session, empresa, "Muitas Sessões")
    criadas = [(1000 + i, _sessao(db_session, empresa, decorrido=1000 + i, usuario=usuario).id) for i in range(150)]
    return [sessao_id for _, sessao_id in sorted(criadas, reverse=True)]


def test_150_sessoes_em_tres_paginas_sem_perder_nem_repetir(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    esperado = _criar_150(db_session, empresa)

    p1 = _agora(app, token_admin, limit=50, offset=0)
    p2 = _agora(app, token_admin, limit=50, offset=50)
    p3 = _agora(app, token_admin, limit=50, offset=100)
    p4 = _agora(app, token_admin, limit=50, offset=150)

    assert [p["total"] for p in (p1, p2, p3, p4)] == [150, 150, 150, 150]
    assert [len(p["items"]) for p in (p1, p2, p3)] == [50, 50, 50]
    assert p4["items"] == []
    assert _ids(p1) + _ids(p2) + _ids(p3) == esperado  # nenhuma perdida, nenhuma repetida, ordem global
    assert (p1["limit"], p1["offset"], p3["offset"]) == (50, 0, 100)


def test_pagina_unica_grande_e_default(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    esperado = _criar_150(db_session, empresa)
    assert _ids(_agora(app, token_admin, limit=200)) == esperado
    padrao = _agora(app, token_admin)
    assert len(padrao["items"]) == 50 and padrao["total"] == 150 and padrao["limit"] == 50


def test_filtro_atinge_sessoes_alem_do_antigo_cap_de_100(
    app, db_session: Session, empresa: Empresa, token_admin: str, client_admin: TestClient
) -> None:
    """A listagem antiga (`GET /sessoes-trabalho?status=ativa&limit=100`) entregava só as 100 mais
    RECENTES; filtrar no cliente não alcançava nada além delas. Aqui as 20 sessões do alvo são as
    mais ANTIGAS (posições 131–150 por recência): a lista antiga não contém nenhuma, e o endpoint
    novo as devolve todas — o filtro opera sobre o universo completo, não sobre uma página."""
    alvo = _usuario(db_session, empresa, "Alvo Antigo")
    outro = _usuario(db_session, empresa, "Outro")
    ids_alvo = {_sessao(db_session, empresa, decorrido=100_000 + i, usuario=alvo).id for i in range(20)}  # as mais antigas
    for i in range(130):
        _sessao(db_session, empresa, decorrido=10 + i, usuario=outro)

    antiga = client_admin.get("/sessoes-trabalho", params={"status": "ativa", "limit": 100}).json()
    assert len(antiga) == 100
    assert not (ids_alvo & {s["id"] for s in antiga}), "pré-condição: o alvo está fora do cap antigo"

    corpo = _agora(app, token_admin, usuarioIds=alvo.id, limit=50)
    assert corpo["total"] == 20
    assert set(_ids(corpo)) == ids_alvo


def test_filtro_de_demanda_alem_do_antigo_cap(app, db_session: Session, empresa: Empresa, token_admin: str, client_admin: TestClient) -> None:
    demanda = client_admin.post("/demandas", json={"nome": "Demanda Escondida XYZ"}).json()
    escondidas = {
        _sessao(db_session, empresa, decorrido=200_000 + i, usuario=_usuario(db_session, empresa), demanda_id=demanda["id"]).id
        for i in range(3)
    }
    for i in range(120):
        _sessao(db_session, empresa, decorrido=10 + i, usuario=_usuario(db_session, empresa))

    antiga = client_admin.get("/sessoes-trabalho", params={"status": "ativa", "limit": 100}).json()
    assert not (escondidas & {s["id"] for s in antiga})
    corpo = _agora(app, token_admin, demandaQuery="escondida xyz")
    assert set(_ids(corpo)) == escondidas and corpo["total"] == 3


# --------------------------------------------------------------------------------------
# Autossuficiência — nome sem depender do diretório do cliente
# --------------------------------------------------------------------------------------

def test_usuario_fora_do_antigo_diretorio_de_200_vem_com_nome(
    app, db_session: Session, empresa: Empresa, token_admin: str, client_admin: TestClient
) -> None:
    """O cliente resolvia o nome no diretório de usuários (`limit=200`) e, fora dele, mostrava o
    UUID. Com 210 usuários, o último não cabe no diretório antigo — e a linha traz o nome."""
    usuarios = [_usuario(db_session, empresa, f"Usuário {i:03d}") for i in range(210)]
    ultimo = usuarios[-1]
    _sessao(db_session, empresa, decorrido=42, usuario=ultimo)

    diretorio = client_admin.get("/usuarios/diretorio", params={"limit": 200}).json()
    assert ultimo.id not in {u["id"] for u in diretorio}, "pré-condição: fora do diretório de 200"

    item = _agora(app, token_admin)["items"][0]
    assert item["usuarioId"] == ultimo.id
    assert item["usuarioNome"] == "Usuário 209" != item["usuarioId"]


# --------------------------------------------------------------------------------------
# Performance — nº de consultas constante
# --------------------------------------------------------------------------------------

def _consultas_a_sessoes(app, db_session: Session, token: str) -> int:
    chamadas: list[str] = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "sessoes_trabalho" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = get(TestClient(app), _url(), token=token)
    finally:
        event.remove(engine, "before_cursor_execute", _contar)
    assert resposta.status_code == 200, resposta.text
    return len(chamadas)


def test_numero_de_consultas_constante_com_1_ou_150_sessoes(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, decorrido=10, usuario=_usuario(db_session, empresa), departamento=_departamento(db_session, empresa))
    com_uma = _consultas_a_sessoes(app, db_session, token_admin)
    for i in range(149):
        _sessao(db_session, empresa, decorrido=20 + i, usuario=_usuario(db_session, empresa), departamento=_departamento(db_session, empresa))
    com_muitas = _consultas_a_sessoes(app, db_session, token_admin)
    assert com_uma == com_muitas == 2  # página + total, sem N+1 de demanda/usuário/departamento


# --------------------------------------------------------------------------------------
# PARIDADE com `filterSessoes` + ordenação da tabela
# --------------------------------------------------------------------------------------

def _normalizar_cliente(valor: str) -> str:
    decomposto = unicodedata.normalize("NFD", valor.lower())
    return "".join(c for c in decomposto if not 0x300 <= ord(c) <= 0x36F)


def _ordem_do_cliente(registros: list[dict], filtros: dict) -> list[str]:
    """Ativas na ordem da API (`inicio_em DESC, created_at DESC`) → `filterSessoes` → sort ESTÁVEL por
    tempo decorrido decrescente (`TrafegoAgoraTable.ordenadas`)."""
    ativas = sorted((r for r in registros if r["status"] == "ativa"), key=lambda r: (r["inicio"], r["created"]), reverse=True)

    def passa(r: dict) -> bool:
        usuario_ok = not filtros["usuarios"] or (r["usuario"] is not None and r["usuario"] in filtros["usuarios"])
        depto_ok = not filtros["departamentos"] or (r["departamento"] is not None and r["departamento"] in filtros["departamentos"])
        consulta = filtros["demanda_query"]
        demanda_ok = True
        if consulta.strip():
            nome = f"#{r['numero']} — {r['nome']}" if r["numero"] is not None else r["demanda"]
            demanda_ok = _normalizar_cliente(consulta) in _normalizar_cliente(f"{r['demanda']} {nome}")
        return usuario_ok and depto_ok and demanda_ok

    filtradas = [r for r in ativas if passa(r)]
    return [r["id"] for r in sorted(filtradas, key=lambda r: -r["decorrido"])]


def test_paridade_com_a_tabela_atual(
    app, db_session: Session, empresa: Empresa, token_admin: str, client_admin: TestClient
) -> None:
    usuarios = [_usuario(db_session, empresa, f"Pessoa {i}") for i in range(4)]
    deptos = [_departamento(db_session, empresa, f"Setor {i}") for i in range(3)]
    demandas = [client_admin.post("/demandas", json={"nome": n}).json() for n in ("Banner Verão", "Relatório Ação", "Vídeo")]
    agora_db = _agora_db(db_session)
    base_criacao = datetime(2026, 1, 1, tzinfo=timezone.utc)

    plano = [  # (decorrido, usuário, depto, demanda, status)
        (900, 0, 0, 0, "ativa"), (900, 1, 1, 1, "ativa"), (300, 0, 1, 1, "ativa"), (1200, 1, 0, 2, "ativa"),
        (50, 2, None, None, "ativa"), (700, 3, 2, 0, "ativa"), (700, None, 0, 1, "ativa"), (10, 2, 2, 2, "ativa"),
        (2000, None, None, None, "ativa"), (400, 3, None, 1, "ativa"), (123, 0, 2, None, "ativa"),
        (500, 0, 0, 0, "encerrada"), (777, 2, 2, 1, "cancelada"),
    ]
    registros: list[dict] = []
    for i, (decorrido, u, d, dem, status) in enumerate(plano):
        demanda_id = demandas[dem]["id"] if dem is not None else str(uuid.uuid4())
        criada = base_criacao + timedelta(minutes=i)
        sessao = _sessao(
            db_session, empresa, status=status, decorrido=decorrido,
            usuario=usuarios[u] if u is not None else None, departamento=deptos[d] if d is not None else None,
            demanda_id=demanda_id, created_at=criada,
        )
        registros.append({
            "id": sessao.id, "status": status, "decorrido": decorrido, "inicio": agora_db - timedelta(seconds=decorrido),
            "created": criada, "usuario": usuarios[u].id if u is not None else None,
            "departamento": deptos[d].id if d is not None else None, "demanda": demanda_id,
            "numero": demandas[dem]["numeroOperacional"] if dem is not None else None,
            "nome": demandas[dem]["nome"] if dem is not None else None,
        })

    casos = [
        {"usuarios": [], "departamentos": [], "demanda_query": ""},
        {"usuarios": [usuarios[0].id], "departamentos": [], "demanda_query": ""},
        {"usuarios": [usuarios[1].id, usuarios[3].id], "departamentos": [], "demanda_query": ""},
        {"usuarios": [], "departamentos": [deptos[0].id], "demanda_query": ""},
        {"usuarios": [], "departamentos": [deptos[1].id, deptos[2].id], "demanda_query": ""},
        {"usuarios": [], "departamentos": [], "demanda_query": "acao"},
        {"usuarios": [], "departamentos": [], "demanda_query": f"#{demandas[0]['numeroOperacional']}"},
        {"usuarios": [usuarios[0].id, usuarios[3].id], "departamentos": [deptos[0].id, deptos[2].id], "demanda_query": "banner"},
        {"usuarios": [], "departamentos": [], "demanda_query": "nada-casa"},
    ]
    for caso in casos:
        servidor = _agora(
            app, token_admin, limit=200,
            usuarioIds=",".join(caso["usuarios"]) or None,
            departamentoIds=",".join(caso["departamentos"]) or None,
            demandaQuery=caso["demanda_query"] or None,
        )
        assert _ids(servidor) == _ordem_do_cliente(registros, caso), f"ordem/conteúdo divergiu em {caso}"
        assert servidor["total"] == len(servidor["items"])
