"""D1.2A-UPDATE — Integridade Cliente ↔ Projeto no PATCH /demandas/{id} (Fase 2G.10B).

Mesma Política C do D1.2A (criação): bloqueia SOMENTE o mismatch verdadeiro — `Projeto.
cliente_id` e `Demanda.cliente_id` preenchidos e diferentes. A diferença do PATCH para o
POST é que a validação precisa olhar o ESTADO FINAL da Demanda, não só os campos enviados:
um PATCH que só troca cliente OU só projeto ainda pode colidir com o lado que ficou parado.

Fora de escopo (não tocado): POST/`create_demanda` (regra já fechada no D1.2A), D1.1
(elegibilidade de criação), D1.2B/C/D/E (limites de Head/Atendimento/Operador-com-grant,
frontend), `core/permissoes.py`, `dependencies/permissoes.py`, `core/escopo.py`.
"""

from __future__ import annotations

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from fastapi.testclient import TestClient

from tests.test_d1_2a_cliente_projeto import _projeto
from tests.test_demanda import _cliente, _criar


# --------------------------------------------------------------------------------------
# Casos aceitos (1-4, 7-9 do checklist).
# --------------------------------------------------------------------------------------


def test_patch_sem_cliente_e_sem_projeto_retorna_200(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    criada = _criar(client_admin, clienteId=cliente.id)

    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={})

    assert resposta.status_code == 200, resposta.text


def test_patch_reenvia_mesmo_cliente_retorna_200(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)
    criada = _criar(client_admin, clienteId=cliente.id, projetoId=projeto.id)

    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"clienteId": cliente.id}
    )

    assert resposta.status_code == 200, resposta.text


def test_patch_reenvia_mesmo_projeto_retorna_200(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)
    criada = _criar(client_admin, clienteId=cliente.id, projetoId=projeto.id)

    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"projetoId": projeto.id}
    )

    assert resposta.status_code == 200, resposta.text


def test_patch_troca_cliente_e_projeto_para_par_compativel_retorna_200(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_a = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_a.id)

    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)

    resposta = client_admin.patch(
        f"/demandas/{criada['id']}",
        json={"clienteId": cliente_b.id, "projetoId": projeto_b.id},
    )

    assert resposta.status_code == 200, resposta.text


def test_patch_limpa_cliente_mantendo_projeto_retorna_200(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)
    criada = _criar(client_admin, clienteId=cliente.id, projetoId=projeto.id)

    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"clienteId": None})

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["clienteId"] is None
    assert resposta.json()["projetoId"] == projeto.id


def test_patch_limpa_projeto_mantendo_cliente_retorna_200(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)
    criada = _criar(client_admin, clienteId=cliente.id, projetoId=projeto.id)

    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"projetoId": None})

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["projetoId"] is None
    assert resposta.json()["clienteId"] == cliente.id


def test_patch_troca_cliente_com_projeto_interno_intocado_retorna_200(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_a = _cliente(db_session, empresa)
    projeto_interno = _projeto(db_session, empresa, cliente_id=None)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_interno.id)

    cliente_b = _cliente(db_session, empresa)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"clienteId": cliente_b.id}
    )

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["clienteId"] == cliente_b.id
    assert resposta.json()["projetoId"] == projeto_interno.id


# --------------------------------------------------------------------------------------
# Casos bloqueados (5-6 do checklist) — o par final colide mesmo só um lado tendo mudado.
# --------------------------------------------------------------------------------------


def test_patch_troca_so_cliente_gerando_mismatch_e_rejeitado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_a = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_a.id)

    cliente_b = _cliente(db_session, empresa)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"clienteId": cliente_b.id}
    )

    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Projeto não pertence ao cliente informado"

    relida = client_admin.get(f"/demandas/{criada['id']}").json()
    assert relida["clienteId"] == cliente_a.id, "cliente não pode ter mudado no mismatch"
    assert relida["projetoId"] == projeto_a.id, "projeto não pode ter mudado no mismatch"


def test_patch_troca_so_projeto_gerando_mismatch_e_rejeitado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_a = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_a.id)

    cliente_c = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_c.id)

    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"projetoId": projeto_b.id}
    )

    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Projeto não pertence ao cliente informado"

    relida = client_admin.get(f"/demandas/{criada['id']}").json()
    assert relida["clienteId"] == cliente_a.id, "cliente não pode ter mudado no mismatch"
    assert relida["projetoId"] == projeto_a.id, "projeto não pode ter mudado no mismatch"


# --------------------------------------------------------------------------------------
# Estado — nenhuma alteração parcial sobrevive ao rollback (item 11 do kickoff).
# --------------------------------------------------------------------------------------


def test_mismatch_por_patch_nao_altera_estado_persistido(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_a = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_a.id)

    cliente_b = _cliente(db_session, empresa)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"clienteId": cliente_b.id}
    )
    assert resposta.status_code == 422

    linha = db_session.execute(
        text("SELECT cliente_id, projeto_id, updated_at FROM demandas WHERE id = :id"),
        {"id": criada["id"]},
    ).one()
    assert linha.cliente_id == cliente_a.id
    assert linha.projeto_id == projeto_a.id


# --------------------------------------------------------------------------------------
# Eventos — mismatch por PATCH não publica DEMANDA_ALTERADA nem nenhum outro (item 12).
# --------------------------------------------------------------------------------------


