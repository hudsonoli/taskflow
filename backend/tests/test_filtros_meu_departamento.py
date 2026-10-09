"""Fase 6.1 — filtros avançados de "Meu Departamento" (`GET /demandas?escopo=meu-departamento`).

Garantias provadas aqui:
- o departamento NUNCA vem do cliente como autoridade: o escopo é derivado no servidor (`departamentos_como_head`) e os
  filtros só REFINAM — `departamentoId` de um departamento que o usuário não lidera devolve vazio, não amplia;
- entre campos: AND; dentro do campo: OR ("é um de"); `*Excluir` = "não é um de", mantendo NULL (cliente/projeto vazio,
  demanda sem responsável) — a mesma semântica de Arquivos/Tráfego (Fase 6);
- tudo no SQL, antes de limit/offset; valor inválido é 422; teto de 50 valores; empresa sempre da sessão.
"""

from __future__ import annotations

import uuid
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.empresa import Empresa
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _client_para, _head_por_lider, _head_por_responsavel, _operador_comum
from tests.test_demanda import _criar, _departamento
from tests.test_gerenciador_arquivos import _cliente, _projeto
from tests.test_trafego_carga import _equipe, _usuario

ESCOPO = {"escopo": "meu-departamento"}


# Fase 7C.2: sem `status` a lista do Meu Departamento é só a operação EM ABERTO (provado em test_fase_7c2_meu_departamento_abertas.py).
# Estes testes são sobre o ESCOPO e os FILTROS, não sobre o status padrão: pedem todos os status explicitamente, para continuar
# enxergando o departamento inteiro (inclusive a concluída do cenário) e provar que nenhum filtro amplia o escopo.
TODOS_OS_STATUS = "rascunho,planejada,em_execucao,pausada,bloqueada,aguardando_cliente,concluida,cancelada"


def _lista(client: TestClient, **params) -> list[dict]:
    params.setdefault("status", TODOS_OS_STATUS)
    consulta = {**ESCOPO, **{chave: valor for chave, valor in params.items() if valor is not None}}
    resposta = client.get("/demandas?" + urlencode(consulta))
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _ids(itens: list[dict]) -> set[str]:
    return {item["id"] for item in itens}


def _cenario(app, db: Session, empresa: Empresa, client_admin: TestClient) -> dict:
    """Head formal de CRIAÇÃO (e só dela). Criação e TI têm demandas; algumas dimensões só existem em TI."""
    head = _operador_comum(db, empresa, sufixo=f"f61-{uuid.uuid4().hex[:6]}")
    criacao = _head_por_responsavel(db, empresa, head)
    ti = _departamento(db, empresa, nome=f"TI {uuid.uuid4().hex[:4]}")
    cli_a, cli_b, cli_ti = _cliente(db, empresa), _cliente(db, empresa), _cliente(db, empresa)
    proj_a = _projeto(db, empresa, cliente_id=cli_a.id)
    ana, bia = _usuario(db, empresa, "Ana"), _usuario(db, empresa, "Bia")
    equipe = _equipe(db, empresa, f"Equipe {uuid.uuid4().hex[:4]}", [ana])

    def demanda(depto, **extra):
        return _criar(client_admin, departamentoResponsavelIds=[depto.id], **extra)

    d1 = demanda(criacao, clienteId=cli_a.id, projetoId=proj_a.id, prioridade="alta", usuarioResponsavelIds=[ana.id])
    d2 = demanda(criacao, clienteId=cli_b.id, prioridade="baixa", usuarioResponsavelIds=[bia.id])
    d3 = demanda(criacao, prioridade="media")  # sem cliente, sem projeto, sem responsável
    t1 = demanda(ti, clienteId=cli_ti.id, prioridade="alta", usuarioResponsavelIds=[ana.id])
    for item, status in ((d1, "em_execucao"), (d2, "pausada"), (d3, "concluida"), (t1, "em_execucao")):
        db.get(Demanda, item["id"]).status = status
    db.flush()
    return {
        "head": head, "client": _client_para(app, head), "criacao": criacao, "ti": ti,
        "cli_a": cli_a, "cli_b": cli_b, "cli_ti": cli_ti, "proj_a": proj_a, "ana": ana, "bia": bia, "equipe": equipe,
        "d1": d1, "d2": d2, "d3": d3, "t1": t1,
    }


