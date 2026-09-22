"""D1.2E — Diretórios de Cliente/Projeto alinhados ao contexto de Atendimento (Fase 2G.10B).

Fecha o gap nomeado explicitamente no código (`test_d1_2a_cliente_projeto.py`,
`test_d1_2c_atendimento_cliente.py`: "frontend/diretórios (D1.2E)"): `GET /clientes/diretorio`
e `GET /projetos/diretorio` passam a refletir o MESMO contexto comercial que D1.2C já aplica
em CREATE/PATCH de Demanda — reaproveitando `eh_atendimento`/`clientes_sob_responsabilidade`
(`app/core/escopo.py`), sem reimplementar nem parametrizar por escopo vindo do cliente.

Decisão formal, não gap esquecido: Operador comum **não** recebe nenhuma restrição nova de
cliente/projeto (nem no diretório, nem em CREATE/PATCH) — D1.2A-D permanecem intactos. Não
existe relação Cliente↔Departamento nem Projeto↔Departamento no schema atual, então qualquer
regra além da de Atendimento exigiria schema novo, fora da política aprovada para esta fase.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
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
from tests.test_demanda import _cliente, _payload


# --------------------------------------------------------------------------------------
# Clientes — diretório (itens 1-8 do kickoff).
# --------------------------------------------------------------------------------------


def test_admin_ve_todos_os_clientes_do_tenant(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    com_responsavel = _cliente(db_session, empresa, responsavel_comercial_id=None)
    sem_responsavel = _cliente(db_session, empresa)
    ids = {c["id"] for c in client_admin.get("/clientes/diretorio").json()}
    assert {com_responsavel.id, sem_responsavel.id} <= ids


def test_gestor_ve_todos_os_clientes(
    client_gestor: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    ids = {c["id"] for c in client_gestor.get("/clientes/diretorio").json()}
    assert cliente.id in ids


def test_operador_comum_ve_todos_os_clientes(
    client_operador: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Decisão D1.2E: operador comum não recebe restrição adicional de cliente/projeto —
    diretório continua igual a antes desta fase."""
    cliente = _cliente(db_session, empresa)
    ids = {c["id"] for c in client_operador.get("/clientes/diretorio").json()}
    assert cliente.id in ids


def test_head_puro_ve_todos_os_clientes(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-diretorio-cli")
    _head_por_responsavel(db_session, empresa, head)
    cliente = _cliente(db_session, empresa)  # fora de qualquer relação com o head

    ids = {c["id"] for c in _client_para(app, head).get("/clientes/diretorio").json()}
    assert cliente.id in ids


def test_atendimento_ve_somente_sua_carteira(app, db_session: Session, empresa: Empresa) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-diretorio-cli")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    cliente_b = _cliente(db_session, empresa)  # de outro responsável

    diretorio = _client_para(app, atendimento).get("/clientes/diretorio").json()
    ids = {c["id"] for c in diretorio}
    assert cliente_a.id in ids
    assert cliente_b.id not in ids


def test_head_e_atendimento_ve_somente_sua_carteira(app, db_session: Session, empresa: Empresa) -> None:
    """Head não anula D1.2C — as duas relações são ortogonais também no diretório."""
    ator = _operador_comum(db_session, empresa, sufixo="head-atend-diretorio-cli")
    _head_por_responsavel(db_session, empresa, ator)
    _atendimento(db_session, empresa, ator)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=ator.id)
    cliente_b = _cliente(db_session, empresa)

    diretorio = _client_para(app, ator).get("/clientes/diretorio").json()
    ids = {c["id"] for c in diretorio}
    assert cliente_a.id in ids
    assert cliente_b.id not in ids


def test_atendimento_sem_carteira_retorna_lista_vazia(app, db_session: Session, empresa: Empresa) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-sem-carteira-cli")
    _atendimento(db_session, empresa, atendimento)
    _cliente(db_session, empresa)  # existe no tenant, mas não é da carteira deste Atendimento

    diretorio = _client_para(app, atendimento).get("/clientes/diretorio").json()
    assert diretorio == []


