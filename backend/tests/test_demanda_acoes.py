"""Ações de Demanda que só publicam evento ou completam a timeline (Fase 2E.4).

Cobre a correção do bug de persistência de RegistrarAjusteCard/EnvioClienteCard/
DemandaConclusaoBanner: as três ações passaram a usar API real (nunca mais
`setDemandas(...)` local) — aqui a prova é que o estado sobrevive a uma nova consulta ao
servidor, não a um estado React que nunca existiu de verdade.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _nome_unico(prefixo: str) -> str:
    return f"{prefixo} {uuid.uuid4().hex[:8]}"


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": _nome_unico("Demanda"), **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _tipos(historico: list[dict]) -> list[str]:
    return [item["tipo"] for item in historico]


# --------------------------------------------------------------------------------------
# RegistrarAjusteCard — /demandas/{id}/ajustes
# --------------------------------------------------------------------------------------

def test_registrar_ajuste_nao_altera_campo_nenhum_da_demanda(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    antes = client_admin.get(f"/demandas/{demanda['id']}").json()

    resposta = client_admin.post(f"/demandas/{demanda['id']}/ajustes", json={"tipo": "ajuste_interno"})
    assert resposta.status_code == 201, resposta.text

    depois = client_admin.get(f"/demandas/{demanda['id']}").json()
    assert depois["updatedAt"] == antes["updatedAt"]
    assert depois["status"] == antes["status"]


def test_registrar_ajuste_sobrevive_a_nova_consulta(client_admin: TestClient) -> None:
    """Prova a correção do bug: a ação grava no servidor, então reconsultar (equivalente a
    reabrir a Demanda depois de um F5) mostra o mesmo evento, não um estado perdido."""
    demanda = _criar_demanda(client_admin)
    client_admin.post(f"/demandas/{demanda['id']}/ajustes", json={"tipo": "ajuste_cliente"})

    historico = client_admin.get(f"/demandas/{demanda['id']}/historico").json()
    assert "demanda.ajuste_cliente_registrado" in _tipos(historico)


def test_tres_tipos_de_ajuste_continuam_diferenciados(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    for tipo, evento_esperado in (
        ("ajuste_interno", "demanda.ajuste_interno_registrado"),
        ("ajuste_cliente", "demanda.ajuste_cliente_registrado"),
        ("refacao", "demanda.refacao_registrada"),
    ):
        resposta = client_admin.post(f"/demandas/{demanda['id']}/ajustes", json={"tipo": tipo})
        assert resposta.status_code == 201, resposta.text
        assert resposta.json()["tipo"] == evento_esperado

    tipos = _tipos(client_admin.get(f"/demandas/{demanda['id']}/historico").json())
    assert "demanda.ajuste_interno_registrado" in tipos
    assert "demanda.ajuste_cliente_registrado" in tipos
    assert "demanda.refacao_registrada" in tipos


def test_tipo_de_ajuste_invalido_e_recusado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.post(f"/demandas/{demanda['id']}/ajustes", json={"tipo": "outro"})
    assert resposta.status_code == 422, resposta.text


def test_ajuste_em_demanda_inexistente_devolve_404(client_admin: TestClient) -> None:
    resposta = client_admin.post(f"/demandas/{uuid.uuid4()}/ajustes", json={"tipo": "refacao"})
    assert resposta.status_code == 404


# --------------------------------------------------------------------------------------
# EnvioClienteCard — PATCH real (sem endpoint dedicado; ver update_demanda)
# --------------------------------------------------------------------------------------

def test_enviar_para_cliente_persiste_campos_reais(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}",
        json={
            "status": "aguardando_cliente",
            "enviadoClienteEm": "2026-08-20T12:00:00+00:00",
            "prazoRetornoCliente": "2026-08-22T12:00:00+00:00",
        },
    )
    assert resposta.status_code == 200, resposta.text

    # Sobrevive a uma nova consulta — prova que não é mais só `setDemandas(...)` local.
    relido = client_admin.get(f"/demandas/{demanda['id']}").json()
    assert relido["status"] == "aguardando_cliente"
    assert relido["enviadoClienteEm"] is not None
    assert relido["prazoRetornoCliente"] is not None

    tipos = _tipos(client_admin.get(f"/demandas/{demanda['id']}/historico").json())
    assert "demanda.status_alterado" in tipos


def test_marcar_retorno_recebido_publica_evento_dedicado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    client_admin.patch(
        f"/demandas/{demanda['id']}",
        json={"status": "aguardando_cliente", "enviadoClienteEm": "2026-08-20T12:00:00+00:00"},
    )

    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}", json={"retornoRecebidoEm": "2026-08-21T09:00:00+00:00"}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["retornoRecebidoEm"] is not None

    tipos = _tipos(client_admin.get(f"/demandas/{demanda['id']}/historico").json())
    assert "demanda.retorno_cliente_registrado" in tipos


def test_marcar_retorno_recebido_duas_vezes_nao_duplica_evento(client_admin: TestClient) -> None:
    """A transição só é None -> valor uma vez; reenviar o mesmo valor não é fato novo."""
    demanda = _criar_demanda(client_admin)
    client_admin.patch(f"/demandas/{demanda['id']}", json={"retornoRecebidoEm": "2026-08-21T09:00:00+00:00"})
    client_admin.patch(f"/demandas/{demanda['id']}", json={"retornoRecebidoEm": "2026-08-21T09:00:00+00:00"})

    tipos = _tipos(client_admin.get(f"/demandas/{demanda['id']}/historico").json())
    assert tipos.count("demanda.retorno_cliente_registrado") == 1


# --------------------------------------------------------------------------------------
# DemandaConclusaoBanner — /demandas/{id}/conclusao-email
# --------------------------------------------------------------------------------------

def _concluir(client: TestClient, demanda_id: str) -> None:
    resposta = client.patch(f"/demandas/{demanda_id}", json={"status": "concluida"})
    assert resposta.status_code == 200, resposta.text


def test_conclusao_email_enviado_persiste_campos_reais(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _concluir(client_admin, demanda["id"])

    resposta = client_admin.post(f"/demandas/{demanda['id']}/conclusao-email", json={"enviado": True})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["emailConclusaoEnviado"] is True
    assert corpo["emailConclusaoData"] is not None

    relido = client_admin.get(f"/demandas/{demanda['id']}").json()
    assert relido["emailConclusaoEnviado"] is True

    tipos = _tipos(client_admin.get(f"/demandas/{demanda['id']}/historico").json())
    assert "demanda.email_conclusao_enviado" in tipos
    assert "demanda.email_conclusao_dispensado" not in tipos


def test_conclusao_email_dispensado_persiste_os_mesmos_campos_com_evento_diferente(
    client_admin: TestClient,
) -> None:
    demanda = _criar_demanda(client_admin)
    _concluir(client_admin, demanda["id"])

    resposta = client_admin.post(f"/demandas/{demanda['id']}/conclusao-email", json={"enviado": False})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    # Mesmos campos reais que a via "enviado" — só o evento distingue a intenção.
    assert corpo["emailConclusaoEnviado"] is True
    assert corpo["emailConclusaoData"] is not None

    tipos = _tipos(client_admin.get(f"/demandas/{demanda['id']}/historico").json())
    assert "demanda.email_conclusao_dispensado" in tipos
    assert "demanda.email_conclusao_enviado" not in tipos


def test_conclusao_email_fora_de_concluida_e_recusada(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.post(f"/demandas/{demanda['id']}/conclusao-email", json={"enviado": True})
    assert resposta.status_code == 409, resposta.text


def test_conclusao_email_em_demanda_inexistente_devolve_404(client_admin: TestClient) -> None:
    resposta = client_admin.post(f"/demandas/{uuid.uuid4()}/conclusao-email", json={"enviado": True})
    assert resposta.status_code == 404
