"""D1.2C — Limites de contexto para Atendimento em Demandas (Fase 2G.10B).

Política ATEND-B: quando o ator É Atendimento de verdade (`eh_atendimento` verdadeiro), só
pode operar Demandas cujo CLIENTE-CONTEXTO esteja sob sua responsabilidade comercial
(`clientes_sob_responsabilidade`). O contexto é:

1. `cliente_id` final, se preenchido;
2. senão, `Projeto.cliente_id` final, se a Demanda não tem cliente próprio e o Projeto não é
   interno;
3. senão (sem cliente, sem projeto, ou projeto interno) — `None`, sempre permitido.

Nenhuma inferência: o payload nunca é alterado, o contexto é só calculado para VALIDAR.

Gatilhada por "é Atendimento", nunca por perfil: admin/gestor sempre livres (zero query);
Head puro e Operador com override, não-Atendimento, ficam fora desta regra (D1.2D).

Fora de escopo (não tocado): responsavel_ids, workflow_modelo_id, D1.2B (departamentos),
frontend/diretório de clientes (D1.2E).
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa

from tests.test_d1_2a_cliente_projeto import _projeto
from tests.test_d1_criacao_demandas import (
    _atendimento,
    _client_para,
    _head_por_responsavel,
    _operador_comum,
    _override,
)
from tests.test_demanda import _cliente, _criar, _payload


# --------------------------------------------------------------------------------------
# Create — casos aceitos e bloqueados (item 25).
# --------------------------------------------------------------------------------------


def test_atendimento_cria_com_cliente_proprio_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-1")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(clienteId=cliente_a.id)
    )
    assert resposta.status_code == 201, resposta.text


def test_atendimento_cria_sem_cliente_sem_projeto_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-2")
    _atendimento(db_session, empresa, atendimento)

    resposta = _client_para(app, atendimento).post("/demandas", json=_payload())
    assert resposta.status_code == 201, resposta.text


def test_atendimento_cria_com_cliente_nao_permitido_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-3")
    _atendimento(db_session, empresa, atendimento)
    cliente_b = _cliente(db_session, empresa)  # sem responsavel_comercial_id == atendimento

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(clienteId=cliente_b.id)
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Cliente não permitido para este usuário"


def test_atendimento_cria_com_cliente_sem_responsavel_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-4")
    _atendimento(db_session, empresa, atendimento)
    cliente_orfao = _cliente(db_session, empresa, responsavel_comercial_id=None)

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(clienteId=cliente_orfao.id)
    )
    assert resposta.status_code == 422, resposta.text


def test_atendimento_cria_sem_cliente_com_projeto_interno_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-5")
    _atendimento(db_session, empresa, atendimento)
    projeto_interno = _projeto(db_session, empresa, cliente_id=None)

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(projetoId=projeto_interno.id)
    )
    assert resposta.status_code == 201, resposta.text


def test_atendimento_cria_sem_cliente_com_projeto_proprio_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-6")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(projetoId=projeto_a.id)
    )
    assert resposta.status_code == 201, resposta.text


def test_atendimento_cria_sem_cliente_com_projeto_de_outro_cliente_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-7")
    _atendimento(db_session, empresa, atendimento)
    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(projetoId=projeto_b.id)
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Cliente não permitido para este usuário"


def test_atendimento_cria_com_cliente_e_projeto_proprios_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-8")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(clienteId=cliente_a.id, projetoId=projeto_a.id)
    )
    assert resposta.status_code == 201, resposta.text


def test_atendimento_cria_com_cliente_a_e_projeto_de_b_e_rejeitado_pela_d1_2a(
    app, db_session: Session, empresa: Empresa
) -> None:
    """Cliente A é permitido para o Atendimento, mas o Projeto pertence a B — a Política C
    do D1.2A (mismatch Cliente↔Projeto) dispara ANTES do D1.2C sequer calcular contexto."""
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-9")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(clienteId=cliente_a.id, projetoId=projeto_b.id)
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Projeto não pertence ao cliente informado"


# --------------------------------------------------------------------------------------
# Numeração — rejeição por Atendimento não reserva nada (item 26).
# --------------------------------------------------------------------------------------


def test_atendimento_rejeitado_nao_reserva_numeracao_nem_gera_evento(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-num")
    _atendimento(db_session, empresa, atendimento)
    cliente_b = _cliente(db_session, empresa)

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

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(clienteId=cliente_b.id)
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

    assert total_depois == total_antes, "rejeição de Atendimento não pode ter criado Demanda"
    assert ultimo_depois == ultimo_antes, "rejeição de Atendimento não pode ter reservado numero_operacional"
    assert max_depois == max_antes
    assert eventos_depois == eventos_antes, "rejeição de Atendimento não pode ter publicado evento"


# --------------------------------------------------------------------------------------
# Patch (itens 15/27).
# --------------------------------------------------------------------------------------


def test_patch_so_nome_em_legado_proibido_retorna_200(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-legado")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    client = _client_para(app, atendimento)
    criada = _criar(client, clienteId=cliente_a.id)

    # Cliente A deixa de ser do Atendimento (dado legado) — PATCH não toca cliente/projeto.
    cliente_a.responsavel_comercial_id = None
    db_session.flush()

    resposta = client.patch(f"/demandas/{criada['id']}", json={"nome": "Só o nome mudou"})
    assert resposta.status_code == 200, resposta.text


def test_patch_reenvia_mesmo_cliente_retorna_200(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-mesmo")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    client = _client_para(app, atendimento)
    criada = _criar(client, clienteId=cliente_a.id)

    resposta = client.patch(f"/demandas/{criada['id']}", json={"clienteId": cliente_a.id})
    assert resposta.status_code == 200, resposta.text


def test_patch_troca_cliente_para_nao_permitido_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-troca")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    cliente_b = _cliente(db_session, empresa)
    client = _client_para(app, atendimento)
    criada = _criar(client, clienteId=cliente_a.id)

    resposta = client.patch(f"/demandas/{criada['id']}", json={"clienteId": cliente_b.id})
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Cliente não permitido para este usuário"


def test_patch_limpa_cliente_mantendo_projeto_proprio_retorna_200(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-limpa-1")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    client = _client_para(app, atendimento)
    criada = _criar(client, clienteId=cliente_a.id, projetoId=projeto_a.id)

    resposta = client.patch(f"/demandas/{criada['id']}", json={"clienteId": None})
    assert resposta.status_code == 200, resposta.text


def test_patch_limpa_cliente_mantendo_projeto_legado_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    """Cliente vira null, mas o Projeto INTOCADO ainda carrega um cliente fora do contexto —
    o estado final continua em contexto B, mesmo sem `cliente_id` explícito."""
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-limpa-2")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    client = _client_para(app, atendimento)
    criada = _criar(client, clienteId=cliente_a.id, projetoId=projeto_a.id)

    # Cliente A deixa de ser do Atendimento — Projeto A continua vinculado à Demanda.
    cliente_a.responsavel_comercial_id = None
    db_session.flush()

    resposta = client.patch(f"/demandas/{criada['id']}", json={"clienteId": None})
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Cliente não permitido para este usuário"


def test_patch_troca_projeto_mantendo_cliente_e_rejeitado_pela_d1_2a(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-projeto-1")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)
    client = _client_para(app, atendimento)
    criada = _criar(client, clienteId=cliente_a.id, projetoId=projeto_a.id)

    resposta = client.patch(f"/demandas/{criada['id']}", json={"projetoId": projeto_b.id})
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Projeto não pertence ao cliente informado"


def test_patch_sem_cliente_troca_projeto_para_outro_cliente_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-projeto-2")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)
    client = _client_para(app, atendimento)
    criada = _criar(client, projetoId=projeto_a.id)  # cliente_id null, projeto A (próprio)

    resposta = client.patch(f"/demandas/{criada['id']}", json={"projetoId": projeto_b.id})
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Cliente não permitido para este usuário"


def test_patch_sem_cliente_troca_projeto_para_interno_retorna_200(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-projeto-3")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    projeto_interno = _projeto(db_session, empresa, cliente_id=None)
    client = _client_para(app, atendimento)
    criada = _criar(client, projetoId=projeto_a.id)

    resposta = client.patch(
        f"/demandas/{criada['id']}", json={"projetoId": projeto_interno.id}
    )
    assert resposta.status_code == 200, resposta.text


def test_patch_sem_cliente_troca_projeto_interno_para_outro_cliente_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-projeto-4")
    _atendimento(db_session, empresa, atendimento)
    projeto_interno = _projeto(db_session, empresa, cliente_id=None)
    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)
    client = _client_para(app, atendimento)
    criada = _criar(client, projetoId=projeto_interno.id)

    resposta = client.patch(f"/demandas/{criada['id']}", json={"projetoId": projeto_b.id})
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Cliente não permitido para este usuário"


def test_patch_sem_tocar_cliente_ou_projeto_nao_aciona_d1_2c(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-omitido")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    client = _client_para(app, atendimento)
    criada = _criar(client, clienteId=cliente_a.id)

    resposta = client.patch(f"/demandas/{criada['id']}", json={"nome": "Nome novo"})
    assert resposta.status_code == 200, resposta.text


# --------------------------------------------------------------------------------------
# Estado/eventos — rejeição D1.2C não muda nada nem publica evento (item 28).
# --------------------------------------------------------------------------------------


def test_patch_mismatch_contexto_nao_altera_estado_nem_gera_evento(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="patch-estado")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    cliente_b = _cliente(db_session, empresa)
    client = _client_para(app, atendimento)
    criada = _criar(client, clienteId=cliente_a.id)

    eventos_antes = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()

    resposta = client.patch(f"/demandas/{criada['id']}", json={"clienteId": cliente_b.id})
    assert resposta.status_code == 422

    eventos_depois = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    assert eventos_depois == eventos_antes, "mismatch de contexto não pode ter publicado evento"

    linha = db_session.execute(
        text("SELECT cliente_id, projeto_id FROM demandas WHERE id = :id"), {"id": criada["id"]}
    ).one()
    assert linha.cliente_id == cliente_a.id, "cliente persistido não pode ter mudado"
    assert linha.projeto_id is None, "projeto persistido não pode ter mudado"


# --------------------------------------------------------------------------------------
# Admin/Gestor — sempre livres (item 29).
# --------------------------------------------------------------------------------------


def test_admin_usa_cliente_e_projeto_sem_responsabilidade_propria(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)
    resposta = client_admin.post(
        "/demandas", json=_payload(clienteId=cliente_b.id, projetoId=projeto_b.id)
    )
    assert resposta.status_code == 201, resposta.text


def test_gestor_usa_cliente_sem_responsabilidade_propria(
    client_gestor: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_b = _cliente(db_session, empresa)
    resposta = client_gestor.post("/demandas", json=_payload(clienteId=cliente_b.id))
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Operador com grant, não Atendimento — D1.2C não deve restringi-lo (item 30).
# --------------------------------------------------------------------------------------


def test_operador_com_grant_nao_atendimento_nao_e_restringido_por_d1_2c(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="grant-atend")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")
    cliente_b = _cliente(db_session, empresa)  # sem nenhuma relação com o operador

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(clienteId=cliente_b.id)
    )
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Head + Atendimento — ortogonalidade entre D1.2B e D1.2C (item 31).
# --------------------------------------------------------------------------------------


def test_head_e_atendimento_departamento_e_cliente_proprios_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    ator = _operador_comum(db_session, empresa, sufixo="head-atend-1")
    departamento_a = _head_por_responsavel(db_session, empresa, ator)
    _atendimento(db_session, empresa, ator)  # também vira Atendimento (próprio departamento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=ator.id)

    resposta = _client_para(app, ator).post(
        "/demandas",
        json=_payload(
            clienteId=cliente_a.id, departamentoResponsavelIds=[departamento_a.id]
        ),
    )
    assert resposta.status_code == 201, resposta.text


def test_head_e_atendimento_departamento_permitido_cliente_fora_e_rejeitado_por_d1_2c(
    app, db_session: Session, empresa: Empresa
) -> None:
    ator = _operador_comum(db_session, empresa, sufixo="head-atend-2")
    departamento_a = _head_por_responsavel(db_session, empresa, ator)
    _atendimento(db_session, empresa, ator)
    cliente_b = _cliente(db_session, empresa)  # não é do ator

    resposta = _client_para(app, ator).post(
        "/demandas",
        json=_payload(
            clienteId=cliente_b.id, departamentoResponsavelIds=[departamento_a.id]
        ),
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Cliente não permitido para este usuário"


# --------------------------------------------------------------------------------------
# Query/performance — invocações de eh_atendimento/clientes_sob_responsabilidade (item 32).
# --------------------------------------------------------------------------------------


def _contar_chamadas(nomes: list[str], acao) -> dict[str, int]:
    from app.core.escopo import clientes_sob_responsabilidade as _real_clientes
    from app.core.escopo import eh_atendimento as _real_atendimento

    reais = {"eh_atendimento": _real_atendimento, "clientes_sob_responsabilidade": _real_clientes}
    mocks = {}
    patches = [
        patch(f"app.services.demanda_service.{nome}", wraps=reais[nome]) for nome in nomes
    ]
    for p, nome in zip(patches, nomes):
        mocks[nome] = p.start()
    try:
        acao()
    finally:
        for p in patches:
            p.stop()
    return {nome: mocks[nome].call_count for nome in nomes}


def test_create_admin_nao_chama_eh_atendimento_nem_clientes(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente_b = _cliente(db_session, empresa)
    resultado = {}

    def _acao():
        resultado["resposta"] = client_admin.post(
            "/demandas", json=_payload(clienteId=cliente_b.id)
        )

    chamadas = _contar_chamadas(["eh_atendimento", "clientes_sob_responsabilidade"], _acao)
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    assert chamadas["eh_atendimento"] == 0
    assert chamadas["clientes_sob_responsabilidade"] == 0


def test_create_contexto_null_nao_chama_eh_atendimento_nem_clientes(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="query-null")
    _atendimento(db_session, empresa, atendimento)
    client = _client_para(app, atendimento)
    resultado = {}

    def _acao():
        resultado["resposta"] = client.post("/demandas", json=_payload())

    chamadas = _contar_chamadas(["eh_atendimento", "clientes_sob_responsabilidade"], _acao)
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    assert chamadas["eh_atendimento"] == 0, "contexto None nunca deveria consultar eh_atendimento"
    assert chamadas["clientes_sob_responsabilidade"] == 0


def test_patch_sem_cliente_projeto_nao_chama_eh_atendimento_nem_clientes(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="query-omitido")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    client = _client_para(app, atendimento)
    criada = _criar(client, clienteId=cliente_a.id)
    resultado = {}

    def _acao():
        resultado["resposta"] = client.patch(
            f"/demandas/{criada['id']}", json={"nome": "Outro nome"}
        )

    chamadas = _contar_chamadas(["eh_atendimento", "clientes_sob_responsabilidade"], _acao)
    assert resultado["resposta"].status_code == 200, resultado["resposta"].text
    assert chamadas["eh_atendimento"] == 0
    assert chamadas["clientes_sob_responsabilidade"] == 0


def test_create_atendimento_com_contexto_faz_no_maximo_uma_chamada_de_cada(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="query-atend")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    client = _client_para(app, atendimento)
    resultado = {}

    def _acao():
        resultado["resposta"] = client.post(
            "/demandas", json=_payload(clienteId=cliente_a.id)
        )

    chamadas = _contar_chamadas(["eh_atendimento", "clientes_sob_responsabilidade"], _acao)
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    assert chamadas["eh_atendimento"] <= 1
    assert chamadas["clientes_sob_responsabilidade"] <= 1
