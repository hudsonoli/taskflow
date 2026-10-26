"""Kanban → Em execução: a intenção é escolhida ANTES da mutation por dois sinais que o SERVIDOR calcula (P1_KANBAN_ADMIN_RUNNING_PATH).

- `ehExecutorEfetivo`  = SÓ responsabilidade (regra central `eh_executor_da_demanda`): quem é → `POST /iniciar-trabalho` (sessão/foco único), qualquer que seja o perfil.
- `podeAlterarStatus`  = SÓ autoridade (`demandas.editar` efetiva, a MESMA permissão do `PATCH /demandas/{id}`; falso em leitura global/acompanhamento).
  Quem não executa mas tem autoridade → PATCH administrativo `status=em_execucao`, sem sessão pessoal e sem tocar no foco que já tenha em outra tarefa.

`POST /iniciar-trabalho` de quem NÃO é executor continua 403 (sem fallback para PATCH, que é decisão do cliente ANTES da chamada). Fora do expediente o executor continua bloqueado
pelo caminho de iniciar trabalho (409) e nunca é convertido em PATCH.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from tests.test_d1_criacao_demandas import _client_para, _override
from tests.test_demanda import dentro_do_expediente, fora_do_expediente  # noqa: F401  (fixtures)
from tests.test_iniciar_trabalho import _ativas, _iniciar, _rascunho, _responsaveis, _status
from tests.test_sessao_trabalho_integridade import _abrir_ok, _demanda, _patch, operadores  # noqa: F401  (fixture `operadores`)


def _da_lista(client: TestClient, demanda_id: str) -> dict:
    resposta = client.get("/demandas?limit=100").json()
    itens = resposta["items"] if isinstance(resposta, dict) else resposta
    return next(item for item in itens if item["id"] == demanda_id)


# ------------------------------------------------------------------ os dois sinais


def test_sinais_responsabilidade_e_autoridade_sao_independentes_na_lista_e_no_detalhe(app, client_admin: TestClient, usuario_admin: Usuario, operadores: list[Usuario]) -> None:
    dono = operadores[0]
    de_outro = _rascunho(client_admin, dono)  # admin NÃO é responsável
    do_admin = _rascunho(client_admin, usuario_admin)  # admin é responsável

    nao_executor = _da_lista(client_admin, de_outro["id"])
    assert nao_executor["ehExecutorEfetivo"] is False and nao_executor["podeAlterarStatus"] is True  # autoridade sem responsabilidade
    executor = _da_lista(client_admin, do_admin["id"])
    assert executor["ehExecutorEfetivo"] is True and executor["podeAlterarStatus"] is True  # admin que executa: as duas coisas, a responsabilidade decide o comando

    detalhe = client_admin.get(f"/demandas/{de_outro['id']}").json()
    assert (detalhe["ehExecutorEfetivo"], detalhe["podeAlterarStatus"]) == (False, True)

    operador = _client_para(app, dono)
    da_lista = _da_lista(operador, de_outro["id"])
    assert (da_lista["ehExecutorEfetivo"], da_lista["podeAlterarStatus"]) == (True, True)  # operador responsável: executor (e o RBAC padrão tem demandas.editar)


def test_sinal_de_executor_nao_mistura_status_nem_expediente(client_admin: TestClient, usuario_admin: Usuario) -> None:
    concluida = _rascunho(client_admin, usuario_admin)
    _patch(client_admin, concluida["id"], status="cancelada")
    item = _da_lista(client_admin, concluida["id"])
    assert item["ehExecutorEfetivo"] is True  # responsabilidade pura: continua true
    assert item["podeIniciarTrabalho"] is False  # o sinal antigo mistura o status; o novo não


def test_autoridade_segue_o_rbac_do_patch_inclusive_excecao_negar(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    dono = operadores[0]
    demanda = _rascunho(client_admin, dono)
    _override(db_session, usuario=dono, permissao="demandas.editar", efeito="negar")
    operador = _client_para(app, dono)
    item = _da_lista(operador, demanda["id"])
    assert item["ehExecutorEfetivo"] is True and item["podeAlterarStatus"] is False
    assert operador.patch(f"/demandas/{demanda['id']}", json={"status": "em_execucao"}).status_code == 403  # o servidor concorda com o sinal


def test_leitura_global_e_acompanhamento_nao_dao_nenhum_dos_dois_sinais(client_admin: TestClient, operadores: list[Usuario]) -> None:
    demanda = _rascunho(client_admin, operadores[0])
    pauta = client_admin.get(f"/demandas/{demanda['id']}?escopo=pauta").json()
    assert pauta["ehExecutorEfetivo"] is False and pauta["podeAlterarStatus"] is False
    lista_pauta = client_admin.get("/demandas?limit=100&escopo=pauta").json()
    itens = lista_pauta["items"] if isinstance(lista_pauta, dict) else lista_pauta
    assert all(i["ehExecutorEfetivo"] is False and i["podeAlterarStatus"] is False for i in itens)


# ------------------------------------------------------------------ B) admin não executor → PATCH administrativo, sem sessão, foco pessoal intacto


def test_admin_nao_executor_move_b_por_patch_sem_criar_sessao_e_sem_tocar_no_proprio_foco(
    app, db_session: Session, client_admin: TestClient, usuario_admin: Usuario, operadores: list[Usuario], dentro_do_expediente  # noqa: F811
) -> None:
    dono = operadores[0]
    a = _rascunho(client_admin, usuario_admin)  # admin executa A e a tem em foco
    _patch(client_admin, a["id"], status="em_execucao")
    _abrir_ok(client_admin, a["id"], usuario_admin.id)
    b = _rascunho(client_admin, dono)  # admin NÃO executa B
    assert [s.demanda_id for s in _ativas(db_session, usuario_admin.id)] == [a["id"]]

    resposta = client_admin.patch(f"/demandas/{b['id']}", json={"status": "em_execucao"})  # o que o Kanban faz quando ehExecutorEfetivo=false e podeAlterarStatus=true
    assert resposta.status_code == 200, resposta.text

    assert _status(db_session, b["id"]) == "em_execucao"
    assert _ativas(db_session, dono.id) == []  # o dono não ganha sessão por isso
    assert [s.demanda_id for s in _ativas(db_session, usuario_admin.id)] == [a["id"]]  # sessão admin/A INTACTA, nenhuma sessão admin/B
    assert _status(db_session, a["id"]) == "em_execucao"  # A permanece exatamente como estava


def test_gestor_nao_executor_tambem_move_por_patch(
    app, db_session: Session, client_admin: TestClient, client_gestor: TestClient, usuario_gestor: Usuario, operadores: list[Usuario], dentro_do_expediente  # noqa: F811
) -> None:
    b = _rascunho(client_admin, operadores[0])
    item = _da_lista(client_gestor, b["id"])
    assert (item["ehExecutorEfetivo"], item["podeAlterarStatus"]) == (False, True)
    assert client_gestor.patch(f"/demandas/{b['id']}", json={"status": "em_execucao"}).status_code == 200
    assert _status(db_session, b["id"]) == "em_execucao"
    assert _ativas(db_session, usuario_gestor.id) == []


# ------------------------------------------------------------------ A) executor (inclusive admin) → iniciar-trabalho; foco único


def test_admin_executor_efetivo_usa_iniciar_trabalho_e_a_troca_de_foco_pausa_a_anterior(
    app, db_session: Session, client_admin: TestClient, usuario_admin: Usuario, dentro_do_expediente  # noqa: F811
) -> None:
    a = _rascunho(client_admin, usuario_admin)
    b = _rascunho(client_admin, usuario_admin)
    assert _iniciar(client_admin, a["id"]).status_code == 200
    assert (_da_lista(client_admin, b["id"])["ehExecutorEfetivo"], _da_lista(client_admin, b["id"])["podeAlterarStatus"]) == (True, True)

    assert _iniciar(client_admin, b["id"]).status_code == 200  # o Kanban escolhe iniciar-trabalho, não PATCH

    assert _status(db_session, a["id"]) == "pausada" and _status(db_session, b["id"]) == "em_execucao"
    assert [s.demanda_id for s in _ativas(db_session, usuario_admin.id)] == [b["id"]]  # uma sessão ativa, a de B


def test_operador_executor_continua_pelo_iniciar_trabalho_com_foco_unico(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario], dentro_do_expediente  # noqa: F811
) -> None:
    hudson = operadores[0]
    a, b = _rascunho(client_admin, hudson), _rascunho(client_admin, hudson)
    operador = _client_para(app, hudson)
    assert _iniciar(operador, a["id"]).status_code == 200 and _iniciar(operador, b["id"]).status_code == 200
    assert _status(db_session, a["id"]) == "pausada" and _status(db_session, b["id"]) == "em_execucao"
    assert [s.demanda_id for s in _ativas(db_session, hudson.id)] == [b["id"]]


# ------------------------------------------------------------------ preservado: POST de não executor = 403, sem efeitos; sem fallback no servidor


def test_post_iniciar_trabalho_de_nao_executor_segue_403_e_nada_muda(
    app, db_session: Session, client_admin: TestClient, usuario_admin: Usuario, operadores: list[Usuario], dentro_do_expediente  # noqa: F811
) -> None:
    b = _rascunho(client_admin, operadores[0])
    resposta = _iniciar(client_admin, b["id"])
    assert resposta.status_code == 403
    assert _status(db_session, b["id"]) == "rascunho" and _ativas(db_session, usuario_admin.id) == []  # o servidor NUNCA converte o POST em mudança de status


# ------------------------------------------------------------------ expediente: executor bloqueado, nunca convertido em PATCH


def test_executor_fora_do_expediente_e_bloqueado_pelo_iniciar_trabalho_e_nada_muda(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario], fora_do_expediente  # noqa: F811
) -> None:
    hudson = operadores[0]
    b = _rascunho(client_admin, hudson)
    operador = _client_para(app, hudson)
    resposta = _iniciar(operador, b["id"])
    assert resposta.status_code == 409, resposta.text  # expediente: o mesmo bloqueio de sempre
    assert _status(db_session, b["id"]) == "rascunho" and _ativas(db_session, hudson.id) == []


def test_sem_autoridade_e_sem_responsabilidade_nao_alcanca_a_tarefa(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    dono, estranho = operadores[0], operadores[1]
    b = _rascunho(client_admin, dono)
    de_fora = _client_para(app, estranho)
    assert de_fora.patch(f"/demandas/{b['id']}", json={"status": "em_execucao"}).status_code == 404  # fora do escopo
    assert _iniciar(de_fora, b["id"]).status_code in (403, 404)
    assert _status(db_session, b["id"]) == "rascunho"
