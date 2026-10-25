"""Troca de foco pausa a Demanda ANTERIOR: quem tem sessão ativa em A e inicia trabalho em B pausa A quando era o último executor ativo nela.

Autoridade: o serviço de domínio (`DemandaService.iniciar_trabalho`) — o Kanban e o botão "Iniciar trabalho" chamam o MESMO `POST /demandas/{id}/iniciar-trabalho`.
A Demanda anterior é a da SESSÃO ATIVA do usuário (nunca "a que estiver em execução"); a pausa usa a transição central de status (evento + intervalo operacional) e
vive na mesma transação do fechamento da sessão e da abertura da nova. Falha ao iniciar B não toca em A.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.services.demanda_service import DemandaService
from app.services.sessao_trabalho_service import MOTIVO_TROCA_RESPONSAVEL, SessaoTrabalhoService
from tests.test_d1_criacao_demandas import _client_para
from tests.test_demanda import _regra_todos_os_dias, dentro_do_expediente  # noqa: F401  (fixture)
from tests.test_demanda_workflow import _departamento
from tests.test_iniciar_trabalho import _ativas, _iniciar, _rascunho, _responsaveis, _status
from tests.test_sessao_trabalho_integridade import _abrir_ok, _demanda, _patch, _sessao, _sessoes, operadores  # noqa: F401  (fixture `operadores`)


@pytest.fixture(autouse=True)
def _expediente_aberto(dentro_do_expediente) -> None:  # noqa: F811
    """Entrar em execução respeita o expediente — a janela é fixada para o teste não depender da hora."""


def _eventos(db: Session, demanda_id: str, tipo: str) -> list[Evento]:
    db.expire_all()
    return list(db.scalars(select(Evento).where(Evento.entidade_id == demanda_id, Evento.tipo == tipo).order_by(Evento.occurred_at.asc())).all())


def _pausas_da_troca(db: Session, demanda_id: str) -> list[Evento]:
    return [e for e in _eventos(db, demanda_id, "demanda.status_alterado") if e.payload.get("para") == "pausada"]


def _linha_do_tempo(db: Session, demanda_id: str) -> list[tuple]:
    db.expire_all()
    return [
        tuple(linha)
        for linha in db.execute(
            text("SELECT status, inicio_em, fim_em FROM demanda_status_intervalos WHERE demanda_id = :d ORDER BY inicio_em ASC, created_at ASC"), {"d": demanda_id}
        ).all()
    ]


def _linha_do_tempo_coerente(db: Session, demanda_id: str) -> list[tuple]:
    """Sem sobreposição nem buraco: cada intervalo começa onde o anterior terminou, e só o ÚLTIMO fica aberto."""
    linha = _linha_do_tempo(db, demanda_id)
    for anterior, seguinte in zip(linha, linha[1:]):
        assert anterior[2] is not None and anterior[2] == seguinte[1], linha
    assert sum(1 for item in linha if item[2] is None) == 1 and linha[-1][2] is None, linha
    return linha


def _em_execucao_com_sessao(client_admin: TestClient, *usuarios: Usuario) -> tuple[dict, list[dict]]:
    a = _demanda(client_admin)
    _responsaveis(client_admin, a["id"], *usuarios)
    return a, [_abrir_ok(client_admin, a["id"], u.id) for u in usuarios]


# --------------------------------------------------------------------------------------
# 1 — único executor: A pausa
# --------------------------------------------------------------------------------------


def test_unico_executor_troca_de_foco_pausa_a_anterior_pela_transicao_central(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    op = operadores[0]
    a, (sessao_a,) = _em_execucao_com_sessao(client_admin, op)
    b = _rascunho(client_admin, op)

    resposta = _iniciar(_client_para(app, op), b["id"])
    assert resposta.status_code == 200, resposta.text

    assert _status(db_session, a["id"]) == "pausada" and _status(db_session, b["id"]) == "em_execucao"
    fechada = _sessao(db_session, sessao_a["id"])
    assert fechada.status == "encerrada" and fechada.motivo_encerramento == "substituicao_sessao_ativa"
    (ativa,) = _ativas(db_session, op.id)  # exatamente UMA sessão ativa, e é a de B
    assert ativa.demanda_id == b["id"]
    assert resposta.json()["trabalhandoAgora"] is True

    # origem da pausa: a transição central grava `manual` (a automática por expediente é outra coisa) e o evento carrega o motivo
    a_db = db_session.get(Demanda, a["id"])
    assert a_db.pausa_origem == "manual" and a_db.pausada_em is not None
    (pausa,) = _pausas_da_troca(db_session, a["id"])
    assert pausa.payload["de"] == "em_execucao" and pausa.payload["motivo"] == "troca_foco" and pausa.usuario_id == op.id

    # cada fato UMA vez: fechamento da sessão de A, abertura da de B
    assert len(_eventos(db_session, a["id"], "sessao_trabalho_encerrada")) == 1
    assert len(_eventos(db_session, b["id"], "sessao_trabalho_iniciada")) == 1
    assert len(_eventos(db_session, b["id"], "sessao_trabalho_encerrada")) == 0

    # intervalos: A fechou a execução e abriu a pausa no mesmo instante; B tem um único intervalo aberto em execução
    linha_a = _linha_do_tempo_coerente(db_session, a["id"])
    assert [item[0] for item in linha_a][-2:] == ["em_execucao", "pausada"]
    linha_b = _linha_do_tempo_coerente(db_session, b["id"])
    assert linha_b[-1][0] == "em_execucao"


def test_troca_para_demanda_ja_em_execucao_pausa_a_anterior_sem_transicao_redundante_em_b(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    op = operadores[0]
    a, _ = _em_execucao_com_sessao(client_admin, op)
    b = _demanda(client_admin)  # já em execução, sem sessão do op
    _responsaveis(client_admin, b["id"], op)
    eventos_status_b = len(_eventos(db_session, b["id"], "demanda.status_alterado"))

    assert _iniciar(_client_para(app, op), b["id"]).status_code == 200

    assert _status(db_session, a["id"]) == "pausada"
    assert len(_eventos(db_session, b["id"], "demanda.status_alterado")) == eventos_status_b  # B já estava em execução: nenhum evento de status novo
    (ativa,) = _ativas(db_session, op.id)
    assert ativa.demanda_id == b["id"]


# --------------------------------------------------------------------------------------
# 2 — outra sessão ativa em A impede a pausa
# --------------------------------------------------------------------------------------


def test_outra_sessao_ativa_em_a_impede_a_pausa_e_so_a_sessao_de_quem_trocou_fecha(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    hudson, raquel = operadores[0], operadores[1]
    a, (sessao_hudson, sessao_raquel) = _em_execucao_com_sessao(client_admin, hudson, raquel)
    b = _rascunho(client_admin, hudson)

    assert _iniciar(_client_para(app, hudson), b["id"]).status_code == 200

    assert _status(db_session, a["id"]) == "em_execucao"
    assert _sessao(db_session, sessao_hudson["id"]).status == "encerrada"
    assert _sessao(db_session, sessao_raquel["id"]).status == "ativa"
    assert [s.demanda_id for s in _ativas(db_session, raquel.id)] == [a["id"]]
    assert [s.demanda_id for s in _ativas(db_session, hudson.id)] == [b["id"]]
    assert _pausas_da_troca(db_session, a["id"]) == []
    assert len(_eventos(db_session, a["id"], "sessao_trabalho_encerrada")) == 1  # só a do Hudson
    linha_a = _linha_do_tempo_coerente(db_session, a["id"])
    assert linha_a[-1][0] == "em_execucao"  # nenhum intervalo novo em A


def test_sessao_departamental_ativa_em_a_tambem_impede_a_pausa(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    op = operadores[0]
    a, _ = _em_execucao_com_sessao(client_admin, op)
    # sessão puramente departamental ativa em A (sem usuário): também é "alguém trabalhando"
    departamento_id = _departamento(db_session, db_session.get(Empresa, op.empresa_id)).id
    agora = datetime.now(timezone.utc)
    evento_id = str(uuid.uuid4())
    db_session.execute(
        text(
            "INSERT INTO eventos (id, empresa_id, tipo, entidade_tipo, entidade_id, payload, occurred_at, created_at) "
            "VALUES (:id, :e, 'sessao_trabalho_iniciada', 'demanda', :d, '{}', :t, :t)"
        ),
        {"id": evento_id, "e": op.empresa_id, "d": a["id"], "t": agora},
    )
    db_session.add(
        SessaoTrabalho(
            id=str(uuid.uuid4()), empresa_id=op.empresa_id, demanda_id=a["id"], departamento_id=departamento_id, evento_inicio_id=evento_id,
            status="ativa", inicio_em=agora, created_at=agora, updated_at=agora,
        )
    )
    db_session.flush()
    b = _rascunho(client_admin, op)

    assert _iniciar(_client_para(app, op), b["id"]).status_code == 200
    assert _status(db_session, a["id"]) == "em_execucao"


# --------------------------------------------------------------------------------------
# 3 — A já não estava em execução: a sessão fecha, o status não é forçado
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ajuste",
    [
        "status = 'aguardando_cliente'",
        "status = 'pausada', pausa_origem = 'manual', pausada_em = now()",
        "status = 'bloqueada', motivo_bloqueio = 'teste de foco'",
    ],
)
def test_sessao_antiga_em_a_que_nao_esta_em_execucao_fecha_sem_forcar_pausada(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario], ajuste: str
) -> None:
    op = operadores[0]
    a, (sessao_a,) = _em_execucao_com_sessao(client_admin, op)
    # estado "velho": a Demanda saiu de execução por fora, deixando a sessão ativa para trás
    status_antes_do_ajuste = _status(db_session, a["id"])
    db_session.execute(text(f"UPDATE demandas SET {ajuste} WHERE id = :d"), {"d": a["id"]})
    db_session.flush()
    status_de_a = _status(db_session, a["id"])
    assert status_de_a != status_antes_do_ajuste
    eventos_status_a = len(_eventos(db_session, a["id"], "demanda.status_alterado"))
    b = _rascunho(client_admin, op)

    assert _iniciar(_client_para(app, op), b["id"]).status_code == 200

    assert _status(db_session, a["id"]) == status_de_a  # NUNCA forçado a `pausada` (nem reescrito)
    assert _sessao(db_session, sessao_a["id"]).status == "encerrada"  # a sessão fecha pela política existente
    assert len(_eventos(db_session, a["id"], "demanda.status_alterado")) == eventos_status_a  # nenhum evento de status novo em A
    assert _pausas_da_troca(db_session, a["id"]) == []
    assert _status(db_session, b["id"]) == "em_execucao"
    (ativa,) = _ativas(db_session, op.id)
    assert ativa.demanda_id == b["id"]


# --------------------------------------------------------------------------------------
# 4 — B inviável: A fica intacta
# --------------------------------------------------------------------------------------


def _estado_de_a(db: Session, a_id: str, sessao_id: str) -> tuple:
    return (
        _status(db, a_id),
        _sessao(db, sessao_id).status,
        len(_eventos(db, a_id, "sessao_trabalho_encerrada")),
        len(_eventos(db, a_id, "demanda.status_alterado")),
        len(_linha_do_tempo(db, a_id)),
    )


def test_b_sem_elegibilidade_recusa_e_nao_toca_em_a(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    op, outro = operadores[0], operadores[1]
    a, (sessao_a,) = _em_execucao_com_sessao(client_admin, op)
    b = _demanda(client_admin)  # em execução, responsável é outra pessoa
    _responsaveis(client_admin, b["id"], outro)
    antes = _estado_de_a(db_session, a["id"], sessao_a["id"])

    resposta = _iniciar(_client_para(app, op), b["id"])
    assert resposta.status_code in (403, 404), resposta.text

    assert _estado_de_a(db_session, a["id"], sessao_a["id"]) == antes
    assert [s.demanda_id for s in _ativas(db_session, op.id)] == [a["id"]]


def test_fora_do_expediente_recusa_e_nao_toca_em_a(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    from app.api.routes import demandas as rotas

    op = operadores[0]
    a, (sessao_a,) = _em_execucao_com_sessao(client_admin, op)
    b = _rascunho(client_admin, op)
    antes = _estado_de_a(db_session, a["id"], sessao_a["id"])

    original = rotas.demanda_service.regra_expediente
    rotas.demanda_service.regra_expediente = _regra_todos_os_dias(manha_inicio="00:00", manha_fim="00:00", tarde_inicio="00:00", tarde_fim="00:00")
    try:
        resposta = _iniciar(_client_para(app, op), b["id"])
    finally:
        rotas.demanda_service.regra_expediente = original
    assert resposta.status_code != 200, resposta.text

    assert _estado_de_a(db_session, a["id"], sessao_a["id"]) == antes
    assert _status(db_session, b["id"]) == "rascunho"


def test_falha_inesperada_depois_da_pausa_desfaz_a_pausa_de_a(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario], monkeypatch: pytest.MonkeyPatch
) -> None:
    """O pior caso: tudo de A já foi escrito (sessão fechada, pausada) e só então a abertura em B quebra — A volta inteira."""
    op = operadores[0]
    a, (sessao_a,) = _em_execucao_com_sessao(client_admin, op)
    b = _rascunho(client_admin, op)
    antes = _estado_de_a(db_session, a["id"], sessao_a["id"])

    def quebra(self, *args, **kwargs):
        raise RuntimeError("falha simulada ao abrir a sessão")

    monkeypatch.setattr(SessaoTrabalhoService, "abrir", quebra)
    cliente = _client_para(app, op)
    sem_propagar = TestClient(app, raise_server_exceptions=False, headers=dict(cliente.headers))
    assert _iniciar(sem_propagar, b["id"]).status_code == 500
    monkeypatch.undo()

    assert _estado_de_a(db_session, a["id"], sessao_a["id"]) == antes
    assert _status(db_session, a["id"]) == "em_execucao" and _status(db_session, b["id"]) == "rascunho"
    assert _pausas_da_troca(db_session, a["id"]) == []
    _linha_do_tempo_coerente(db_session, a["id"])


# --------------------------------------------------------------------------------------
# Responsabilidade EFETIVA por departamento continua valendo para B
# --------------------------------------------------------------------------------------


def _demanda_com_etapa_do_departamento(client_admin: TestClient, departamento_id: str) -> dict:
    from tests.test_fase_8a_workflow_progressao import _etapa
    from tests.test_sessao_trabalho_integridade import _demanda_com_workflow

    demanda = _demanda_com_workflow(client_admin, [_etapa("Criação"), _etapa("Revisão")], departamentoResponsavelIds=[departamento_id])  # escopo de acesso do departamento
    etapa_atual = next(e for e in demanda["workflowEtapas"] if e["ordem"] == 1)
    resposta = client_admin.put(
        f"/demandas/{demanda['id']}/workflow/etapas/{etapa_atual['id']}/responsaveis",
        json={"usuarioResponsavelIds": [], "departamentoResponsavelIds": [departamento_id]},
    )
    assert resposta.status_code == 200, resposta.text
    return demanda


def test_membro_do_departamento_da_etapa_de_b_troca_o_foco_e_pausa_a(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    op = operadores[0]
    departamento = _departamento(db_session, db_session.get(Empresa, op.empresa_id))
    op.departamento_id = departamento.id  # pelo ORM: a mesma Session atende a requisição
    db_session.flush()
    a, _ = _em_execucao_com_sessao(client_admin, op)
    b = _demanda_com_etapa_do_departamento(client_admin, departamento.id)

    assert _iniciar(_client_para(app, op), b["id"]).status_code == 200

    assert _status(db_session, a["id"]) == "pausada" and _status(db_session, b["id"]) == "em_execucao"
    (ativa,) = _ativas(db_session, op.id)
    assert ativa.demanda_id == b["id"] and ativa.workflow_etapa_id is not None  # a sessão nasce ligada à etapa do departamento


def test_quem_nao_e_do_departamento_da_etapa_de_b_nao_troca_o_foco_e_a_fica_intacta(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    op = operadores[0]
    departamento = _departamento(db_session, db_session.get(Empresa, op.empresa_id))  # o operador NÃO pertence a ele
    a, (sessao_a,) = _em_execucao_com_sessao(client_admin, op)
    b = _demanda_com_etapa_do_departamento(client_admin, departamento.id)
    _patch(client_admin, b["id"], status="em_execucao")  # já em execução: quem não é executor leva 403 (sem no-op silencioso)
    antes = _estado_de_a(db_session, a["id"], sessao_a["id"])

    resposta = _iniciar(_client_para(app, op), b["id"])
    assert resposta.status_code in (403, 404), resposta.text

    assert _estado_de_a(db_session, a["id"], sessao_a["id"]) == antes
    assert [s.demanda_id for s in _ativas(db_session, op.id)] == [a["id"]]


# --------------------------------------------------------------------------------------
# 5 — mesma demanda: idempotente
# --------------------------------------------------------------------------------------


def test_iniciar_na_mesma_demanda_nao_pausa_nem_fecha_nem_duplica_evento(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    op = operadores[0]
    a, (sessao_a,) = _em_execucao_com_sessao(client_admin, op)
    antes = _estado_de_a(db_session, a["id"], sessao_a["id"])
    iniciadas = len(_eventos(db_session, a["id"], "sessao_trabalho_iniciada"))

    for _ in range(2):
        assert _iniciar(_client_para(app, op), a["id"]).status_code == 200

    assert _estado_de_a(db_session, a["id"], sessao_a["id"]) == antes
    assert len(_eventos(db_session, a["id"], "sessao_trabalho_iniciada")) == iniciadas
    assert [s.id for s in _ativas(db_session, op.id)] == [sessao_a["id"]]  # a MESMA sessão (sem fechar/reabrir)
    assert _pausas_da_troca(db_session, a["id"]) == []


def test_cadeia_de_trocas_a_b_c_pausa_a_e_b_e_deixa_so_c(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    op = operadores[0]
    a, _ = _em_execucao_com_sessao(client_admin, op)
    b = _rascunho(client_admin, op)
    c = _rascunho(client_admin, op)
    cliente = _client_para(app, op)
    assert _iniciar(cliente, b["id"]).status_code == 200
    assert _iniciar(cliente, c["id"]).status_code == 200

    assert [_status(db_session, d["id"]) for d in (a, b, c)] == ["pausada", "pausada", "em_execucao"]
    (ativa,) = _ativas(db_session, op.id)
    assert ativa.demanda_id == c["id"]
    for d in (a, b, c):
        _linha_do_tempo_coerente(db_session, d["id"])
    # voltar para A: A sai de pausada (limpa a origem da pausa) e B fica pausada
    assert _iniciar(cliente, a["id"]).status_code == 200
    assert [_status(db_session, d["id"]) for d in (a, b, c)] == ["em_execucao", "pausada", "pausada"]
    assert db_session.get(Demanda, a["id"]).pausa_origem is None



# --------------------------------------------------------------------------------------
# Caminho REAL do Kanban: arrastar para Em execução = POST iniciar-trabalho (P1_KANBAN_FOCUS_SWITCH)
# --------------------------------------------------------------------------------------


def test_tarefa_ja_em_execucao_sem_sessao_ganha_a_sessao_no_arrasto_e_a_troca_seguinte_pausa_a(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    """O defeito real: A foi parar em Em execução SEM sessão (campo Status do drawer, ou criada já em execução). O arrasto de A para Em execução tem de abrir a sessão — sem ela, arrastar B
    não tem 'tarefa anterior' (a da sessão ativa) para pausar e as duas ficam em execução."""
    op = operadores[0]
    a = _demanda(client_admin)  # já em execução, sem sessão de ninguém
    _responsaveis(client_admin, a["id"], op)
    b = _rascunho(client_admin, op)
    assert _status(db_session, a["id"]) == "em_execucao" and _ativas(db_session, op.id) == []
    eventos_status_a = len(_eventos(db_session, a["id"], "demanda.status_alterado"))
    cliente = _client_para(app, op)

    # 1º arrasto (A → Em execução): o servidor só abre a sessão — nenhuma transição de status redundante
    assert _iniciar(cliente, a["id"]).status_code == 200
    (sessao_a,) = _ativas(db_session, op.id)
    assert sessao_a.demanda_id == a["id"]
    assert _status(db_session, a["id"]) == "em_execucao"
    assert len(_eventos(db_session, a["id"], "demanda.status_alterado")) == eventos_status_a
    assert len(_eventos(db_session, a["id"], "sessao_trabalho_iniciada")) == 1

    # 2º arrasto (B → Em execução): A pausa, B executa, exatamente 1 sessão ativa
    assert _iniciar(cliente, b["id"]).status_code == 200
    assert _status(db_session, a["id"]) == "pausada" and _status(db_session, b["id"]) == "em_execucao"
    (ativa,) = _ativas(db_session, op.id)
    assert ativa.demanda_id == b["id"]
    assert _sessao(db_session, sessao_a.id).status == "encerrada"
    assert len(_pausas_da_troca(db_session, a["id"])) == 1
    _linha_do_tempo_coerente(db_session, a["id"])


def test_patch_de_status_para_em_execucao_nao_abre_sessao_nem_pausa_a_anterior_so_o_comando_faz(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    """Contrato que explica o defeito: o PATCH de status (drawer, modal Nova tarefa) NÃO é 'começar a trabalhar'. Por isso o Kanban nunca usa PATCH para Em execução."""
    op = operadores[0]
    a, (sessao_a,) = _em_execucao_com_sessao(client_admin, op)
    b = _rascunho(client_admin, op)

    _patch(client_admin, b["id"], status="em_execucao")  # como o campo Status do drawer faz

    assert _status(db_session, b["id"]) == "em_execucao" and _status(db_session, a["id"]) == "em_execucao"  # A não foi pausada
    assert _sessao(db_session, sessao_a["id"]).status == "ativa" and [s.demanda_id for s in _ativas(db_session, op.id)] == [a["id"]]  # nenhuma sessão em B
    assert _pausas_da_troca(db_session, a["id"]) == []


def test_gestor_nao_executor_arrastando_a_e_b_so_move_status_sem_sessao_nem_pausa(
    app, db_session: Session, client_admin: TestClient, client_gestor: TestClient, usuario_gestor: Usuario, operadores: list[Usuario]
) -> None:
    """Movimento administrativo preservado: quem organiza o trabalho dos outros move o status das duas; nenhuma sessão pessoal nasce e ninguém é pausado por ele."""
    dono = operadores[0]
    a = _rascunho(client_admin, dono)
    b = _rascunho(client_admin, dono)

    assert _iniciar(client_gestor, a["id"]).status_code == 200
    assert _iniciar(client_gestor, b["id"]).status_code == 200

    assert _status(db_session, a["id"]) == "em_execucao" and _status(db_session, b["id"]) == "em_execucao"
    assert _ativas(db_session, usuario_gestor.id) == [] and _ativas(db_session, dono.id) == []
    assert _pausas_da_troca(db_session, a["id"]) == []


def test_cadeia_kanban_com_dois_executores_em_a_nao_pausa_a_e_reload_mostra_o_estado_do_servidor(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    """Hudson + Raquel executam A (ambos arrastaram A); Hudson arrasta B: A segue em execução com a sessão da Raquel. O que a tela mostra depois do reload (lista) é o estado do servidor."""
    hudson, raquel = operadores[0], operadores[1]
    a = _demanda(client_admin)
    _responsaveis(client_admin, a["id"], hudson, raquel)
    b = _rascunho(client_admin, hudson)
    assert _iniciar(_client_para(app, hudson), a["id"]).status_code == 200
    assert _iniciar(_client_para(app, raquel), a["id"]).status_code == 200

    assert _iniciar(_client_para(app, hudson), b["id"]).status_code == 200

    assert _status(db_session, a["id"]) == "em_execucao"
    assert [s.demanda_id for s in _ativas(db_session, hudson.id)] == [b["id"]]
    assert [s.demanda_id for s in _ativas(db_session, raquel.id)] == [a["id"]]
    # "reload": a listagem do Hudson reflete o servidor (B com 'trabalhando agora'; A em execução com a sessão da Raquel, não dele)
    resposta = _client_para(app, hudson).get("/demandas?limit=50").json()
    lista = {d["id"]: d for d in (resposta["items"] if isinstance(resposta, dict) else resposta)}
    assert lista[b["id"]]["trabalhandoAgora"] is True and lista[a["id"]]["trabalhandoAgora"] is False
    assert lista[a["id"]]["status"] == "em_execucao" and lista[b["id"]]["status"] == "em_execucao"

# --------------------------------------------------------------------------------------
# 6 — concorrência real (dados commitados, várias conexões)
# --------------------------------------------------------------------------------------


@pytest.fixture()
def cenario(test_engine):
    Fabrica = sessionmaker(bind=test_engine)
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(timezone.utc)
    with Fabrica() as db:
        empresa = Empresa(id=str(uuid.uuid4()), nome="Empresa Foco2", codigo_interno=f"FOCO2-{sufixo}".upper(), status="ativa", created_at=agora, updated_at=agora)
        db.add(empresa)
        db.flush()
        usuarios = []
        for i in (1, 2):
            usuario = Usuario(
                id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"foco2-{i}-{sufixo}", nome=f"Operador Foco {i}", email=f"foco2-{i}-{sufixo}@teste.taskfloww.local",
                perfil_base="operador", acesso_sistema=True, status="ativo", created_at=agora, updated_at=agora,
            )
            db.add(usuario)
            db.flush()
            usuarios.append(usuario.id)
        demandas = []
        for i in (1, 2, 3):
            demanda = Demanda(
                id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"G26{sufixo[:5]}{i}", ano_referencia=26, sequencial_referencia=i,
                numero_operacional=i, identificador=f"#{i}", nome=f"Foco2 {i}", status="planejada", prioridade="media", sinalizada=False, created_at=agora, updated_at=agora,
            )
            db.add(demanda)
            db.flush()
            for usuario_id in usuarios:
                db.add(DemandaResponsavel(demanda_id=demanda.id, usuario_id=usuario_id, created_at=agora))
            demandas.append(demanda.id)
        db.commit()
        ids = {"empresa": empresa.id, "usuarios": usuarios, "demandas": demandas}
    try:
        yield Fabrica, ids
    finally:
        with Fabrica() as db:
            db.execute(text("DELETE FROM regra_expediente WHERE empresa_id = :e"), {"e": ids["empresa"]})
            for tabela in ("sessoes_trabalho", "eventos"):
                db.execute(text(f"DELETE FROM {tabela} WHERE empresa_id = :e"), {"e": ids["empresa"]})
            db.execute(text("DELETE FROM demandas WHERE empresa_id = :e"), {"e": ids["empresa"]})
            db.execute(text("DELETE FROM usuarios WHERE empresa_id = :e"), {"e": ids["empresa"]})
            db.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": ids["empresa"]})
            db.commit()


def _iniciar_no_servico(Fabrica, usuario_id: str, demanda_id: str) -> None:
    with Fabrica() as db:
        DemandaService().iniciar_trabalho(db, db.get(Demanda, demanda_id), actor=db.get(Usuario, usuario_id))


def _correr(Fabrica, tarefas: list[tuple[str, str]]) -> list[str]:
    barreira = threading.Barrier(len(tarefas))
    resultados: list[str] = []
    trava = threading.Lock()

    def executar(usuario_id: str, demanda_id: str) -> None:
        with Fabrica() as db:
            servico = DemandaService()
            ator = db.get(Usuario, usuario_id)
            demanda = db.get(Demanda, demanda_id)
            barreira.wait(timeout=10)
            try:
                servico.iniciar_trabalho(db, demanda, actor=ator)
                saida = "ok"
            except Exception as exc:  # noqa: BLE001 — só o TIPO importa: erro de domínio é válido; deadlock/500 não
                saida = type(exc).__name__
            with trava:
                resultados.append(saida)

    threads = [threading.Thread(target=executar, args=tarefa) for tarefa in tarefas]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
        assert not t.is_alive(), "thread presa — possível deadlock"
    return resultados


def _ativas_da_empresa(db: Session, empresa_id: str) -> list[SessaoTrabalho]:
    return list(db.scalars(select(SessaoTrabalho).where(SessaoTrabalho.empresa_id == empresa_id, SessaoTrabalho.status == "ativa")).all())


def test_duplo_clique_pausa_a_uma_unica_vez(cenario) -> None:
    Fabrica, ids = cenario
    u1 = ids["usuarios"][0]
    a, b, _ = ids["demandas"]
    _iniciar_no_servico(Fabrica, u1, a)

    resultados = _correr(Fabrica, [(u1, b), (u1, b)])

    assert resultados == ["ok", "ok"], resultados  # a segunda chamada é idempotente (nada a fazer), nunca um erro nem um 500
    with Fabrica() as db:
        assert db.get(Demanda, a).status == "pausada" and db.get(Demanda, b).status == "em_execucao"
        ativas = _ativas_da_empresa(db, ids["empresa"])
        assert [(s.usuario_id, s.demanda_id) for s in ativas] == [(u1, b)]
        pausas = [e for e in db.scalars(select(Evento).where(Evento.entidade_id == a, Evento.tipo == "demanda.status_alterado")).all() if e.payload.get("para") == "pausada"]
        assert len(pausas) == 1
        assert db.scalar(select(func.count()).select_from(Evento).where(Evento.entidade_id == a, Evento.tipo == "sessao_trabalho_encerrada")) == 1
        assert db.scalar(select(func.count()).select_from(Evento).where(Evento.entidade_id == b, Evento.tipo == "sessao_trabalho_iniciada")) == 1


def test_dois_usuarios_trocando_de_foco_em_sentidos_opostos_nao_se_travam(cenario) -> None:
    Fabrica, ids = cenario
    u1, u2 = ids["usuarios"]
    a, b, _ = ids["demandas"]
    _iniciar_no_servico(Fabrica, u1, a)
    _iniciar_no_servico(Fabrica, u2, b)

    resultados = _correr(Fabrica, [(u1, b), (u2, a)])

    assert resultados == ["ok", "ok"], resultados  # sem deadlock (locks das duas Demandas em ordem de id)
    with Fabrica() as db:
        ativas = _ativas_da_empresa(db, ids["empresa"])
        assert sorted((s.usuario_id, s.demanda_id) for s in ativas) == sorted([(u1, b), (u2, a)])
        # cada Demanda com alguém trabalhando está em execução; nenhuma ficou pausada por engano
        assert db.get(Demanda, a).status == "em_execucao" and db.get(Demanda, b).status == "em_execucao"


def test_outro_usuario_fechando_a_sessao_em_a_ao_mesmo_tempo_deixa_estado_coerente(cenario) -> None:
    Fabrica, ids = cenario
    u1, u2 = ids["usuarios"]
    a, b, _ = ids["demandas"]
    _iniciar_no_servico(Fabrica, u1, a)
    _iniciar_no_servico(Fabrica, u2, a)
    barreira = threading.Barrier(2)
    erros: list[str] = []

    def troca() -> None:
        with Fabrica() as db:
            servico = DemandaService()
            ator, demanda = db.get(Usuario, u1), db.get(Demanda, b)
            barreira.wait(timeout=10)
            try:
                servico.iniciar_trabalho(db, demanda, actor=ator)
            except Exception as exc:  # noqa: BLE001
                erros.append(type(exc).__name__)

    def fecha() -> None:
        with Fabrica() as db:
            barreira.wait(timeout=10)
            try:
                SessaoTrabalhoService().encerrar_ativas_da_demanda(
                    db, empresa_id=ids["empresa"], demanda_id=a, motivo_encerramento=MOTIVO_TROCA_RESPONSAVEL, fim_em=datetime.now(timezone.utc), usuario_ids=[u2]
                )
                db.commit()
            except Exception as exc:  # noqa: BLE001
                erros.append(type(exc).__name__)

    threads = [threading.Thread(target=troca), threading.Thread(target=fecha)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
        assert not t.is_alive(), "thread presa — possível deadlock"

    assert erros == [], erros
    with Fabrica() as db:
        sessoes_a = list(db.scalars(select(SessaoTrabalho).where(SessaoTrabalho.demanda_id == a)).all())
        assert all(s.status == "encerrada" for s in sessoes_a)  # as duas fecharam, cada uma UMA vez
        fins = db.scalar(select(func.count()).select_from(Evento).where(Evento.entidade_id == a, Evento.tipo == "sessao_trabalho_encerrada"))
        assert fins == len(sessoes_a) == 2
        status_a = db.get(Demanda, a).status
        # corrida legítima: se o fechamento do u2 venceu, u1 era o último e A pausou; se a troca do u1 venceu, u2 ainda estava lá e A seguiu em execução
        assert status_a in ("pausada", "em_execucao")
        pausas = [e for e in db.scalars(select(Evento).where(Evento.entidade_id == a, Evento.tipo == "demanda.status_alterado")).all() if e.payload.get("para") == "pausada"]
        assert len(pausas) == (1 if status_a == "pausada" else 0)
        assert [(s.usuario_id, s.demanda_id) for s in _ativas_da_empresa(db, ids["empresa"])] == [(u1, b)]