def test_mismatch_por_patch_nao_gera_evento(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_a = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_a.id)

    total_eventos_antes = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()

    cliente_b = _cliente(db_session, empresa)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"clienteId": cliente_b.id}
    )
    assert resposta.status_code == 422

    total_eventos_depois = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    assert total_eventos_depois == total_eventos_antes, "mismatch não pode ter publicado evento"


# --------------------------------------------------------------------------------------
# Tenant — cross-tenant continua 422 antes mesmo da checagem de compatibilidade (10-11).
# --------------------------------------------------------------------------------------


def test_patch_cliente_de_outra_empresa_continua_422(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    cliente_a = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_a.id)

    cliente_alheio = _cliente(db_session, outra_empresa)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"clienteId": cliente_alheio.id}
    )

    assert resposta.status_code == 422, resposta.text


def test_patch_projeto_de_outra_empresa_continua_422(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    cliente_a = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_a.id)

    projeto_alheio = _projeto(db_session, outra_empresa)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"projetoId": projeto_alheio.id}
    )

    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Arquivado — novo vínculo arquivado continua 422 por conta própria, não por mismatch (12-13).
# --------------------------------------------------------------------------------------


def test_patch_novo_cliente_arquivado_continua_422(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    criada = _criar(client_admin)

    cliente_arquivado = _cliente(db_session, empresa)
    cliente_arquivado.status = "arquivado"
    db_session.flush()

    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"clienteId": cliente_arquivado.id}
    )

    assert resposta.status_code == 422, resposta.text
    assert "arquivado" in resposta.json()["detail"].lower()


def test_patch_novo_projeto_arquivado_continua_422(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    criada = _criar(client_admin)

    projeto_arquivado = _projeto(db_session, empresa, status="arquivado")

    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"projetoId": projeto_arquivado.id}
    )

    assert resposta.status_code == 422, resposta.text
    assert "arquivado" in resposta.json()["detail"].lower()


def test_patch_projeto_atual_arquivado_por_fora_nao_bloqueia_troca_de_cliente(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Projeto JÁ vinculado, arquivado por fora deste PATCH: o fetch cru do estado final é
    só leitura de `cliente_id`, nunca `_ensure_projeto_valido` — arquivar o projeto depois
    de vinculado não pode passar a bloquear um PATCH que não está tentando trocá-lo."""
    cliente_a = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_a.id)

    projeto_a.status = "arquivado"
    db_session.flush()

    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"clienteId": cliente_a.id}
    )

    assert resposta.status_code == 200, resposta.text


# --------------------------------------------------------------------------------------
# Query count — item 13 do kickoff. Conta só "FROM projetos": prova ausência de segunda
# consulta (não força um número exato — mesma ressalva de identity map do D1.2A/POST).
# --------------------------------------------------------------------------------------


def _contar_consultas_a_projetos(db_session: Session, acao) -> int:
    chamadas: list[str] = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "FROM projetos" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        acao()
    finally:
        event.remove(engine, "before_cursor_execute", _contar)
    return len(chamadas)


def test_patch_sem_cliente_e_sem_projeto_nao_consulta_projetos(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)
    criada = _criar(client_admin, clienteId=cliente.id, projetoId=projeto.id)

    resultado = {}

    def _acao():
        resultado["resposta"] = client_admin.patch(f"/demandas/{criada['id']}", json={"nome": "Outro nome"})

    chamadas = _contar_consultas_a_projetos(db_session, _acao)

    assert resultado["resposta"].status_code == 200, resultado["resposta"].text
    assert chamadas == 0, "PATCH que não toca cliente/projeto não pode consultar projetos"


def test_patch_so_projeto_reaproveita_projeto_ja_carregado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente.id)
    criada = _criar(client_admin, clienteId=cliente.id, projetoId=projeto_a.id)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente.id)

    resultado = {}

    def _acao():
        resultado["resposta"] = client_admin.patch(
            f"/demandas/{criada['id']}", json={"projetoId": projeto_b.id}
        )

    chamadas = _contar_consultas_a_projetos(db_session, _acao)

    assert resultado["resposta"].status_code == 200, resultado["resposta"].text
    assert chamadas <= 1, f"esperada no máximo 1 consulta a projetos, houve {chamadas}"


def test_patch_so_cliente_com_projeto_atual_faz_no_maximo_um_fetch(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """`projeto_id` não está em `updates`, mas a Demanda já tem projeto — o único jeito de
    validar o par final é buscar o `cliente_id` do Projeto atual (fetch cru, sem revalidar
    tenant/arquivado). Reenviar o mesmo cliente já dispara esse fetch, porque "tocado"
    significa "a chave está em `updates`", não "o valor mudou" — ver diagnóstico, seção 7."""
    cliente_a = _cliente(db_session, empresa)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    criada = _criar(client_admin, clienteId=cliente_a.id, projetoId=projeto_a.id)

    resultado = {}

    def _acao():
        resultado["resposta"] = client_admin.patch(
            f"/demandas/{criada['id']}", json={"clienteId": cliente_a.id}
        )

    chamadas = _contar_consultas_a_projetos(db_session, _acao)

    assert resultado["resposta"].status_code == 200, resultado["resposta"].text
    assert chamadas <= 1, f"esperado no máximo 1 fetch adicional do Projeto atual, houve {chamadas}"
