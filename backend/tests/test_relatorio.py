"""Relatórios — agregação de Ajustes internos/Ajustes cliente/Refações por Projeto (Fase 2F.4).

`GET /relatorios/demandas/ajustes` lê a contagem real de `eventos` (`demanda.ajuste_interno_
registrado`/`demanda.ajuste_cliente_registrado`/`demanda.refacao_registrada`) — a prova central
deste domínio é que nenhum outro tipo de evento (retorno de cliente, criação, comentário,
checklist, arquivo, status, ou evento de outra entidade/empresa/Projeto) contamina a contagem.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.projeto import Projeto


def _nome_unico(prefixo: str) -> str:
    return f"{prefixo} {uuid.uuid4().hex[:8]}"


def _criar_projeto(client: TestClient, **extra) -> dict:
    resposta = client.post("/projetos", json={"nome": _nome_unico("Projeto"), **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": _nome_unico("Demanda"), **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _registrar_ajuste(client: TestClient, demanda_id: str, tipo: str) -> None:
    resposta = client.post(f"/demandas/{demanda_id}/ajustes", json={"tipo": tipo})
    assert resposta.status_code == 201, resposta.text


def _ajustes(client: TestClient, projeto_id: str) -> dict:
    resposta = client.get("/relatorios/demandas/ajustes", params={"projetoId": projeto_id})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# --------------------------------------------------------------------------------------
# Contagem
# --------------------------------------------------------------------------------------


def test_contagem_por_tipo_em_uma_demanda(client_admin: TestClient) -> None:
    projeto = _criar_projeto(client_admin)
    demanda = _criar_demanda(client_admin, projetoId=projeto["id"])

    _registrar_ajuste(client_admin, demanda["id"], "ajuste_interno")
    _registrar_ajuste(client_admin, demanda["id"], "ajuste_cliente")
    _registrar_ajuste(client_admin, demanda["id"], "refacao")
    _registrar_ajuste(client_admin, demanda["id"], "refacao")

    resultado = _ajustes(client_admin, projeto["id"])
    assert resultado["total"] == {"ajustesInternos": 1, "ajustesCliente": 1, "refacoes": 2}
    assert resultado["porDemanda"][demanda["id"]] == {
        "ajustesInternos": 1,
        "ajustesCliente": 1,
        "refacoes": 2,
    }


def test_multiplas_demandas_soma_no_total_e_separa_por_demanda(client_admin: TestClient) -> None:
    projeto = _criar_projeto(client_admin)
    demanda_a = _criar_demanda(client_admin, projetoId=projeto["id"])
    demanda_b = _criar_demanda(client_admin, projetoId=projeto["id"])

    _registrar_ajuste(client_admin, demanda_a["id"], "ajuste_interno")
    _registrar_ajuste(client_admin, demanda_a["id"], "ajuste_interno")
    _registrar_ajuste(client_admin, demanda_b["id"], "ajuste_cliente")

    resultado = _ajustes(client_admin, projeto["id"])
    assert resultado["total"] == {"ajustesInternos": 2, "ajustesCliente": 1, "refacoes": 0}
    assert resultado["porDemanda"][demanda_a["id"]] == {
        "ajustesInternos": 2,
        "ajustesCliente": 0,
        "refacoes": 0,
    }
    assert resultado["porDemanda"][demanda_b["id"]] == {
        "ajustesInternos": 0,
        "ajustesCliente": 1,
        "refacoes": 0,
    }


def test_retorno_cliente_nao_altera_contagem(client_admin: TestClient) -> None:
    projeto = _criar_projeto(client_admin)
    demanda = _criar_demanda(client_admin, projetoId=projeto["id"])
    _registrar_ajuste(client_admin, demanda["id"], "ajuste_interno")

    # Transição None -> valor publica `demanda.retorno_cliente_registrado` (ver
    # DemandaService.atualizar_demanda) — não é ajuste/refação e não deve contar.
    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}", json={"retornoRecebidoEm": "2026-08-20T10:00:00Z"}
    )
    assert resposta.status_code == 200, resposta.text

    resultado = _ajustes(client_admin, projeto["id"])
    assert resultado["total"] == {"ajustesInternos": 1, "ajustesCliente": 0, "refacoes": 0}


def test_evento_de_outra_entidade_nao_conta(client_admin: TestClient, db_session: Session) -> None:
    projeto = _criar_projeto(client_admin)
    demanda = _criar_demanda(client_admin, projetoId=projeto["id"])
    _registrar_ajuste(client_admin, demanda["id"], "ajuste_interno")

    agora = datetime.now(timezone.utc)
    intruso = Evento(
        id=str(uuid.uuid4()),
        empresa_id=demanda["empresaId"],
        agencia_id=None,
        tipo="demanda.ajuste_interno_registrado",
        entidade_tipo="projeto",  # mesmo id, entidade_tipo diferente
        entidade_id=demanda["id"],
        usuario_id=None,
        payload={},
        occurred_at=agora,
        created_at=agora,
    )
    db_session.add(intruso)
    db_session.flush()

    resultado = _ajustes(client_admin, projeto["id"])
    assert resultado["total"] == {"ajustesInternos": 1, "ajustesCliente": 0, "refacoes": 0}


def test_evento_de_outro_projeto_nao_conta(client_admin: TestClient) -> None:
    projeto_a = _criar_projeto(client_admin)
    projeto_b = _criar_projeto(client_admin)
    demanda_b = _criar_demanda(client_admin, projetoId=projeto_b["id"])
    _registrar_ajuste(client_admin, demanda_b["id"], "refacao")

    resultado = _ajustes(client_admin, projeto_a["id"])
    assert resultado["total"] == {"ajustesInternos": 0, "ajustesCliente": 0, "refacoes": 0}
    assert resultado["porDemanda"] == {}


def test_evento_de_outra_empresa_nao_conta(client_admin: TestClient, db_session: Session) -> None:
    projeto = _criar_projeto(client_admin)
    demanda = _criar_demanda(client_admin, projetoId=projeto["id"])
    _registrar_ajuste(client_admin, demanda["id"], "ajuste_interno")

    agora = datetime.now(timezone.utc)
    outra = Empresa(
        id=str(uuid.uuid4()),
        nome="Outra Empresa Relatorio",
        documento=None,
        codigo_interno=f"REL-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(outra)
    db_session.flush()

    # `entidade_id` coincide de propósito com a Demanda real — prova que o filtro por
    # `empresa_id` na query é o que barra, não só a ausência de colisão de UUID.
    intruso = Evento(
        id=str(uuid.uuid4()),
        empresa_id=outra.id,
        agencia_id=None,
        tipo="demanda.refacao_registrada",
        entidade_tipo="demanda",
        entidade_id=demanda["id"],
        usuario_id=None,
        payload={},
        occurred_at=agora,
        created_at=agora,
    )
    db_session.add(intruso)
    db_session.flush()

    resultado = _ajustes(client_admin, projeto["id"])
    assert resultado["total"] == {"ajustesInternos": 1, "ajustesCliente": 0, "refacoes": 0}


def test_projeto_valido_sem_eventos_devolve_zero_real(client_admin: TestClient) -> None:
    projeto = _criar_projeto(client_admin)
    _criar_demanda(client_admin, projetoId=projeto["id"])

    resultado = _ajustes(client_admin, projeto["id"])
    assert resultado == {
        "total": {"ajustesInternos": 0, "ajustesCliente": 0, "refacoes": 0},
        "porDemanda": {},
    }


# --------------------------------------------------------------------------------------
# Projeto inexistente / cross-tenant — sempre 404, nunca 403 nem 200 zerado
# --------------------------------------------------------------------------------------


def test_projeto_inexistente_devolve_404(client_admin: TestClient) -> None:
    resposta = client_admin.get(
        "/relatorios/demandas/ajustes", params={"projetoId": str(uuid.uuid4())}
    )
    assert resposta.status_code == 404


def test_projeto_de_outra_empresa_devolve_404_nao_403_nem_zerado(
    client_admin: TestClient, db_session: Session
) -> None:
    agora = datetime.now(timezone.utc)
    outra = Empresa(
        id=str(uuid.uuid4()),
        nome="Outra Empresa Relatorio Projeto",
        documento=None,
        codigo_interno=f"RELP-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(outra)
    db_session.flush()

    alheio = Projeto(
        id=str(uuid.uuid4()),
        empresa_id=outra.id,
        codigo_referencia="P26009999",
        ano_referencia=26,
        sequencial_referencia=9999,
        nome="Projeto de outra empresa",
        nome_normalizado="projeto de outra empresa",
        status="ativo",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(alheio)
    db_session.flush()

    resposta = client_admin.get(
        "/relatorios/demandas/ajustes", params={"projetoId": alheio.id}
    )
    assert resposta.status_code == 404


# --------------------------------------------------------------------------------------
# Permissões
# --------------------------------------------------------------------------------------


def test_admin_acessa(client_admin: TestClient) -> None:
    projeto = _criar_projeto(client_admin)
    assert (
        client_admin.get("/relatorios/demandas/ajustes", params={"projetoId": projeto["id"]}).status_code
        == 200
    )


def test_gestor_acessa(client_admin: TestClient, client_gestor: TestClient) -> None:
    projeto = _criar_projeto(client_admin)
    assert (
        client_gestor.get("/relatorios/demandas/ajustes", params={"projetoId": projeto["id"]}).status_code
        == 200
    )


def test_operador_nao_acessa(client_admin: TestClient, client_operador: TestClient) -> None:
    projeto = _criar_projeto(client_admin)
    resposta = client_operador.get(
        "/relatorios/demandas/ajustes", params={"projetoId": projeto["id"]}
    )
    assert resposta.status_code == 403
