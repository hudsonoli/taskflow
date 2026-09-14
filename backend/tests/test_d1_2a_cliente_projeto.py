"""D1.2A — Integridade Cliente ↔ Projeto na criação de Demandas (Fase 2G.10B).

Política C do diagnóstico: bloqueia SOMENTE o mismatch verdadeiro — `Projeto.cliente_id` e
`Demanda.cliente_id` preenchidos e diferentes. Projeto interno (`cliente_id IS NULL`) e
ausência de cliente na Demanda continuam livremente compatíveis com qualquer combinação —
não há inferência automática de cliente nem alteração silenciosa de payload.

Fora de escopo (não tocado): limites de Head/Atendimento/Operador-com-grant (D1.2B/C/D),
frontend/diretórios (D1.2E), `update_demanda` (a validação vive só na criação nesta fase).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.projeto import Projeto
from fastapi.testclient import TestClient

from tests.test_demanda import _cliente, _criar, _payload


def _projeto(db: Session, empresa: Empresa, *, cliente_id: str | None = None, status: str = "planejamento") -> Projeto:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    projeto = Projeto(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_referencia=f"P26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Projeto {sufixo}",
        nome_normalizado=f"projeto {sufixo}",
        status=status,
        prioridade="media",
        cliente_id=cliente_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(projeto)
    db.flush()
    return projeto


# --------------------------------------------------------------------------------------
# Casos aceitos (A-F do kickoff).
# --------------------------------------------------------------------------------------


def test_sem_projeto_sem_cliente(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    assert criada["projetoId"] is None
    assert criada["clienteId"] is None


def test_sem_projeto_com_cliente(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    criada = _criar(client_admin, clienteId=cliente.id)
    assert criada["clienteId"] == cliente.id
    assert criada["projetoId"] is None


def test_projeto_interno_sem_cliente_na_demanda(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa, cliente_id=None)
    criada = _criar(client_admin, projetoId=projeto.id)
    assert criada["projetoId"] == projeto.id
    assert criada["clienteId"] is None


def test_projeto_interno_com_cliente_na_demanda(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa, cliente_id=None)
    cliente = _cliente(db_session, empresa)
    criada = _criar(client_admin, projetoId=projeto.id, clienteId=cliente.id)
    assert criada["projetoId"] == projeto.id
    assert criada["clienteId"] == cliente.id


def test_projeto_com_cliente_e_demanda_com_mesmo_cliente(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)
    criada = _criar(client_admin, projetoId=projeto.id, clienteId=cliente.id)
    assert criada["projetoId"] == projeto.id
    assert criada["clienteId"] == cliente.id


def test_projeto_com_cliente_e_demanda_sem_cliente(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)
    criada = _criar(client_admin, projetoId=projeto.id)
    assert criada["projetoId"] == projeto.id
    assert criada["clienteId"] is None


# --------------------------------------------------------------------------------------
# Caso bloqueado (G do kickoff) — o teste central deste bloco.
# --------------------------------------------------------------------------------------


def test_projeto_com_cliente_a_e_demanda_com_cliente_b_e_rejeitado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_a = _cliente(db_session, empresa)
    cliente_b = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente_a.id)

    resposta = client_admin.post(
        "/demandas", json=_payload(projetoId=projeto.id, clienteId=cliente_b.id)
    )

    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Projeto não pertence ao cliente informado"
    # Nenhum dado de outro cliente vaza na mensagem.
    assert cliente_a.id not in resposta.json()["detail"]
    assert cliente_b.id not in resposta.json()["detail"]


# --------------------------------------------------------------------------------------
# Numeração — mismatch nunca reserva número operacional nem código de referência.
# --------------------------------------------------------------------------------------


def test_mismatch_nao_reserva_numeracao(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente_a = _cliente(db_session, empresa)
    cliente_b = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente_a.id)

    total_antes = db_session.execute(
        text("SELECT COUNT(*) FROM demandas WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    ultimo_antes = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_operacionais "
            "WHERE empresa_id = :e AND tipo_entidade = 'demanda'"
        ),
        {"e": empresa.id},
    ).scalar_one_or_none()

    resposta = client_admin.post(
        "/demandas", json=_payload(projetoId=projeto.id, clienteId=cliente_b.id)
    )
    assert resposta.status_code == 422

    total_depois = db_session.execute(
        text("SELECT COUNT(*) FROM demandas WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    ultimo_depois = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_operacionais "
            "WHERE empresa_id = :e AND tipo_entidade = 'demanda'"
        ),
        {"e": empresa.id},
    ).scalar_one_or_none()

    assert total_depois == total_antes, "mismatch não pode ter criado Demanda"
    assert ultimo_depois == ultimo_antes, "mismatch não pode ter reservado numero_operacional"


def test_mismatch_nao_gera_evento(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente_a = _cliente(db_session, empresa)
    cliente_b = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente_a.id)

    total_eventos_antes = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()

    resposta = client_admin.post(
        "/demandas", json=_payload(projetoId=projeto.id, clienteId=cliente_b.id)
    )
    assert resposta.status_code == 422

    total_eventos_depois = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    assert total_eventos_depois == total_eventos_antes, "mismatch não pode ter publicado evento"


# --------------------------------------------------------------------------------------
# Tenant — comportamento cross-tenant preservado (422, nunca 403/404, doutrina inalterada).
# --------------------------------------------------------------------------------------


def test_cliente_de_outra_empresa_continua_422(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    cliente_alheio = _cliente(db_session, outra_empresa)
    resposta = client_admin.post("/demandas", json=_payload(clienteId=cliente_alheio.id))
    assert resposta.status_code == 422


def test_projeto_de_outra_empresa_continua_422(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    projeto_alheio = _projeto(db_session, outra_empresa)
    resposta = client_admin.post("/demandas", json=_payload(projetoId=projeto_alheio.id))
    assert resposta.status_code == 422


# --------------------------------------------------------------------------------------
# Projeto/cliente arquivado — mecanismo atual preservado, não mascarado pela nova regra.
# --------------------------------------------------------------------------------------


def test_projeto_arquivado_continua_422_mesmo_com_cliente_compativel(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id, status="arquivado")
    resposta = client_admin.post(
        "/demandas", json=_payload(projetoId=projeto.id, clienteId=cliente.id)
    )
    assert resposta.status_code == 422
    assert "arquivado" in resposta.json()["detail"].lower()


def test_cliente_arquivado_continua_422(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    cliente.status = "arquivado"
    db_session.flush()
    resposta = client_admin.post("/demandas", json=_payload(clienteId=cliente.id))
    assert resposta.status_code == 422
    assert "arquivado" in resposta.json()["detail"].lower()


# --------------------------------------------------------------------------------------
# Query count — evidência de que a nova checagem não adiciona SELECT extra. Conta só
# consultas à tabela `projetos`: `_ensure_projeto_valido` carrega o Projeto no máximo uma
# vez (via `db.get()`, que pode ser satisfeito pelo identity map da sessão sem emitir SQL
# quando o objeto já foi criado na mesma sessão — daí `<= 1`, não `== 1`: o teste prova a
# ausência de uma SEGUNDA consulta, não força um número exato que depende de cache);
# `_ensure_projeto_compativel_com_cliente` só lê o atributo `.cliente_id` do objeto Python
# já em memória, sem tocar o banco de novo — por isso nunca poderia gerar uma segunda
# consulta, com ou sem cache.
# --------------------------------------------------------------------------------------


def test_criacao_com_projeto_compativel_nao_gera_segunda_consulta_a_projetos(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)

    chamadas: list[str] = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "FROM projetos" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = client_admin.post(
            "/demandas", json=_payload(projetoId=projeto.id, clienteId=cliente.id)
        )
    finally:
        event.remove(engine, "before_cursor_execute", _contar)

    assert resposta.status_code == 201, resposta.text
    assert len(chamadas) <= 1, f"esperada no máximo 1 consulta a projetos (nunca uma segunda), houve {len(chamadas)}"
