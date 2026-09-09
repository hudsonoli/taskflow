"""Configuração de Numeração de tarefas — leitura real (Fase 2G.8B).

`GET /configuracoes/numeracao-tarefas` é estritamente read-only: nunca chama
`reservar_proximo_operacional`, nunca insere/atualiza `sequencias_operacionais`. Cobre
admin/gestor/operador, tenant, contador ausente vs presente, maior número emitido,
consistência, e a garantia de que leituras repetidas nunca alteram o banco nem geram Evento.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.sequencia_operacional import SequenciaOperacional
from tests.fixtures.usuarios import _criar_usuario_com_credencial

# --------------------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------------------


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _seed_sequencia(
    db: Session, empresa_id: str, *, ultimo_numero: int, tipo_entidade: str = "demanda"
) -> SequenciaOperacional:
    agora = datetime.now(timezone.utc)
    seq = SequenciaOperacional(
        id=str(uuid.uuid4()),
        empresa_id=empresa_id,
        tipo_entidade=tipo_entidade,
        ultimo_numero=ultimo_numero,
        created_at=agora,
        updated_at=agora,
    )
    db.add(seq)
    db.flush()
    return seq


def _registro(db: Session, empresa_id: str) -> SequenciaOperacional:
    return db.scalars(
        select(SequenciaOperacional).where(
            SequenciaOperacional.empresa_id == empresa_id, SequenciaOperacional.tipo_entidade == "demanda"
        )
    ).one()


def _cliente_para_outra_empresa(
    app, db_session: Session, outra_empresa: Empresa, perfil_base: str = "admin"
) -> TestClient:
    """Mesmo padrão de test_regra_expediente.py/test_configuracao_email.py."""
    usuario = _criar_usuario_com_credencial(
        db_session, empresa=outra_empresa, perfil_base=perfil_base, email_prefixo=perfil_base
    )
    db_session.flush()
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=perfil_base)
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


# --------------------------------------------------------------------------------------
# A-C: permissões
# --------------------------------------------------------------------------------------


def test_a_admin_le_200(client_admin: TestClient) -> None:
    resposta = client_admin.get("/configuracoes/numeracao-tarefas")
    assert resposta.status_code == 200, resposta.text


def test_b_gestor_le_200(client_gestor: TestClient) -> None:
    assert client_gestor.get("/configuracoes/numeracao-tarefas").status_code == 200


def test_c_operador_403(client_operador: TestClient) -> None:
    assert client_operador.get("/configuracoes/numeracao-tarefas").status_code == 403


# --------------------------------------------------------------------------------------
# D-F: contador ausente/presente/próximo
# --------------------------------------------------------------------------------------


def test_d_sem_contador_atual_zero_proximo_um(client_admin: TestClient) -> None:
    corpo = client_admin.get("/configuracoes/numeracao-tarefas").json()
    assert corpo["contadorAtual"] == 0
    assert corpo["proximoNumeroEstimado"] == 1
    assert corpo["maiorNumeroEmitido"] is None
    assert corpo["consistente"] is True
    assert corpo["entidade"] == "demanda"
    assert corpo["rotuloEntidade"] == "Tarefa"
    assert corpo["gerenciadoAutomaticamente"] is True
    assert "empresaId" not in corpo


def test_e_contador_existente_atual_correto(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    _seed_sequencia(db_session, empresa.id, ultimo_numero=2062)
    corpo = client_admin.get("/configuracoes/numeracao-tarefas").json()
    assert corpo["contadorAtual"] == 2062


def test_f_proximo_e_atual_mais_um(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    _seed_sequencia(db_session, empresa.id, ultimo_numero=41)
    corpo = client_admin.get("/configuracoes/numeracao-tarefas").json()
    assert corpo["proximoNumeroEstimado"] == 42


# --------------------------------------------------------------------------------------
# G-H: read-only de verdade
# --------------------------------------------------------------------------------------


def test_g_get_nao_incrementa_contador(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    _seed_sequencia(db_session, empresa.id, ultimo_numero=10)
    client_admin.get("/configuracoes/numeracao-tarefas")
    assert _registro(db_session, empresa.id).ultimo_numero == 10


def test_h_duas_leituras_nao_alteram_banco(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    _seed_sequencia(db_session, empresa.id, ultimo_numero=5)
    primeira = client_admin.get("/configuracoes/numeracao-tarefas").json()
    segunda = client_admin.get("/configuracoes/numeracao-tarefas").json()
    assert primeira == segunda
    assert _registro(db_session, empresa.id).ultimo_numero == 5


# --------------------------------------------------------------------------------------
# I-K: maior número emitido / consistência
# --------------------------------------------------------------------------------------


def test_i_maior_numero_emitido_correto(client_admin: TestClient) -> None:
    _criar_demanda(client_admin)
    _criar_demanda(client_admin)
    terceira = _criar_demanda(client_admin)
    corpo = client_admin.get("/configuracoes/numeracao-tarefas").json()
    assert corpo["maiorNumeroEmitido"] == terceira["numeroOperacional"]
    assert corpo["contadorAtual"] == terceira["numeroOperacional"]


def test_j_contador_maior_que_emitido_e_consistente(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Cenário legítimo do kickoff (item 5): contador inicializado acima do que já foi
    emitido pelo próprio TaskFloww — continuidade com sistema anterior, não anomalia."""
    demanda = _criar_demanda(client_admin)  # numero_operacional = 1, sequencia criada com ultimo_numero = 1
    registro = _registro(db_session, empresa.id)
    registro.ultimo_numero = 2062
    db_session.flush()

    corpo = client_admin.get("/configuracoes/numeracao-tarefas").json()
    assert corpo["contadorAtual"] == 2062
    assert corpo["maiorNumeroEmitido"] == demanda["numeroOperacional"]
    assert corpo["consistente"] is True


