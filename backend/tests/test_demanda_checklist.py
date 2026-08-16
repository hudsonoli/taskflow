"""Checklist de Demanda (Fase 2E.3) — primeira versão: texto, ordem, concluído.

Sem responsável, departamento, prazo, SLA ou dependência entre itens — fora do escopo desta
fase por decisão explícita (ver instrução da Fase 2E.3, item 8).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.empresa import Empresa
from app.models.usuario import Usuario


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_item(client: TestClient, demanda_id: str, texto: str = "Revisar briefing") -> dict:
    resposta = client.post(f"/demandas/{demanda_id}/checklist", json={"texto": texto})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# --------------------------------------------------------------------------------------
# CRUD básico
# --------------------------------------------------------------------------------------

def test_criar_item(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    item = _criar_item(client_admin, demanda["id"], "Confirmar prazo com cliente")

    assert item["texto"] == "Confirmar prazo com cliente"
    assert item["ordem"] == 0
    assert item["concluido"] is False
    assert item["concluidoEm"] is None
    assert item["demandaId"] == demanda["id"]
    assert item["criadoPorUsuarioId"] is not None


def test_texto_so_espaco_e_recusado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.post(f"/demandas/{demanda['id']}/checklist", json={"texto": "   "})
    assert resposta.status_code == 422, resposta.text


def test_listar_itens_ordenados(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _criar_item(client_admin, demanda["id"], "Item 1")
    _criar_item(client_admin, demanda["id"], "Item 2")
    _criar_item(client_admin, demanda["id"], "Item 3")

    resposta = client_admin.get(f"/demandas/{demanda['id']}/checklist")
    assert resposta.status_code == 200
    itens = resposta.json()
    assert [item["texto"] for item in itens] == ["Item 1", "Item 2", "Item 3"]
    assert [item["ordem"] for item in itens] == [0, 1, 2]


def test_demanda_recem_criada_tem_checklist_vazio(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.get(f"/demandas/{demanda['id']}/checklist")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_editar_texto(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    item = _criar_item(client_admin, demanda["id"])

    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}/checklist/{item['id']}", json={"texto": "Texto revisado"}
    )
    assert resposta.status_code == 200
    assert resposta.json()["texto"] == "Texto revisado"


def test_concluir_e_reabrir(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    item = _criar_item(client_admin, demanda["id"])

    concluido = client_admin.patch(
        f"/demandas/{demanda['id']}/checklist/{item['id']}", json={"concluido": True}
    ).json()
    assert concluido["concluido"] is True
    assert concluido["concluidoEm"] is not None
    assert concluido["concluidoPorUsuarioId"] is not None

    reaberto = client_admin.patch(
        f"/demandas/{demanda['id']}/checklist/{item['id']}", json={"concluido": False}
    ).json()
    assert reaberto["concluido"] is False
    assert reaberto["concluidoEm"] is None
    assert reaberto["concluidoPorUsuarioId"] is None


def test_reordenar(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    a = _criar_item(client_admin, demanda["id"], "A")
    b = _criar_item(client_admin, demanda["id"], "B")
    c = _criar_item(client_admin, demanda["id"], "C")

    resposta = client_admin.put(
        f"/demandas/{demanda['id']}/checklist/reordenar",
        json={"itemIds": [c["id"], a["id"], b["id"]]},
    )
    assert resposta.status_code == 200
    reordenados = resposta.json()
    assert [item["id"] for item in reordenados] == [c["id"], a["id"], b["id"]]
    assert [item["ordem"] for item in reordenados] == [0, 1, 2]


def test_reordenar_com_conjunto_diferente_e_recusado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    a = _criar_item(client_admin, demanda["id"], "A")
    _criar_item(client_admin, demanda["id"], "B")

    # Falta um id da demanda e sobra um estranho — nem subconjunto nem superconjunto válido.
    resposta = client_admin.put(
        f"/demandas/{demanda['id']}/checklist/reordenar",
        json={"itemIds": [a["id"], str(uuid.uuid4())]},
    )
    assert resposta.status_code == 422, resposta.text


def test_excluir_item(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    item = _criar_item(client_admin, demanda["id"])

    resposta = client_admin.delete(f"/demandas/{demanda['id']}/checklist/{item['id']}")
    assert resposta.status_code == 204

    itens = client_admin.get(f"/demandas/{demanda['id']}/checklist").json()
    assert itens == []


# --------------------------------------------------------------------------------------
# Escopo e isolamento
# --------------------------------------------------------------------------------------

def test_demanda_inexistente_devolve_404(client_admin: TestClient) -> None:
    assert client_admin.get(f"/demandas/{uuid.uuid4()}/checklist").status_code == 404
    assert (
        client_admin.post(f"/demandas/{uuid.uuid4()}/checklist", json={"texto": "x"}).status_code == 404
    )


def test_item_inexistente_devolve_404(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}/checklist/{uuid.uuid4()}", json={"concluido": True}
    )
    assert resposta.status_code == 404


def test_item_de_outra_demanda_nao_e_alcancavel(client_admin: TestClient) -> None:
    """O id do item existe, mas não nesta Demanda — mesmo 404 de item inexistente, não 200
    nem confusão de escopo entre duas Demandas da mesma empresa."""
    demanda_a = _criar_demanda(client_admin)
    demanda_b = _criar_demanda(client_admin)
    item_de_a = _criar_item(client_admin, demanda_a["id"])

    resposta = client_admin.patch(
        f"/demandas/{demanda_b['id']}/checklist/{item_de_a['id']}", json={"texto": "invasão"}
    )
    assert resposta.status_code == 404


def test_operador_sem_escopo_recebe_404(
    client_admin: TestClient, client_operador: TestClient
) -> None:
    alheia = _criar_demanda(client_admin)
    resposta = client_operador.get(f"/demandas/{alheia['id']}/checklist")
    assert resposta.status_code == 404


def test_operador_com_escopo_interage_normalmente(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    """Checklist é operacional: qualquer um com escopo sobre a Demanda cria, edita, conclui e
    exclui — não é ação restrita a admin/gestor (ver instrução da fase, item 13)."""
    minha = _criar_demanda(client_admin, usuarioResponsavelIds=[usuario_operador.id])

    item = _criar_item(client_operador, minha["id"], "Tarefa do operador")
    assert (
        client_operador.patch(
            f"/demandas/{minha['id']}/checklist/{item['id']}", json={"concluido": True}
        ).status_code
        == 200
    )
    assert client_operador.delete(f"/demandas/{minha['id']}/checklist/{item['id']}").status_code == 204


def test_demanda_de_outra_empresa_devolve_404(
    client_admin: TestClient, db_session: Session
) -> None:
    agora = datetime.now(timezone.utc)
    outra = Empresa(
        id=str(uuid.uuid4()),
        nome="Outra Empresa Checklist",
        documento=None,
        codigo_interno=f"CHK-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(outra)
    db_session.flush()

    intrusa = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=outra.id,
        codigo_referencia="T26008888",
        ano_referencia=26,
        sequencial_referencia=8888,
        numero_operacional=8888,
        nome="Demanda de outra empresa",
        status="rascunho",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(intrusa)
    db_session.flush()

    assert client_admin.get(f"/demandas/{intrusa.id}/checklist").status_code == 404