def test_diretorio_clientes_nunca_vaza_outro_tenant(
    app, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-tenant-cli")
    _atendimento(db_session, empresa, atendimento)
    # Cliente de OUTRO tenant, mesmo se (hipoteticamente) tivesse o mesmo responsável comercial
    # id, nunca poderia aparecer — clientes_sob_responsabilidade já filtra por empresa_id.
    _cliente(db_session, outra_empresa, responsavel_comercial_id=atendimento.id)

    diretorio = _client_para(app, atendimento).get("/clientes/diretorio").json()
    assert diretorio == []


# --------------------------------------------------------------------------------------
# Projetos — diretório (itens 9-16 do kickoff).
# --------------------------------------------------------------------------------------


def test_admin_ve_projetos_normais_e_internos(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto_normal = _projeto(db_session, empresa, cliente_id=cliente.id)
    projeto_interno = _projeto(db_session, empresa, cliente_id=None)

    ids = {p["id"] for p in client_admin.get("/projetos/diretorio").json()}
    assert {projeto_normal.id, projeto_interno.id} <= ids


def test_operador_comum_mantem_comportamento_atual_em_projetos(
    client_operador: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)

    ids = {p["id"] for p in client_operador.get("/projetos/diretorio").json()}
    assert projeto.id in ids


def test_atendimento_ve_projeto_da_propria_carteira(app, db_session: Session, empresa: Empresa) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-diretorio-proj-1")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)

    ids = {p["id"] for p in _client_para(app, atendimento).get("/projetos/diretorio").json()}
    assert projeto_a.id in ids


def test_atendimento_nao_ve_projeto_de_cliente_alheio(app, db_session: Session, empresa: Empresa) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-diretorio-proj-2")
    _atendimento(db_session, empresa, atendimento)
    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)

    ids = {p["id"] for p in _client_para(app, atendimento).get("/projetos/diretorio").json()}
    assert projeto_b.id not in ids


def test_atendimento_ve_projeto_interno(app, db_session: Session, empresa: Empresa) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-diretorio-proj-3")
    _atendimento(db_session, empresa, atendimento)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=atendimento.id)
    _projeto(db_session, empresa, cliente_id=cliente_a.id)
    projeto_interno = _projeto(db_session, empresa, cliente_id=None)

    ids = {p["id"] for p in _client_para(app, atendimento).get("/projetos/diretorio").json()}
    assert projeto_interno.id in ids


def test_atendimento_sem_carteira_ainda_ve_projeto_interno(app, db_session: Session, empresa: Empresa) -> None:
    """D1.2C trata contexto sem cliente como sempre permitido — projeto interno nunca some,
    mesmo com carteira vazia."""
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-sem-carteira-proj")
    _atendimento(db_session, empresa, atendimento)
    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)
    projeto_interno = _projeto(db_session, empresa, cliente_id=None)

    diretorio = _client_para(app, atendimento).get("/projetos/diretorio").json()
    ids = {p["id"] for p in diretorio}
    assert projeto_interno.id in ids
    assert projeto_b.id not in ids


def test_head_e_atendimento_segue_regra_atendimento_em_projetos(app, db_session: Session, empresa: Empresa) -> None:
    ator = _operador_comum(db_session, empresa, sufixo="head-atend-diretorio-proj")
    _head_por_responsavel(db_session, empresa, ator)
    _atendimento(db_session, empresa, ator)
    cliente_a = _cliente(db_session, empresa, responsavel_comercial_id=ator.id)
    projeto_a = _projeto(db_session, empresa, cliente_id=cliente_a.id)
    cliente_b = _cliente(db_session, empresa)
    projeto_b = _projeto(db_session, empresa, cliente_id=cliente_b.id)

    diretorio = _client_para(app, ator).get("/projetos/diretorio").json()
    ids = {p["id"] for p in diretorio}
    assert projeto_a.id in ids
    assert projeto_b.id not in ids


def test_diretorio_projetos_nunca_vaza_outro_tenant(
    app, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-tenant-proj")
    _atendimento(db_session, empresa, atendimento)
    _projeto(db_session, outra_empresa, cliente_id=None)  # interno, mas de OUTRO tenant

    diretorio = _client_para(app, atendimento).get("/projetos/diretorio").json()
    assert diretorio == []


# --------------------------------------------------------------------------------------
# Regressão — Operador comum em CREATE de Demanda (item 21): decisão D1.2E, não gap.
# --------------------------------------------------------------------------------------


def test_operador_comum_create_demanda_sem_restricao_adicional_de_cliente_projeto(
    app, db_session: Session, empresa: Empresa
) -> None:
    """Decisão D1.2E: operador comum não recebe restrição adicional de cliente/projeto — o
    gap deliberadamente registrado em D1.2D (commit `9381221`) permanece política final.
    Diretório e CREATE/PATCH continuam livres para este ator, sujeitos só a D1.2A (tenant,
    arquivado, compatibilidade cliente↔projeto)."""
    operador = _operador_comum(db_session, empresa, sufixo="d1-2e-regressao")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")
    cliente = _cliente(db_session, empresa)  # sem nenhuma relação com o operador
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(clienteId=cliente.id, projetoId=projeto.id)
    )
    assert resposta.status_code == 201, resposta.text