def test_k_contador_menor_que_emitido_e_inconsistente(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    demanda = _criar_demanda(client_admin)  # numero_operacional = 1
    registro = _registro(db_session, empresa.id)
    registro.ultimo_numero = 0  # anomalia: contador ficou para trás do que já foi emitido
    db_session.flush()

    corpo = client_admin.get("/configuracoes/numeracao-tarefas").json()
    assert corpo["contadorAtual"] == 0
    assert corpo["maiorNumeroEmitido"] == demanda["numeroOperacional"]
    assert corpo["consistente"] is False


# --------------------------------------------------------------------------------------
# L-M: tenant
# --------------------------------------------------------------------------------------


def test_l_tenant_isolation(
    app, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    _seed_sequencia(db_session, empresa.id, ultimo_numero=999)
    cliente_outra = _cliente_para_outra_empresa(app, db_session, outra_empresa)
    corpo_outra = cliente_outra.get("/configuracoes/numeracao-tarefas").json()
    assert corpo_outra["contadorAtual"] == 0  # não vê o contador da outra Empresa


def test_m_query_de_empresa_arbitraria_e_ignorada(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    _seed_sequencia(db_session, outra_empresa.id, ultimo_numero=777)
    corpo = client_admin.get(f"/configuracoes/numeracao-tarefas?empresaId={outra_empresa.id}").json()
    assert corpo["contadorAtual"] == 0  # ignora o query param; empresa vem só de current_user


# --------------------------------------------------------------------------------------
# N: nenhuma escrita/evento
# --------------------------------------------------------------------------------------


def test_n_get_nao_produz_evento(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    antes = len(db_session.scalars(select(Evento).where(Evento.empresa_id == empresa.id)).all())
    client_admin.get("/configuracoes/numeracao-tarefas")
    depois = len(db_session.scalars(select(Evento).where(Evento.empresa_id == empresa.id)).all())
    assert depois == antes
