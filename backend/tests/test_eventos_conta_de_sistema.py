"""Fase 1A — privacidade da conta de sistema nas superfícies de leitura do TENANT.

Achado de produção: o proprietário da plataforma é uma conta `is_system_account` DENTRO de uma empresa, e os
eventos dela (`auth.login_sucesso` com nome, IP e navegador) apareciam em `GET /eventos` (tela Acessos) para
qualquer gestor. Regra: o tenant normal NÃO recebe eventos cujo ATOR seja `is_system_account`; a própria conta de
sistema continua vendo os seus; eventos automáticos (`usuario_id` nulo) nunca são escondidos por esta regra. É só
VISIBILIDADE — nenhum evento é apagado ou alterado.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario

from tests.fixtures.usuarios import _criar_usuario_com_credencial


def _usuario_sistema(db: Session, empresa: Empresa) -> Usuario:
    conta = _criar_usuario_com_credencial(db, empresa=empresa, perfil_base="admin", email_prefixo="sistema")
    conta.is_system_account = True
    db.flush()
    return conta


def _client_para(app, usuario: Usuario) -> TestClient:
    cliente = TestClient(app)
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


def _evento(
    db: Session,
    empresa: Empresa,
    *,
    tipo: str,
    usuario_id: str | None,
    entidade_tipo: str = "usuario",
    entidade_id: str | None = None,
) -> Evento:
    agora = datetime.now(timezone.utc)
    evento = Evento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        tipo=tipo,
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id or usuario_id or empresa.id,
        usuario_id=usuario_id,
        payload={"nome": "Alguém", "ip_address": "10.0.0.1"},
        occurred_at=agora,
        created_at=agora,
    )
    db.add(evento)
    db.flush()
    return evento


def _ids(resposta) -> set[str]:
    assert resposta.status_code == 200, resposta.text
    return {item["id"] for item in resposta.json()}


# --------------------------------------------------------------------------------------
# GET /eventos (tela Acessos)
# --------------------------------------------------------------------------------------


def test_gestor_nao_recebe_login_de_conta_de_sistema(
    client_gestor: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    sistema = _usuario_sistema(db_session, empresa)
    do_sistema = _evento(db_session, empresa, tipo="auth.login_sucesso", usuario_id=sistema.id)
    normal = _evento(db_session, empresa, tipo="auth.login_sucesso", usuario_id=usuario_operador.id)

    ids = _ids(client_gestor.get("/eventos", params={"tipo": "auth.login_sucesso", "limit": 200}))
    assert normal.id in ids
    assert do_sistema.id not in ids


def test_gestor_nao_recebe_outros_eventos_de_ator_de_sistema(
    client_gestor: TestClient, db_session: Session, empresa: Empresa
) -> None:
    sistema = _usuario_sistema(db_session, empresa)
    outro_tipo = _evento(db_session, empresa, tipo="usuario.alterado", usuario_id=sistema.id)
    falha = _evento(db_session, empresa, tipo="auth.login_falha", usuario_id=sistema.id)
    ids = _ids(client_gestor.get("/eventos", params={"limit": 200}))
    assert outro_tipo.id not in ids and falha.id not in ids


def test_gestor_continua_recebendo_eventos_de_usuarios_normais_e_automaticos(
    client_gestor: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    de_usuario = _evento(db_session, empresa, tipo="usuario.alterado", usuario_id=usuario_operador.id)
    automatico = _evento(db_session, empresa, tipo="demanda.status_alterado", usuario_id=None, entidade_tipo="demanda")
    ids = _ids(client_gestor.get("/eventos", params={"limit": 200}))
    assert de_usuario.id in ids
    assert automatico.id in ids


def test_admin_legado_nao_conta_de_sistema_tambem_nao_ve(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    sistema = _usuario_sistema(db_session, empresa)
    do_sistema = _evento(db_session, empresa, tipo="auth.login_sucesso", usuario_id=sistema.id)
    assert do_sistema.id not in _ids(client_admin.get("/eventos", params={"limit": 200}))


def test_conta_de_sistema_continua_vendo_os_proprios_eventos(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    sistema = _usuario_sistema(db_session, empresa)
    proprio = _evento(db_session, empresa, tipo="auth.login_sucesso", usuario_id=sistema.id)
    normal = _evento(db_session, empresa, tipo="auth.login_sucesso", usuario_id=usuario_operador.id)
    ids = _ids(_client_para(app, sistema).get("/eventos", params={"tipo": "auth.login_sucesso", "limit": 200}))
    assert proprio.id in ids and normal.id in ids


def test_get_evento_por_id_segue_a_mesma_politica(
    app, client_gestor: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    sistema = _usuario_sistema(db_session, empresa)
    do_sistema = _evento(db_session, empresa, tipo="auth.login_sucesso", usuario_id=sistema.id)
    normal = _evento(db_session, empresa, tipo="auth.login_sucesso", usuario_id=usuario_operador.id)
    automatico = _evento(db_session, empresa, tipo="demanda.status_alterado", usuario_id=None, entidade_tipo="demanda")

    assert client_gestor.get(f"/eventos/{do_sistema.id}").status_code == 404
    assert client_gestor.get(f"/eventos/{normal.id}").status_code == 200
    assert client_gestor.get(f"/eventos/{automatico.id}").status_code == 200
    assert _client_para(app, sistema).get(f"/eventos/{do_sistema.id}").status_code == 200


def test_eventos_historicos_nao_sao_apagados(
    client_gestor: TestClient, db_session: Session, empresa: Empresa
) -> None:
    sistema = _usuario_sistema(db_session, empresa)
    for _ in range(3):
        _evento(db_session, empresa, tipo="auth.login_sucesso", usuario_id=sistema.id)
    antes = db_session.scalar(select(func.count()).select_from(Evento).where(Evento.usuario_id == sistema.id))
    client_gestor.get("/eventos", params={"limit": 200})
    depois = db_session.scalar(select(func.count()).select_from(Evento).where(Evento.usuario_id == sistema.id))
    assert antes == depois == 3


# --------------------------------------------------------------------------------------
# Histórico de Demanda
# --------------------------------------------------------------------------------------


def test_historico_de_demanda_oculta_passos_da_conta_de_sistema_para_o_tenant(
    app, client_gestor: TestClient, db_session: Session, empresa: Empresa, usuario_gestor: Usuario
) -> None:
    """HISTORICO_DEMANDA_EXPOE_SYSTEM_ACCOUNT era SIM (o evento carregava `usuarioId` da conta de sistema);
    agora o tenant não vê esses passos, e os passos do próprio gestor e os automáticos continuam."""
    sistema = _usuario_sistema(db_session, empresa)
    cliente_sistema = _client_para(app, sistema)
    criada = cliente_sistema.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:6]}"})
    assert criada.status_code == 201, criada.text
    demanda_id = criada.json()["id"]

    do_sistema = cliente_sistema.get(f"/demandas/{demanda_id}/historico")
    assert do_sistema.status_code == 200
    ids_sistema = {e["id"] for e in do_sistema.json()}
    assert ids_sistema, "a própria conta de sistema deve enxergar a timeline"
    assert all(e["usuarioId"] == sistema.id for e in do_sistema.json() if e["usuarioId"])

    # O tenant (gestor) não vê os passos cujo ator é a conta de sistema…
    do_gestor = client_gestor.get(f"/demandas/{demanda_id}/historico")
    assert do_gestor.status_code == 200
    assert not any(e["usuarioId"] == sistema.id for e in do_gestor.json())
    assert not (ids_sistema & {e["id"] for e in do_gestor.json()})

    # …mas vê os próprios passos.
    alterada = client_gestor.patch(f"/demandas/{demanda_id}", json={"nome": "Renomeada pelo gestor"})
    assert alterada.status_code == 200, alterada.text
    depois = client_gestor.get(f"/demandas/{demanda_id}/historico").json()
    assert any(e["usuarioId"] == usuario_gestor.id for e in depois)

    # O evento da conta de sistema continua no banco e visível para ela.
    assert ids_sistema <= {e["id"] for e in cliente_sistema.get(f"/demandas/{demanda_id}/historico").json()}
