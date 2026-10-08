"""Fase 6 — filtros avançados de Arquivos (`GET /arquivos`) e Tráfego (`/sessoes-trabalho/trafego/*`).

Semântica provada aqui (a mesma que a interface usa):
- entre campos diferentes: AND; dentro de um campo: OR ("é um de");
- "não é um de" (`*Excluir`) mantém o registro cujo campo é NULL;
- tudo é aplicado no SQL, ANTES da paginação (limit/offset);
- valor inválido na query é 422 (nunca ignorado em silêncio) e há teto de valores;
- a empresa vem sempre da sessão: nenhum filtro atravessa tenant.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from tests.helpers.api import get
from tests.test_gerenciador_arquivos import _central, _cliente, _criar_demanda, _link, _projeto, _upload, PNG_VALIDO
from tests.test_trafego_carga import _departamento, _sessao, _usuario

# ======================================================================================
# ARQUIVOS
# ======================================================================================


def _ids(achados: list[dict]) -> set[str]:
    return {item["id"] for item in achados}


def _montar_arquivos(client_admin: TestClient, db: Session, empresa: Empresa) -> dict:
    """Três demandas (cliente A, cliente B, sem cliente) com um link cada, mais um layout aprovado."""
    cliente_a, cliente_b = _cliente(db, empresa), _cliente(db, empresa)
    projeto_a = _projeto(db, empresa, cliente_id=cliente_a.id)
    d_a = _criar_demanda(client_admin, clienteId=str(cliente_a.id), projetoId=str(projeto_a.id))
    d_b = _criar_demanda(client_admin, clienteId=str(cliente_b.id))
    d_0 = _criar_demanda(client_admin)
    return {
        "cliente_a": cliente_a,
        "cliente_b": cliente_b,
        "projeto_a": projeto_a,
        "d_a": d_a,
        "d_b": d_b,
        "d_0": d_0,
        "link_a": _link(client_admin, d_a["id"], titulo="alfa").json(),
        "link_b": _link(client_admin, d_b["id"], titulo="beta").json(),
        "link_0": _link(client_admin, d_0["id"], titulo="gama").json(),
    }


def test_arquivos_cliente_e_um_de_varios(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    m = _montar_arquivos(client_admin, db_session, empresa)
    um = _central(client_admin, clienteId=str(m["cliente_a"].id)).json()
    assert _ids(um) == {m["link_a"]["id"]}
    varios = _central(client_admin, clienteId=f"{m['cliente_a'].id},{m['cliente_b'].id}").json()
    assert _ids(varios) == {m["link_a"]["id"], m["link_b"]["id"]}  # OR dentro do campo


def test_arquivos_cliente_nao_e_mantem_arquivo_sem_cliente(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    m = _montar_arquivos(client_admin, db_session, empresa)
    achados = _central(client_admin, clienteIdExcluir=str(m["cliente_a"].id)).json()
    # NULL não é igual a nenhum valor: o arquivo da demanda SEM cliente continua na lista
    assert {m["link_b"]["id"], m["link_0"]["id"]} <= _ids(achados)
    assert m["link_a"]["id"] not in _ids(achados)
    nenhum = _central(client_admin, clienteIdExcluir=f"{m['cliente_a'].id},{m['cliente_b'].id}").json()
    assert m["link_0"]["id"] in _ids(nenhum) and not ({m["link_a"]["id"], m["link_b"]["id"]} & _ids(nenhum))


def test_arquivos_projeto_demanda_e_tipo(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    m = _montar_arquivos(client_admin, db_session, empresa)
    assert _ids(_central(client_admin, projetoId=str(m["projeto_a"].id)).json()) == {m["link_a"]["id"]}
    assert m["link_a"]["id"] not in _ids(_central(client_admin, projetoIdExcluir=str(m["projeto_a"].id)).json())
    assert _ids(_central(client_admin, demandaId=f"{m['d_a']['id']},{m['d_b']['id']}").json()) == {m["link_a"]["id"], m["link_b"]["id"]}
    anexo = _upload(client_admin, m["d_0"]["id"], nome="x.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout").json()
    so_links = _central(client_admin, demandaId=m["d_0"]["id"], tipo="link").json()
    assert _ids(so_links) == {m["link_0"]["id"]}
    sem_links = _central(client_admin, demandaId=m["d_0"]["id"], tipoExcluir="link").json()
    assert _ids(sem_links) == {anexo["id"]}
    layout_ou_link = _central(client_admin, demandaId=m["d_0"]["id"], tipo="layout,link").json()
    assert _ids(layout_ou_link) == {anexo["id"], m["link_0"]["id"]}


def test_arquivos_status_layout_e_um_de_e_nao_e(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    novo = _upload(client_admin, demanda["id"], nome="a.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout").json()
    aprovado = _upload(client_admin, demanda["id"], nome="b.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout").json()
    reprovado = _upload(client_admin, demanda["id"], nome="c.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout").json()
    client_admin.patch(f"/demandas/{demanda['id']}/arquivos/{aprovado['id']}", json={"statusLayout": "aprovado"})
    client_admin.patch(f"/demandas/{demanda['id']}/arquivos/{reprovado['id']}", json={"statusLayout": "reprovado"})
    link = _link(client_admin, demanda["id"]).json()  # link não tem status de layout (NULL)

    base = {"demandaId": demanda["id"]}
    assert _ids(_central(client_admin, **base, status="aprovado,reprovado").json()) == {aprovado["id"], reprovado["id"]}
    nao_aprovado = _ids(_central(client_admin, **base, statusExcluir="aprovado").json())
    assert nao_aprovado == {novo["id"], reprovado["id"], link["id"]}  # inclui o NULL (link)


def test_arquivos_enviado_por_e_um_de_e_nao_e(client_admin: TestClient, client_gestor: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    do_admin = _link(client_admin, demanda["id"], titulo="a").json()
    do_gestor = _link(client_gestor, demanda["id"], titulo="b").json()
    base = {"demandaId": demanda["id"]}
    assert _ids(_central(client_admin, **base, usuarioId=do_admin["enviadoPorUsuarioId"]).json()) == {do_admin["id"]}
    assert _ids(_central(client_admin, **base, usuarioIdExcluir=do_admin["enviadoPorUsuarioId"]).json()) == {do_gestor["id"]}
    ambos = f"{do_admin['enviadoPorUsuarioId']},{do_gestor['enviadoPorUsuarioId']}"
    assert _ids(_central(client_admin, **base, usuarioId=ambos).json()) == {do_admin["id"], do_gestor["id"]}


def test_arquivos_filtros_combinam_com_and_e_com_busca(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    m = _montar_arquivos(client_admin, db_session, empresa)
    # cliente A E tipo link E busca "alfa"
    achados = _central(client_admin, clienteId=str(m["cliente_a"].id), tipo="link", search="alfa").json()
    assert _ids(achados) == {m["link_a"]["id"]}
    # a busca restringe: mesmo cliente, outro termo
    assert _central(client_admin, clienteId=str(m["cliente_a"].id), search="beta").json() == []
    # "é um de" de cliente + "não é" de tipo
    assert _central(client_admin, clienteId=f"{m['cliente_a'].id},{m['cliente_b'].id}", tipoExcluir="link").json() == []


def test_arquivos_filtro_vale_antes_da_paginacao(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    demanda_alvo = _criar_demanda(client_admin, clienteId=str(cliente.id))
    alvo = _link(client_admin, demanda_alvo["id"], titulo="alvo-antigo").json()
    ruido = _criar_demanda(client_admin)
    for i in range(5):  # mais recentes que o alvo: ele ficaria fora de uma página de 3 sem filtro
        _link(client_admin, ruido["id"], titulo=f"ruido-{i}")
    sem_filtro = _central(client_admin, limit=3, offset=0).json()
    assert alvo["id"] not in _ids(sem_filtro)
    com_filtro = _central(client_admin, clienteId=str(cliente.id), limit=3, offset=0).json()
    assert _ids(com_filtro) == {alvo["id"]}  # filtrado no servidor ANTES do limit
    assert _central(client_admin, clienteId=str(cliente.id), limit=3, offset=3).json() == []


def test_arquivos_sem_resultado_e_lista_vazia(client_admin: TestClient) -> None:
    resposta = _central(client_admin, clienteId=str(uuid.uuid4()))
    assert resposta.status_code == 200 and resposta.json() == []


@pytest.mark.parametrize(
    "params",
    [
        {"clienteId": "nao-uuid"},
        {"clienteIdExcluir": "x"},
        {"projetoId": "1,2"},
        {"tipo": "documento"},
        {"tipoExcluir": "anexo,foo"},
        {"status": "aprovado,bogus"},
        {"usuarioId": "abc"},
        {"demandaId": ",".join(str(uuid.uuid4()) for _ in range(51))},  # teto de valores
    ],
)
def test_arquivos_valor_invalido_e_422(client_admin: TestClient, params: dict) -> None:
    assert _central(client_admin, **params).status_code == 422


def test_arquivos_filtros_nao_atravessam_tenant(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    alheio = _cliente(db_session, outra_empresa)
    # Filtrar por cliente de OUTRA empresa nunca revela nada: o escopo/empresa vêm da sessão.
    assert _central(client_admin, clienteId=str(alheio.id)).json() == []
    assert _central(client_admin, clienteIdExcluir=str(alheio.id)).status_code == 200


# ======================================================================================
# TRÁFEGO
# ======================================================================================

TRAFEGO = "/sessoes-trabalho/trafego"


def _consulta(app, token: str, caminho: str, **params) -> dict:
    consulta = {chave: valor for chave, valor in params.items() if valor is not None}
    if caminho == "indicadores":
        consulta.setdefault("periodoInicio", (datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    url = f"{TRAFEGO}/{caminho}" + (f"?{urlencode(consulta)}" if consulta else "")
    resposta = get(TestClient(app), url, token=token)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _sessoes_ids(corpo: dict) -> set[str]:
    return {item["sessaoId"] for item in corpo["items"]}


def _cenario_trafego(client_admin: TestClient, db: Session, empresa: Empresa) -> dict:
    cliente_a, cliente_b = _cliente(db, empresa), _cliente(db, empresa)
    projeto_a = _projeto(db, empresa, cliente_id=cliente_a.id)
    agora = datetime.now(timezone.utc)
    d_a = _criar_demanda(
        client_admin, clienteId=str(cliente_a.id), projetoId=str(projeto_a.id), prioridade="alta",
        prazoEtapaAtual=(agora + timedelta(days=2)).isoformat(),
    )
    d_b = _criar_demanda(
        client_admin, clienteId=str(cliente_b.id), prioridade="baixa",
        prazoEtapaAtual=(agora + timedelta(days=10)).isoformat(),
    )
    d_0 = _criar_demanda(client_admin, prioridade="media")  # sem cliente, sem projeto, sem prazo
    ana, bia = _usuario(db, empresa, "Ana"), _usuario(db, empresa, "Bia")
    ti, criacao = _departamento(db, empresa, "TI"), _departamento(db, empresa, "Criação")
    return {
        "cliente_a": cliente_a, "cliente_b": cliente_b, "projeto_a": projeto_a, "agora": agora,
        "ana": ana, "bia": bia, "ti": ti, "criacao": criacao,
        "s_a": _sessao(db, empresa, decorrido=300, usuario=ana, departamento=ti, demanda_id=d_a["id"]),
        "s_b": _sessao(db, empresa, decorrido=200, usuario=bia, departamento=criacao, demanda_id=d_b["id"]),
        "s_0": _sessao(db, empresa, decorrido=100, usuario=None, departamento=None, demanda_id=d_0["id"]),
    }


def test_trafego_usuario_e_departamento_nao_e(app, token_admin: str, client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    c = _cenario_trafego(client_admin, db_session, empresa)
    e = _consulta(app, token_admin, "agora", usuarioIdsExcluir=c["ana"].id)
    assert _sessoes_ids(e) == {c["s_b"].id, c["s_0"].id}  # inclui a sessão SEM usuário (NULL ≠ Ana)
    e = _consulta(app, token_admin, "agora", departamentoIdsExcluir=f"{c['ti'].id},{c['criacao'].id}")
    assert _sessoes_ids(e) == {c["s_0"].id}
    # "é um de" existente continua valendo e combina por AND com o "não é"
    e = _consulta(app, token_admin, "agora", usuarioIds=f"{c['ana'].id},{c['bia'].id}", usuarioIdsExcluir=c["bia"].id)
    assert _sessoes_ids(e) == {c["s_a"].id}


def test_trafego_cliente_projeto_prioridade(app, token_admin: str, client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    c = _cenario_trafego(client_admin, db_session, empresa)
    assert _sessoes_ids(_consulta(app, token_admin, "agora", clienteIds=str(c["cliente_a"].id))) == {c["s_a"].id}
    assert _sessoes_ids(_consulta(app, token_admin, "agora", clienteIds=f"{c['cliente_a'].id},{c['cliente_b'].id}")) == {c["s_a"].id, c["s_b"].id}
    assert _sessoes_ids(_consulta(app, token_admin, "agora", clienteIdsExcluir=str(c["cliente_a"].id))) == {c["s_b"].id, c["s_0"].id}
    assert _sessoes_ids(_consulta(app, token_admin, "agora", projetoIds=str(c["projeto_a"].id))) == {c["s_a"].id}
    assert _sessoes_ids(_consulta(app, token_admin, "agora", projetoIdsExcluir=str(c["projeto_a"].id))) == {c["s_b"].id, c["s_0"].id}
    assert _sessoes_ids(_consulta(app, token_admin, "agora", prioridades="alta,media")) == {c["s_a"].id, c["s_0"].id}
    assert _sessoes_ids(_consulta(app, token_admin, "agora", prioridadesExcluir="alta")) == {c["s_b"].id, c["s_0"].id}


def test_trafego_prazo_da_demanda(app, token_admin: str, client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    c = _cenario_trafego(client_admin, db_session, empresa)
    corte = (c["agora"] + timedelta(days=5)).isoformat()
    assert _sessoes_ids(_consulta(app, token_admin, "agora", prazoFim=corte)) == {c["s_a"].id}  # antes do corte
    assert _sessoes_ids(_consulta(app, token_admin, "agora", prazoInicio=corte)) == {c["s_b"].id}  # depois do corte
    # demanda sem prazo nunca casa com filtro de prazo
    assert c["s_0"].id not in _sessoes_ids(_consulta(app, token_admin, "agora", prazoInicio=(c["agora"] - timedelta(days=30)).isoformat()))
    # prazo sem timezone é 422
    assert get(TestClient(app), f"{TRAFEGO}/agora?prazoFim=2026-10-15T00:00:00", token=token_admin).status_code == 422


def test_trafego_filtros_combinam_com_and(app, token_admin: str, client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    c = _cenario_trafego(client_admin, db_session, empresa)
    e = _consulta(app, token_admin, "agora", clienteIds=f"{c['cliente_a'].id},{c['cliente_b'].id}", prioridades="baixa", usuarioIds=c["bia"].id)
    assert _sessoes_ids(e) == {c["s_b"].id}
    e = _consulta(app, token_admin, "agora", clienteIds=str(c["cliente_a"].id), prioridades="baixa")
    assert e["items"] == [] and e["total"] == 0


def test_trafego_mesma_regra_em_agora_carga_e_indicadores(app, token_admin: str, client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    c = _cenario_trafego(client_admin, db_session, empresa)
    filtros = {"clienteIds": str(c["cliente_a"].id), "prioridades": "alta"}
    agora = _consulta(app, token_admin, "agora", **filtros)
    carga = _consulta(app, token_admin, "carga", **filtros)
    indicadores = _consulta(app, token_admin, "indicadores", **filtros)
    assert agora["total"] == 1
    assert [u["id"] for u in carga["usuarios"]] == [c["ana"].id]
    assert [d["id"] for d in carga["departamentos"]] == [c["ti"].id]
    assert indicadores["sessoesAtivas"] == 1 and indicadores["demandasDistintas"] == 1
    # "não é" também chega aos agregados
    sem_ana = _consulta(app, token_admin, "carga", usuarioIdsExcluir=c["ana"].id)
    assert c["ana"].id not in [u["id"] for u in sem_ana["usuarios"]]
    assert _consulta(app, token_admin, "indicadores", clienteIdsExcluir=str(c["cliente_a"].id))["sessoesAtivas"] == 2


def test_trafego_filtro_vale_antes_da_paginacao(app, token_admin: str, client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    demanda = _criar_demanda(client_admin, clienteId=str(cliente.id))
    alvo = _sessao(db_session, empresa, decorrido=1, demanda_id=demanda["id"])  # a MENOS tempo em execução: última da ordem
    for i in range(4):
        _sessao(db_session, empresa, decorrido=1000 + i)
    sem_filtro = _consulta(app, token_admin, "agora", limit=2)
    assert alvo.id not in _sessoes_ids(sem_filtro)
    com_filtro = _consulta(app, token_admin, "agora", clienteIds=str(cliente.id), limit=2)
    assert _sessoes_ids(com_filtro) == {alvo.id} and com_filtro["total"] == 1


@pytest.mark.parametrize(
    "params",
    [
        {"usuarioIdsExcluir": "x"},
        {"departamentoIdsExcluir": "1"},
        {"clienteIds": "nao-uuid"},
        {"clienteIdsExcluir": "nao-uuid"},
        {"projetoIds": "nao-uuid"},
        {"prioridades": "urgente"},
        {"prioridadesExcluir": "alta,urgente"},
        {"clienteIds": ",".join(str(uuid.uuid4()) for _ in range(51))},
    ],
)
@pytest.mark.parametrize("caminho", ["agora", "carga"])
def test_trafego_valor_invalido_e_422(app, token_admin: str, caminho: str, params: dict) -> None:
    url = f"{TRAFEGO}/{caminho}?{urlencode(params)}"
    assert get(TestClient(app), url, token=token_admin).status_code == 422


def test_trafego_filtros_avancados_nao_atravessam_tenant(
    app, token_admin: str, db_session: Session, outra_empresa: Empresa, client_admin: TestClient
) -> None:
    alheio = _usuario(db_session, outra_empresa)
    cliente_alheio = _cliente(db_session, outra_empresa)
    _sessao(db_session, outra_empresa, decorrido=500, usuario=alheio)
    for parametros in ({"clienteIds": str(cliente_alheio.id)}, {"usuarioIdsExcluir": alheio.id}, {"prioridades": "alta"}, {}):
        corpo = _consulta(app, token_admin, "agora", **parametros)
        assert corpo["items"] == [] and corpo["total"] == 0


def test_trafego_filtros_avancados_respeitam_rbac(app, token_operador: str) -> None:
    assert get(TestClient(app), f"{TRAFEGO}/agora?prioridades=alta", token=token_operador).status_code == 403
    assert get(TestClient(app), f"{TRAFEGO}/carga?clienteIds={uuid.uuid4()}", token=token_operador).status_code == 403
