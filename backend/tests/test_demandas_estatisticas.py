"""`GET /demandas/estatisticas` — os cards de `DemandasStats` (tela Tarefas) agregados no servidor.

Antes, `DemandasStats` contava no navegador sobre `AppDataContext.demandas`
(`GET /demandas?limit=200`, as 200 mais recentes do ESCOPO de quem pede, sem arquivadas). Aqui os
números saem de SQL sobre o universo integral do mesmo escopo. Há paridade com a lógica antiga
portada (`DemandasStats.tsx`), prova de escopo (contra a própria listagem) e dataset de >200
Demandas em que a conta antiga dá um valor comprovadamente diferente.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.helpers.api import get
from tests.test_relatorios_projeto import BASE, _demanda

URL = "/demandas/estatisticas"
STATUS_TODOS = (
    "rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente", "concluida", "cancelada", "arquivada",
)
ZERO = {"total": 0, "emExecucao": 0, "pausadasOuBloqueadas": 0, "aguardandoCliente": 0, "concluidas": 0}


def _estatisticas(client: TestClient, **params: str) -> dict:
    resposta = client.get(URL, params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _listar_tudo(client: TestClient) -> list[dict]:
    """Todas as Demandas que a LISTAGEM da tela devolve para quem pede, página a página."""
    itens: list[dict] = []
    offset = 0
    while True:
        pagina = client.get("/demandas", params={"limit": 200, "offset": offset}).json()
        itens.extend(pagina)
        if len(pagina) < 200:
            return itens
        offset += 200


def _stats_antigo(demandas: list[dict]) -> dict:
    """Porte de `DemandasStats.tsx` (pré-migração): conta sobre o array que recebia."""
    return {
        "total": len(demandas),
        "emExecucao": sum(1 for d in demandas if d["status"] == "em_execucao"),
        "pausadasOuBloqueadas": sum(1 for d in demandas if d["status"] in ("pausada", "bloqueada")),
        "aguardandoCliente": sum(1 for d in demandas if d["status"] == "aguardando_cliente"),
        "concluidas": sum(1 for d in demandas if d["status"] == "concluida"),
    }


# --------------------------------------------------------------------------------------
# RBAC / tenant
# --------------------------------------------------------------------------------------


def test_sem_token_e_401(app) -> None:
    assert get(TestClient(app), URL).status_code == 401


def test_admin_gestor_e_operador_acessam(client_admin: TestClient, client_gestor: TestClient, client_operador: TestClient) -> None:
    """Mesma autoridade da listagem (`demandas.visualizar`): qualquer autenticado com a
    permissão, sempre dentro do próprio escopo — operador NÃO recebe 403 (a tela Tarefas é dele)."""
    for client in (client_admin, client_gestor, client_operador):
        assert client.get(URL).status_code == 200


def test_rota_nao_e_capturada_por_demanda_id(client_admin: TestClient) -> None:
    assert client_admin.get(URL).status_code == 200  # `/{demanda_id}` daria 422 (UUID inválido)


def test_tenant_isolado(client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    _demanda(db_session, empresa, None, status="em_execucao")
    _demanda(db_session, outra_empresa, None, status="em_execucao")
    _demanda(db_session, outra_empresa, None, status="concluida")
    assert _estatisticas(client_admin) == {**ZERO, "total": 1, "emExecucao": 1}


# --------------------------------------------------------------------------------------
# Contagens
# --------------------------------------------------------------------------------------


def test_vazio(client_admin: TestClient) -> None:
    assert _estatisticas(client_admin) == ZERO


def test_uma_demanda(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    _demanda(db_session, empresa, None, status="aguardando_cliente")
    assert _estatisticas(client_admin) == {**ZERO, "total": 1, "aguardandoCliente": 1}


def test_cada_status_conta_so_no_seu_card_e_arquivada_fica_de_fora(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    for status in STATUS_TODOS:
        _demanda(db_session, empresa, None, status=status)
        _demanda(db_session, empresa, None, status=status)
    assert _estatisticas(client_admin) == {
        "total": 16,  # 9 status × 2, menos as 2 arquivadas
        "emExecucao": 2,
        "pausadasOuBloqueadas": 4,  # pausada + bloqueada
        "aguardandoCliente": 2,
        "concluidas": 2,
    }  # rascunho, planejada e cancelada só entram em "Total"


def test_nao_acompanha_busca_nem_filtro_de_status(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    """`DemandasStats` sempre recebeu o array global, nunca a página filtrada: parâmetros de
    listagem não existem aqui e, se enviados, não mudam nada."""
    _demanda(db_session, empresa, None, status="concluida", nome="Alfa")
    _demanda(db_session, empresa, None, status="em_execucao", nome="Beta")
    esperado = {**ZERO, "total": 2, "emExecucao": 1, "concluidas": 1}
    assert _estatisticas(client_admin) == esperado
    assert _estatisticas(client_admin, status="concluida", search="Alfa") == esperado


# --------------------------------------------------------------------------------------
# Escopo — o mesmo da listagem
# --------------------------------------------------------------------------------------


def test_operador_so_conta_o_que_a_propria_listagem_mostra(
    client_admin: TestClient, client_operador: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    _demanda(db_session, empresa, None, status="em_execucao", responsaveis=[usuario_operador])
    _demanda(db_session, empresa, None, status="concluida", responsaveis=[usuario_operador])
    for status in ("em_execucao", "pausada", "concluida", "rascunho"):
        _demanda(db_session, empresa, None, status=status)  # de outras pessoas: fora do escopo dele

    assert _estatisticas(client_operador) == {**ZERO, "total": 2, "emExecucao": 1, "concluidas": 1}
    assert _estatisticas(client_admin)["total"] == 6
    # O total dos cards é exatamente o tamanho da lista que a tela mostra, para cada perfil.
    assert _estatisticas(client_operador)["total"] == len(_listar_tudo(client_operador))
    assert _estatisticas(client_admin)["total"] == len(_listar_tudo(client_admin))


def test_operador_sem_vinculo_recebe_zeros_nao_403(client_operador: TestClient, db_session: Session, empresa: Empresa) -> None:
    _demanda(db_session, empresa, None, status="em_execucao")
    assert _estatisticas(client_operador) == ZERO


# --------------------------------------------------------------------------------------
# Paridade com a lógica antiga e dataset > 200
# --------------------------------------------------------------------------------------


def test_paridade_com_a_logica_antiga_em_dataset_pequeno(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    for i, status in enumerate(STATUS_TODOS * 3):
        _demanda(db_session, empresa, None, status=status, criada=BASE + timedelta(minutes=i))
    esperado = _stats_antigo(client_admin.get("/demandas", params={"limit": 200}).json())
    assert _estatisticas(client_admin) == esperado


def test_acima_de_200_conta_tudo_e_a_conta_antiga_daria_outro_valor(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """250 Demandas com distribuição conhecida. As 50 MAIS ANTIGAS (fora das 200 que o
    `GET /demandas?limit=200` entregava) são todas `concluida` — a conta antiga as perderia."""
    distribuicao = ["em_execucao", "pausada", "bloqueada", "aguardando_cliente", "rascunho", "cancelada"]
    for i in range(50):
        _demanda(db_session, empresa, None, numero=i + 1, status="concluida")
    for i in range(200):
        _demanda(db_session, empresa, None, numero=1000 + i, status=distribuicao[i % 6] if i % 7 else "concluida")
    for i in range(10):
        _demanda(db_session, empresa, None, numero=5000 + i, status="arquivada")  # não contam em lugar nenhum

    # 200 recentes: i%7==0 → concluida (29 delas: i=0,7,...,196); o resto cicla em 6 status.
    recentes = [distribuicao[i % 6] if i % 7 else "concluida" for i in range(200)]
    esperado = {
        "total": 250,
        "emExecucao": recentes.count("em_execucao"),
        "pausadasOuBloqueadas": recentes.count("pausada") + recentes.count("bloqueada"),
        "aguardandoCliente": recentes.count("aguardando_cliente"),
        "concluidas": 50 + recentes.count("concluida"),
    }
    assert _estatisticas(client_admin) == esperado

    antigo = _stats_antigo(client_admin.get("/demandas", params={"limit": 200}).json())
    assert antigo["total"] == 200 and esperado["total"] == 250
    assert antigo["concluidas"] == recentes.count("concluida")  # as 50 antigas não entravam
    assert antigo != esperado


# --------------------------------------------------------------------------------------
# Sem N+1
# --------------------------------------------------------------------------------------


def _consultas_a_demandas(app, db_session: Session, token: str) -> int:
    chamadas: list[str] = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "FROM demandas" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = get(TestClient(app), URL, token=token)
    finally:
        event.remove(engine, "before_cursor_execute", _contar)
    assert resposta.status_code == 200, resposta.text
    return len(chamadas)


@pytest.mark.parametrize("perfil", ["admin", "operador"])
def test_numero_de_consultas_constante(
    app, db_session: Session, empresa: Empresa, token_admin: str, token_operador: str, usuario_operador: Usuario, perfil: str
) -> None:
    token = token_admin if perfil == "admin" else token_operador
    _demanda(db_session, empresa, None, status="em_execucao", responsaveis=[usuario_operador])
    com_uma = _consultas_a_demandas(app, db_session, token)
    for i in range(80):
        _demanda(db_session, empresa, None, status=STATUS_TODOS[i % 9], responsaveis=[usuario_operador])
    com_muitas = _consultas_a_demandas(app, db_session, token)
    assert com_uma == com_muitas == 1  # um único agregado, com escopo e tenant no próprio SQL
