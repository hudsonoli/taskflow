"""D1.2B — Limites de contexto para Head em Demandas (Fase 2G.10B).

Política HEAD-A: quando o ator É Head de verdade (`departamentos_como_head` não-vazio),
`departamento_responsavel_ids` só pode conter departamentos que ele lidera —
`set(desejados) ⊆ set(departamentos_como_head(actor))`. Qualquer item fora rejeita o
payload INTEIRO (nunca remove silenciosamente).

Gatilhada por "é Head", nunca por "não é admin/gestor": admin/gestor sempre livres (zero
query); um ator que não é Head de nada (Atendimento sem relação de Head, Operador com
`demandas.criar`/`demandas.editar` concedido por override) não aciona a regra — essas
categorias ficam deliberadamente fora até D1.2C/D1.2D.

Fora de escopo (não tocado): responsavel_ids, cliente_id/projeto_id (D1.2A/D1.2A-UPDATE
intactos), workflow_modelo_id, frontend, D1.1 (permissão de chamar a rota).
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa

from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _client_para, _head_por_responsavel, _operador_comum, _override
from tests.test_demanda import _departamento, _criar, _payload


def _admin_da_empresa(db: Session, empresa: Empresa):
    return _criar_usuario_com_credencial(
        db, empresa=empresa, perfil_base="admin", email_prefixo="admin-d1-2b"
    )


# --------------------------------------------------------------------------------------
# Create — Head de um único departamento (item 24, casos 1-5).
# --------------------------------------------------------------------------------------


def test_head_a_cria_com_a_retorna_201(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-a-1")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    resposta = _client_para(app, head).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_a.id])
    )
    assert resposta.status_code == 201, resposta.text


def test_head_a_cria_com_lista_vazia_retorna_201(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-a-2")
    _head_por_responsavel(db_session, empresa, head)
    resposta = _client_para(app, head).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[])
    )
    assert resposta.status_code == 201, resposta.text


def test_head_a_cria_com_null_retorna_201(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-a-3")
    _head_por_responsavel(db_session, empresa, head)
    resposta = _client_para(app, head).post(
        "/demandas", json=_payload(departamentoResponsavelIds=None)
    )
    assert resposta.status_code == 201, resposta.text


def test_head_a_cria_com_b_e_rejeitado(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-a-4")
    _head_por_responsavel(db_session, empresa, head)
    departamento_b = _departamento(db_session, empresa, nome="Criação")
    resposta = _client_para(app, head).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_b.id])
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Departamento responsável não permitido para este usuário"


def test_head_a_cria_com_a_e_b_e_rejeitado(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-a-5")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    departamento_b = _departamento(db_session, empresa, nome="Mídia")
    resposta = _client_para(app, head).post(
        "/demandas",
        json=_payload(departamentoResponsavelIds=[departamento_a.id, departamento_b.id]),
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Create — Head multidepartamento (item 24, casos 6-9; item 14).
# --------------------------------------------------------------------------------------


def test_head_a_e_b_cria_com_a_retorna_201(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-ab-1")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    _head_por_responsavel(db_session, empresa, head)  # segundo departamento liderado
    resposta = _client_para(app, head).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_a.id])
    )
    assert resposta.status_code == 201, resposta.text


def test_head_a_e_b_cria_com_b_retorna_201(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-ab-2")
    _head_por_responsavel(db_session, empresa, head)
    departamento_b = _head_por_responsavel(db_session, empresa, head)
    resposta = _client_para(app, head).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_b.id])
    )
    assert resposta.status_code == 201, resposta.text


def test_head_a_e_b_cria_com_a_e_b_retorna_201(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-ab-3")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    departamento_b = _head_por_responsavel(db_session, empresa, head)
    resposta = _client_para(app, head).post(
        "/demandas",
        json=_payload(departamentoResponsavelIds=[departamento_a.id, departamento_b.id]),
    )
    assert resposta.status_code == 201, resposta.text


def test_head_a_e_b_cria_com_a_e_x_e_rejeitado(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-ab-4")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    _head_por_responsavel(db_session, empresa, head)
    departamento_x = _departamento(db_session, empresa, nome="Fora")
    resposta = _client_para(app, head).post(
        "/demandas",
        json=_payload(departamentoResponsavelIds=[departamento_a.id, departamento_x.id]),
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Numeração — rejeição por Head não reserva nada (item 25).
# --------------------------------------------------------------------------------------


def test_head_a_rejeitado_com_b_nao_reserva_numeracao_nem_gera_evento(
    app, db_session: Session, empresa: Empresa
) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-num")
    _head_por_responsavel(db_session, empresa, head)
    departamento_b = _departamento(db_session, empresa, nome="Fora-num")

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
    max_antes = db_session.execute(
        text("SELECT MAX(numero_operacional) FROM demandas WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one_or_none()
    eventos_antes = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()

    resposta = _client_para(app, head).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_b.id])
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
    max_depois = db_session.execute(
        text("SELECT MAX(numero_operacional) FROM demandas WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one_or_none()
    eventos_depois = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()

    assert total_depois == total_antes, "rejeição de Head não pode ter criado Demanda"
    assert ultimo_depois == ultimo_antes, "rejeição de Head não pode ter reservado numero_operacional"
    assert max_depois == max_antes, "rejeição de Head não pode ter avançado numero_operacional"
    assert eventos_depois == eventos_antes, "rejeição de Head não pode ter publicado evento"


# --------------------------------------------------------------------------------------
# Patch (item 26).
# --------------------------------------------------------------------------------------


def test_head_a_patch_para_a_retorna_200(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-patch-1")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    client = _client_para(app, head)
    criada = _criar(client, departamentoResponsavelIds=[departamento_a.id])

    resposta = client.patch(
        f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": [departamento_a.id]}
    )
    assert resposta.status_code == 200, resposta.text


def test_head_a_patch_para_b_e_rejeitado(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-patch-2")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    departamento_b = _departamento(db_session, empresa, nome="Fora-patch-2")
    client = _client_para(app, head)
    criada = _criar(client, departamentoResponsavelIds=[departamento_a.id])

    resposta = client.patch(
        f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": [departamento_b.id]}
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Departamento responsável não permitido para este usuário"


def test_head_a_patch_para_a_e_b_e_rejeitado(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-patch-3")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    departamento_b = _departamento(db_session, empresa, nome="Fora-patch-3")
    client = _client_para(app, head)
    criada = _criar(client, departamentoResponsavelIds=[departamento_a.id])

    resposta = client.patch(
        f"/demandas/{criada['id']}",
        json={"departamentoResponsavelIds": [departamento_a.id, departamento_b.id]},
    )
    assert resposta.status_code == 422, resposta.text


def test_head_a_patch_lista_vazia_retorna_200(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-patch-4")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    client = _client_para(app, head)
    criada = _criar(client, departamentoResponsavelIds=[departamento_a.id])

    resposta = client.patch(f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": []})
    assert resposta.status_code == 200, resposta.text


def test_head_a_patch_null_retorna_200(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-patch-5")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    client = _client_para(app, head)
    criada = _criar(client, departamentoResponsavelIds=[departamento_a.id])

    resposta = client.patch(f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": None})
    assert resposta.status_code == 200, resposta.text


def test_patch_sem_tocar_departamentos_nao_aciona_d1_2b(
    app, db_session: Session, empresa: Empresa
) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-patch-6")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    client = _client_para(app, head)
    criada = _criar(client, departamentoResponsavelIds=[departamento_a.id])

    resposta = client.patch(f"/demandas/{criada['id']}", json={"nome": "Nome ajustado"})
    assert resposta.status_code == 200, resposta.text


# --------------------------------------------------------------------------------------
# Estado/eventos — mismatch no PATCH não muda nada nem publica evento (item 27).
# --------------------------------------------------------------------------------------


def test_patch_mismatch_departamento_nao_altera_lista_nem_gera_evento(
    app, db_session: Session, empresa: Empresa
) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-estado")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    departamento_b = _departamento(db_session, empresa, nome="Fora-estado")
    client = _client_para(app, head)
    criada = _criar(client, departamentoResponsavelIds=[departamento_a.id])

    eventos_antes = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()

    resposta = client.patch(
        f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": [departamento_b.id]}
    )
    assert resposta.status_code == 422

    eventos_depois = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    assert eventos_depois == eventos_antes, "mismatch de departamento não pode ter publicado evento"

    relida = client.get(f"/demandas/{criada['id']}").json()
    assert relida["departamentoResponsavelIds"] == [departamento_a.id], (
        "lista de departamentos não pode ter mudado (nem parcialmente) num PATCH rejeitado"
    )


# --------------------------------------------------------------------------------------
# Dado legado — campo intocado não aciona a regra mesmo com combinação antiga inválida
# para o Head atual (item 13/28).
# --------------------------------------------------------------------------------------


def test_patch_de_nome_nao_valida_departamentos_legados_fora_do_escopo(
    app, db_session: Session, empresa: Empresa
) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-legado")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    departamento_x = _departamento(db_session, empresa, nome="Legado-x")

    # Só admin/gestor conseguem CRIAR uma demanda com departamento fora do Head — reproduz o
    # "dado legado": [A, X] já existente, Head lidera só A.
    admin_client = _client_para(app, _admin_da_empresa(db_session, empresa))
    criada = _criar(
        admin_client, departamentoResponsavelIds=[departamento_a.id, departamento_x.id]
    )

    resposta = _client_para(app, head).patch(
        f"/demandas/{criada['id']}", json={"nome": "Só o nome mudou"}
    )
    assert resposta.status_code == 200, resposta.text


# --------------------------------------------------------------------------------------
# Operador com grant, não Head — D1.2B não deve restringi-lo (item 16/29).
# --------------------------------------------------------------------------------------


def test_operador_com_grant_nao_head_nao_e_restringido_por_d1_2b(
    app, db_session: Session, empresa: Empresa
) -> None:
    """D1.2B especificamente (a checagem de Head) NUNCA dispara aqui — `departamentos_como_
    head` continua vazio para este operador, então `_ensure_departamentos_permitidos_para_
    head` retorna sem erro, como sempre. A rejeição abaixo vem de D1.2D
    (`_ensure_departamentos_permitidos_para_operador_comum`, Fase 2G.10B): sem departamento
    próprio (`_operador_comum` não define `departamento_id`), o único conjunto permitido é
    vazio — `departamento_b` (não-vazio, alheio) é 422. Antes do D1.2D existir, este mesmo
    cenário retornava 201 (fora de escopo naquela fase); o teste foi atualizado para refletir
    a política aprovada, não uma regressão."""
    operador = _operador_comum(db_session, empresa, sufixo="grant")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")
    departamento_b = _departamento(db_session, empresa, nome="Grant-b")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_b.id])
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Departamento responsável não permitido para este usuário"


# --------------------------------------------------------------------------------------
# Admin/Gestor — sempre livres (item 17/30).
# --------------------------------------------------------------------------------------


def test_admin_nao_head_usa_departamento_qualquer(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento_qualquer = _departamento(db_session, empresa, nome="Admin-livre")
    resposta = client_admin.post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_qualquer.id])
    )
    assert resposta.status_code == 201, resposta.text


def test_gestor_nao_head_usa_departamento_qualquer(
    client_gestor: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento_qualquer = _departamento(db_session, empresa, nome="Gestor-livre")
    resposta = client_gestor.post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_qualquer.id])
    )
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Query/performance — invocações de `departamentos_como_head` no service (item 23/31).
# Monkeypatch em vez de contar SQL: mais estável, prova a INVOCAÇÃO, não uma contagem de
# statement que dependeria do plano/identity map (mesma ressalva já usada em D1.2A/D1.2A-UPDATE).
# --------------------------------------------------------------------------------------


def _contar_chamadas_head(acao) -> int:
    with patch(
        "app.services.demanda_service.departamentos_como_head", wraps=_departamentos_como_head_real()
    ) as mock_head:
        acao()
        return mock_head.call_count


def _departamentos_como_head_real():
    from app.core.escopo import departamentos_como_head

    return departamentos_como_head


def test_create_sem_departamento_nao_chama_departamentos_como_head(
    app, db_session: Session, empresa: Empresa
) -> None:
    head = _operador_comum(db_session, empresa, sufixo="query-1")
    _head_por_responsavel(db_session, empresa, head)
    client = _client_para(app, head)

    resultado = {}

    def _acao():
        resultado["resposta"] = client.post("/demandas", json=_payload())

    chamadas = _contar_chamadas_head(_acao)
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    assert chamadas == 0, "PATCH/POST sem departamento_responsavel_ids não pode chamar departamentos_como_head no service"


def test_create_com_lista_vazia_nao_chama_departamentos_como_head(
    app, db_session: Session, empresa: Empresa
) -> None:
    head = _operador_comum(db_session, empresa, sufixo="query-2")
    _head_por_responsavel(db_session, empresa, head)
    client = _client_para(app, head)

    resultado = {}

    def _acao():
        resultado["resposta"] = client.post(
            "/demandas", json=_payload(departamentoResponsavelIds=[])
        )

    chamadas = _contar_chamadas_head(_acao)
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    assert chamadas == 0, "lista vazia não pode acionar departamentos_como_head no service"


def test_create_admin_nao_chama_departamentos_como_head(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa, nome="Query-admin")

    resultado = {}

    def _acao():
        resultado["resposta"] = client_admin.post(
            "/demandas", json=_payload(departamentoResponsavelIds=[departamento.id])
        )

    chamadas = _contar_chamadas_head(_acao)
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    assert chamadas == 0, "admin/gestor não pode acionar departamentos_como_head no service (D1.2B)"


def test_create_head_com_lista_faz_no_maximo_duas_chamadas(
    app, db_session: Session, empresa: Empresa
) -> None:
    """Desde o D1.2D (Fase 2G.10B), um Head com `departamento_responsavel_ids` não-vazio
    aciona `departamentos_como_head` até DUAS vezes — uma em `_ensure_departamentos_
    permitidos_para_head` (D1.2B, decide o caso dele) e outra em `_ensure_departamentos_
    permitidos_para_operador_comum` (D1.2D, que precisa saber "é Head?" antes de decidir se
    a regra de Operador comum se aplica, e não se aplica). É custo O(1) fixo, não O(n) — não
    depende de quantos departamentos estão no payload nem vira N+1; os dois helpers foram
    mantidos separados de propósito (baixo acoplamento, D1.2B intocado) em vez de unificados
    numa única consulta, aceitando essa segunda chamada como o preço dessa simplicidade."""
    head = _operador_comum(db_session, empresa, sufixo="query-3")
    departamento_a = _head_por_responsavel(db_session, empresa, head)
    client = _client_para(app, head)

    resultado = {}

    def _acao():
        resultado["resposta"] = client.post(
            "/demandas", json=_payload(departamentoResponsavelIds=[departamento_a.id])
        )

    chamadas = _contar_chamadas_head(_acao)
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    assert chamadas <= 2, f"esperadas no máximo 2 chamadas a departamentos_como_head no service, houve {chamadas}"