# ------------------------------------------------------------------ escopo fixo
def test_escopo_e_so_do_departamento_do_head_mesmo_sem_departamento_id(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    assert _ids(_lista(c["client"])) == {c["d1"]["id"], c["d2"]["id"], c["d3"]["id"]}  # nada de TI


def test_departamento_id_do_cliente_nao_e_autoridade_e_nao_amplia(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    assert _lista(c["client"], departamentoId=c["ti"].id) == []  # departamento que ele não lidera: vazio
    assert _ids(_lista(c["client"], departamentoId=c["criacao"].id)) == {c["d1"]["id"], c["d2"]["id"], c["d3"]["id"]}
    # filtros que só existem em TI (cliente de TI) nunca fazem aparecer o registro de TI
    assert _lista(c["client"], clienteId=c["cli_ti"].id) == []
    assert _lista(c["client"], clienteIdExcluir=c["cli_a"].id, prioridade="alta") == []  # t1 é "alta" mas é de TI


def test_filtro_nao_e_nunca_inclui_demanda_de_outro_departamento(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    achados = _ids(_lista(c["client"], clienteIdExcluir=c["cli_a"].id))
    assert c["t1"]["id"] not in achados  # "não é cliente A" NÃO abre o departamento TI
    assert achados == {c["d2"]["id"], c["d3"]["id"]}


def test_nao_head_nao_acessa_o_escopo_do_departamento(app, db_session, empresa, client_operador) -> None:
    assert client_operador.get("/demandas?escopo=meu-departamento&prioridade=alta").status_code == 403


def test_gestor_lider_so_ve_o_departamento_atual_e_o_contexto_acompanha_a_troca(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    gestor = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="gestor", email_prefixo="f61-gestor")
    _head_por_lider(db_session, empresa, gestor)  # departamento atual = um departamento novo, sem demandas
    cliente_gestor = _client_para(app, gestor)
    # Gestor tem visão total no escopo-base, mas "Meu Departamento" continua sendo SÓ o departamento atual dele
    assert _lista(cliente_gestor, prioridade="alta") == []
    # troca de contexto (Fase 5): passa a liderar Criação — mesma autoridade, outro departamento atual
    gestor.departamento_id = c["criacao"].id
    gestor.lider_departamento = True
    db_session.flush()
    assert _ids(_lista(cliente_gestor, prioridade="alta")) == {c["d1"]["id"]}  # só Criação, nada de TI
    gestor.departamento_id = c["ti"].id
    db_session.flush()
    assert _ids(_lista(cliente_gestor, prioridade="alta")) == {c["t1"]["id"]}  # agora TI; mesmo filtro, sem dado velho de Criação


# ------------------------------------------------------------------ filtros
def test_cliente_e_um_de_e_nao_e_um_de(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    assert _ids(_lista(c["client"], clienteId=str(c["cli_a"].id))) == {c["d1"]["id"]}
    assert _ids(_lista(c["client"], clienteId=f"{c['cli_a'].id},{c['cli_b'].id}")) == {c["d1"]["id"], c["d2"]["id"]}  # OR
    # NULL ≠ qualquer valor: a demanda sem cliente continua em "não é A, B"
    assert _ids(_lista(c["client"], clienteIdExcluir=f"{c['cli_a'].id},{c['cli_b'].id}")) == {c["d3"]["id"]}


def test_projeto_prioridade_e_status(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    assert _ids(_lista(c["client"], projetoId=str(c["proj_a"].id))) == {c["d1"]["id"]}
    assert _ids(_lista(c["client"], projetoIdExcluir=str(c["proj_a"].id))) == {c["d2"]["id"], c["d3"]["id"]}
    assert _ids(_lista(c["client"], prioridade="alta,media")) == {c["d1"]["id"], c["d3"]["id"]}
    assert _ids(_lista(c["client"], prioridadeExcluir="alta")) == {c["d2"]["id"], c["d3"]["id"]}
    assert _ids(_lista(c["client"], status="em_execucao,pausada")) == {c["d1"]["id"], c["d2"]["id"]}
    assert _ids(_lista(c["client"], statusExcluir="concluida,cancelada")) == {c["d1"]["id"], c["d2"]["id"]}


def test_responsavel_e_equipe(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    assert _ids(_lista(c["client"], responsavelId=c["ana"].id)) == {c["d1"]["id"]}
    assert _ids(_lista(c["client"], responsavelId=f"{c['ana'].id},{c['bia'].id}")) == {c["d1"]["id"], c["d2"]["id"]}
    # "não é Ana": mantém a demanda SEM responsável
    assert _ids(_lista(c["client"], responsavelIdExcluir=c["ana"].id)) == {c["d2"]["id"], c["d3"]["id"]}
    assert _ids(_lista(c["client"], equipeId=c["equipe"].id)) == {c["d1"]["id"]}
    assert _ids(_lista(c["client"], equipeIdExcluir=c["equipe"].id)) == {c["d2"]["id"], c["d3"]["id"]}


def test_filtros_combinam_com_and_e_com_o_periodo_existente(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    assert _ids(_lista(c["client"], clienteId=f"{c['cli_a'].id},{c['cli_b'].id}", prioridade="alta")) == {c["d1"]["id"]}
    assert _lista(c["client"], clienteId=str(c["cli_a"].id), prioridade="baixa") == []
    assert _lista(c["client"], origem="interna", clienteId=str(c["cli_a"].id)) == []  # origem existente continua valendo


def test_filtro_vale_antes_da_paginacao(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    for _ in range(4):  # mais recentes (número operacional maior) que o alvo: sem filtro ele sairia da 1ª página
        _criar(client_admin, departamentoResponsavelIds=[c["criacao"].id], prioridade="media")
    sem_filtro = _lista(c["client"], limit=3, offset=0)
    assert c["d1"]["id"] not in _ids(sem_filtro)
    com_filtro = _lista(c["client"], clienteId=str(c["cli_a"].id), limit=3, offset=0)
    assert _ids(com_filtro) == {c["d1"]["id"]}
    assert _lista(c["client"], clienteId=str(c["cli_a"].id), limit=3, offset=3) == []  # página seguinte mantém o filtro
    pagina2 = _lista(c["client"], prioridade="media", limit=2, offset=2)
    assert len(pagina2) == 2 and all(item["prioridade"] == "media" for item in pagina2)


def test_sem_resultado_e_lista_vazia(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    assert _lista(c["client"], clienteId=str(uuid.uuid4())) == []


@pytest.mark.parametrize(
    "params",
    [
        {"clienteId": "nao-uuid"},
        {"clienteIdExcluir": "x"},
        {"projetoIdExcluir": "1,2"},
        {"responsavelId": "abc"},
        {"responsavelIdExcluir": "abc"},
        {"equipeId": "abc"},
        {"equipeIdExcluir": "abc"},
        {"prioridade": "urgente"},
        {"prioridadeExcluir": "alta,urgente"},
        {"statusExcluir": "inexistente"},
        {"clienteId": ",".join(str(uuid.uuid4()) for _ in range(51))},
    ],
)
def test_valor_invalido_e_422(app, db_session, empresa, client_admin, params: dict) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    resposta = c["client"].get("/demandas?" + urlencode({**ESCOPO, **params}))
    assert resposta.status_code == 422, resposta.text


def test_filtros_nao_atravessam_tenant(app, db_session, empresa, outra_empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    cliente_alheio = _cliente(db_session, outra_empresa)
    usuario_alheio = _usuario(db_session, outra_empresa)
    assert _lista(c["client"], clienteId=str(cliente_alheio.id)) == []
    assert _lista(c["client"], responsavelId=usuario_alheio.id) == []
    # "não é" de um id alheio não revela nada além do escopo do próprio departamento
    assert _ids(_lista(c["client"], clienteIdExcluir=str(cliente_alheio.id))) == {c["d1"]["id"], c["d2"]["id"], c["d3"]["id"]}


def test_listagem_geral_continua_aceitando_um_so_valor_como_antes(app, db_session, empresa, client_admin) -> None:
    """Compatibilidade: Tarefas/Pauta enviam UM id/valor — o comportamento é o mesmo de antes dos filtros avançados."""
    c = _cenario(app, db_session, empresa, client_admin)
    resposta = client_admin.get("/demandas", params={"clienteId": str(c["cli_a"].id), "prioridade": "alta", "limit": 50})
    assert resposta.status_code == 200
    assert _ids(resposta.json()) == {c["d1"]["id"]}
