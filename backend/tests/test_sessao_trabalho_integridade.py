"""Fase 11B.2A — integridade das sessões de trabalho como fonte de TEMPO REALIZADO.

Cobre: validação de abertura (tenant/demanda/etapa), uma sessão ativa por pessoa (409 `SESSAO_ATIVA_EXISTENTE` + índice único no banco), sessão departamental sem
multiplicação, encerramento automático e idempotente nas transições (pausa, bloqueio, aguardando cliente, conclusão, cancelamento, arquivamento, mudança de etapa,
troca de responsável, aprovação/rejeição), agregação (cancelada fora, `as_of` único) e isolamento entre empresas.

As aberturas e as transições passam pela API real (a mesma que a UI usa); a corrida real entre conexões está em test_sessao_trabalho_concorrencia.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository
from app.services.sessao_trabalho_service import SessaoTrabalhoService
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _client_para as client_do
from tests.test_demanda import dentro_do_expediente  # noqa: F401  (fixture)
from tests.test_fase_8a_workflow_progressao import _demanda_com_workflow, _etapa, _por_ordem, _url
from tests.test_sessao_trabalho import _departamento, _usuario


# ------------------------------------------------------------------------------------------------------------------------------------------------
# auxiliares
# ------------------------------------------------------------------------------------------------------------------------------------------------


def _demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _abrir(client: TestClient, demanda_id: str, usuario_id: str | None = None, *, etapa_id: str | None = None, departamento_id: str | None = None):
    corpo: dict = {"demandaId": demanda_id}
    if usuario_id:
        corpo["usuarioId"] = usuario_id
    if departamento_id:
        corpo["departamentoId"] = departamento_id
    if etapa_id:
        corpo["workflowEtapaId"] = etapa_id
    return client.post("/sessoes-trabalho/abrir", json=corpo)


def _abrir_ok(client: TestClient, demanda_id: str, usuario_id: str | None = None, **kw) -> dict:
    resposta = _abrir(client, demanda_id, usuario_id, **kw)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _sessoes(db: Session, demanda_id: str) -> list[SessaoTrabalho]:
    db.expire_all()
    return list(db.scalars(select(SessaoTrabalho).where(SessaoTrabalho.demanda_id == demanda_id).order_by(SessaoTrabalho.inicio_em.asc())).all())


def _ativas(db: Session, demanda_id: str) -> list[SessaoTrabalho]:
    return [s for s in _sessoes(db, demanda_id) if s.status == "ativa"]


def _sessao(db: Session, sessao_id: str) -> SessaoTrabalho:
    db.expire_all()
    return db.get(SessaoTrabalho, sessao_id)


def _eventos_fim(db: Session, demanda_id: str) -> list[Evento]:
    return list(db.scalars(select(Evento).where(Evento.entidade_id == demanda_id, Evento.tipo == "sessao_trabalho_encerrada")).all())


def _patch(client: TestClient, demanda_id: str, **corpo):
    resposta = client.patch(f"/demandas/{demanda_id}", json=corpo)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


@pytest.fixture()
def operadores(db_session: Session, empresa: Empresa) -> list[Usuario]:
    return [_usuario(db_session, empresa) for _ in range(3)]


# ------------------------------------------------------------------------------------------------------------------------------------------------
# A. validação ao abrir: tenant, demanda, etapa
# ------------------------------------------------------------------------------------------------------------------------------------------------


def test_abre_sessao_valida(client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id)
    assert sessao["status"] == "ativa" and sessao["demandaId"] == demanda["id"] and sessao["usuarioId"] == usuario_operador.id
    assert sessao["workflowEtapaId"] is None


def test_demanda_inexistente_e_404(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = _abrir(client_admin, str(uuid.uuid4()), usuario_operador.id)
    assert resposta.status_code == 404


def test_demanda_de_outra_empresa_e_404_igual_a_inexistente(
    db_session: Session, client_admin: TestClient, usuario_operador: Usuario, outra_empresa: Empresa
) -> None:
    admin_b = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="adminb")
    demanda_b = _demanda(client_do_(admin_b, db_session))
    resposta = _abrir(client_admin, demanda_b["id"], usuario_operador.id)
    inexistente = _abrir(client_admin, str(uuid.uuid4()), usuario_operador.id)
    assert resposta.status_code == 404 and resposta.json() == inexistente.json()  # nunca confirma que a demanda existe em outra empresa
    assert _sessoes(db_session, demanda_b["id"]) == []


def client_do_(usuario: Usuario, db: Session) -> TestClient:
    from app.main import app as aplicacao

    db.flush()
    return client_do(aplicacao, usuario)


@pytest.mark.parametrize("status", ["concluida", "cancelada", "pausada", "aguardando_cliente"])
def test_demanda_nao_executavel_e_409(client_admin: TestClient, usuario_operador: Usuario, status: str) -> None:
    demanda = _demanda(client_admin)
    _patch(client_admin, demanda["id"], status=status)
    resposta = _abrir(client_admin, demanda["id"], usuario_operador.id)
    assert resposta.status_code == 409
    assert resposta.json()["detail"]["code"] == "DEMANDA_NAO_EXECUTAVEL"


def test_demanda_bloqueada_e_409(client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    _patch(client_admin, demanda["id"], status="bloqueada", motivoBloqueio="Aguardando material")
    resposta = _abrir(client_admin, demanda["id"], usuario_operador.id)
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "DEMANDA_NAO_EXECUTAVEL"


def test_demanda_arquivada_e_409(client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "teste"}).status_code == 200
    resposta = _abrir(client_admin, demanda["id"], usuario_operador.id)
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "DEMANDA_NAO_EXECUTAVEL"


def test_volta_a_ser_executavel_permite_iniciar_de_novo(client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    _patch(client_admin, demanda["id"], status="pausada")
    assert _abrir(client_admin, demanda["id"], usuario_operador.id).status_code == 409
    _patch(client_admin, demanda["id"], status="planejada")
    assert _abrir(client_admin, demanda["id"], usuario_operador.id).status_code == 201


def test_etapa_valida_da_demanda_fica_ligada_a_sessao(client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criação"), _etapa("Revisão")])
    etapas = _por_ordem(demanda)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id, etapa_id=etapas[0]["id"])
    assert sessao["workflowEtapaId"] == etapas[0]["id"]


def test_sem_etapa_continua_aceito_em_demanda_com_workflow(client_admin: TestClient, usuario_operador: Usuario) -> None:
    """CALLER_WITHOUT_STEP: o único chamador atual (Tráfego → 'Iniciar sessão de teste') não envia a etapa; torná-la obrigatória é decisão de produto."""
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criação")])
    assert _abrir(client_admin, demanda["id"], usuario_operador.id).status_code == 201


def test_etapa_inexistente_422(client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    resposta = _abrir(client_admin, demanda["id"], usuario_operador.id, etapa_id=str(uuid.uuid4()))
    assert resposta.status_code == 422 and not _ativas_vazio(resposta)


def _ativas_vazio(resposta) -> bool:  # a resposta de erro nunca traz uma sessão
    return "id" in resposta.json() and "status" in resposta.json()


def test_etapa_de_outra_demanda_422(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    com_workflow = _demanda_com_workflow(client_admin, [_etapa("Criação")])
    outra = _demanda(client_admin)
    resposta = _abrir(client_admin, outra["id"], usuario_operador.id, etapa_id=com_workflow["workflowEtapas"][0]["id"])
    assert resposta.status_code == 422
    assert _sessoes(db_session, outra["id"]) == []


def test_etapa_de_outra_empresa_422_com_a_mesma_mensagem(
    db_session: Session, client_admin: TestClient, usuario_operador: Usuario, outra_empresa: Empresa
) -> None:
    admin_b = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="adminb2")
    etapa_b = _demanda_com_workflow(client_do_(admin_b, db_session), [_etapa("Criação")])["workflowEtapas"][0]["id"]
    demanda = _demanda(client_admin)
    resposta = _abrir(client_admin, demanda["id"], usuario_operador.id, etapa_id=etapa_b)
    inexistente = _abrir(client_admin, demanda["id"], usuario_operador.id, etapa_id=str(uuid.uuid4()))
    assert resposta.status_code == 422 and resposta.json() == inexistente.json()


def test_usuario_de_outra_empresa_continua_422(db_session: Session, client_admin: TestClient, outra_empresa: Empresa) -> None:
    demanda = _demanda(client_admin)
    alheio = _usuario(db_session, outra_empresa)
    assert _abrir(client_admin, demanda["id"], alheio.id).status_code == 422


def test_usuario_e_departamento_juntos_continua_422(db_session: Session, client_admin: TestClient, empresa: Empresa, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    resposta = _abrir(client_admin, demanda["id"], usuario_operador.id, departamento_id=_departamento(db_session, empresa).id)
    assert resposta.status_code == 422


def test_operador_nao_abre_sessao(client_operador: TestClient, client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    assert _abrir(client_operador, demanda["id"], usuario_operador.id).status_code == 403


# ------------------------------------------------------------------------------------------------------------------------------------------------
# B. uma sessão ativa por pessoa
# ------------------------------------------------------------------------------------------------------------------------------------------------


def test_segunda_sessao_da_mesma_pessoa_na_mesma_demanda_e_409(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    primeira = _abrir_ok(client_admin, demanda["id"], usuario_operador.id)
    resposta = _abrir(client_admin, demanda["id"], usuario_operador.id)
    assert resposta.status_code == 409
    assert resposta.json()["detail"] == {"code": "SESSAO_ATIVA_EXISTENTE", "message": "Você já possui uma atividade em execução."}
    anterior = _sessao(db_session, primeira["id"])
    assert anterior.status == "ativa" and anterior.fim_em is None  # NUNCA encerrada em silêncio
    assert len(_sessoes(db_session, demanda["id"])) == 1


def test_segunda_sessao_da_mesma_pessoa_em_outra_demanda_e_409_sem_vazar_a_primeira(
    db_session: Session, client_admin: TestClient, usuario_operador: Usuario
) -> None:
    x, y = _demanda(client_admin), _demanda(client_admin)
    primeira = _abrir_ok(client_admin, x["id"], usuario_operador.id)
    resposta = _abrir(client_admin, y["id"], usuario_operador.id)
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "SESSAO_ATIVA_EXISTENTE"
    assert x["id"] not in resposta.text and primeira["id"] not in resposta.text  # sem dados da outra sessão na resposta
    assert _sessoes(db_session, y["id"]) == []
    assert _sessao(db_session, primeira["id"]).status == "ativa"


def test_pessoas_diferentes_trabalham_ao_mesmo_tempo(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    x, y = _demanda(client_admin), _demanda(client_admin)
    _abrir_ok(client_admin, x["id"], operadores[0].id)
    _abrir_ok(client_admin, y["id"], operadores[1].id)
    _abrir_ok(client_admin, x["id"], operadores[2].id)  # duas pessoas na mesma demanda também pode
    assert len(_ativas(db_session, x["id"])) == 2 and len(_ativas(db_session, y["id"])) == 1


def test_pode_iniciar_outra_depois_de_fechar_a_anterior(client_admin: TestClient, usuario_operador: Usuario) -> None:
    x, y = _demanda(client_admin), _demanda(client_admin)
    primeira = _abrir_ok(client_admin, x["id"], usuario_operador.id)
    assert client_admin.post(f"/sessoes-trabalho/{primeira['id']}/fechar", json={"motivoEncerramento": "pausa"}).status_code == 200
    assert _abrir(client_admin, y["id"], usuario_operador.id).status_code == 201


def test_banco_impede_duas_ativas_da_mesma_pessoa_mesmo_sem_passar_pelo_service(db_session: Session, empresa: Empresa, usuario_operador: Usuario) -> None:
    """A barreira real contra a corrida é o índice parcial único (empresa_id, usuario_id) WHERE status='ativa' — não depende do SELECT do service."""
    agora = datetime.now(timezone.utc)

    def inserir(demanda_id: str, status: str = "ativa") -> None:
        db_session.execute(
            text(
                "INSERT INTO sessoes_trabalho (id, empresa_id, demanda_id, usuario_id, evento_inicio_id, status, inicio_em, fim_em, evento_fim_id, duracao_segundos, created_at, updated_at) "
                "VALUES (:id, :e, :d, :u, :ev, :st, :ini, :fim, :evf, :dur, :ini, :ini)"
            ),
            {"id": str(uuid.uuid4()), "e": empresa.id, "d": demanda_id, "u": usuario_operador.id, "ev": str(uuid.uuid4()), "st": status, "ini": agora,
             "fim": agora if status == "encerrada" else None, "evf": str(uuid.uuid4()) if status == "encerrada" else None, "dur": 0 if status == "encerrada" else None},
        )

    inserir(str(uuid.uuid4()))
    inserir(str(uuid.uuid4()), "encerrada")  # encerradas não contam
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            inserir(str(uuid.uuid4()))


def test_indice_do_banco_nao_cobre_sessao_departamental_nem_outra_empresa(db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    repo = SessaoTrabalhoRepository()
    service = SessaoTrabalhoService(repository=repo)
    agora = datetime.now(timezone.utc)
    # duas sessões departamentais (sem usuário) em demandas diferentes: permitido
    for _ in range(2):
        service.open_session(db_session, empresa_id=empresa.id, demanda_id=str(uuid.uuid4()), evento_inicio_id=str(uuid.uuid4()), inicio_em=agora, departamento_id=departamento.id)
    # o MESMO índice não confunde empresas (usuários diferentes de empresas diferentes)
    u_a, u_b = _usuario(db_session, empresa), _usuario(db_session, outra_empresa)
    service.open_session(db_session, empresa_id=empresa.id, demanda_id=str(uuid.uuid4()), evento_inicio_id=str(uuid.uuid4()), inicio_em=agora, usuario_id=u_a.id)
    service.open_session(db_session, empresa_id=outra_empresa.id, demanda_id=str(uuid.uuid4()), evento_inicio_id=str(uuid.uuid4()), inicio_em=agora, usuario_id=u_b.id)


def test_sessao_departamental_sem_pessoa_nao_e_multiplicada_pelos_membros(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    departamento = _departamento(db_session, empresa)
    membros = [_usuario(db_session, empresa) for _ in range(4)]
    for membro in membros:
        db_session.execute(text("UPDATE usuarios SET departamento_id = :d WHERE id = :u"), {"d": departamento.id, "u": membro.id})
    demanda = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, demanda["id"], departamento_id=departamento.id)
    assert sessao["usuarioId"] is None and sessao["departamentoId"] == departamento.id
    as_of = datetime.now(timezone.utc)
    horas, quantidade = SessaoTrabalhoRepository().horas_departamento(db_session, empresa_id=empresa.id, departamento_id=departamento.id, as_of=as_of)
    assert quantidade == 1  # UMA sessão, não uma por membro
    assert horas >= 0


# ------------------------------------------------------------------------------------------------------------------------------------------------
# C. encerramento automático nas transições da Demanda
# ------------------------------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "corpo, motivo",
    [
        ({"status": "pausada"}, "pausa"),
        ({"status": "bloqueada", "motivoBloqueio": "Sem material"}, "bloqueio"),
        ({"status": "aguardando_cliente"}, "aguardando_cliente"),
        ({"status": "concluida"}, "conclusao"),
        ({"status": "cancelada"}, "cancelamento"),
    ],
)
def test_transicao_de_status_encerra_a_sessao_ativa(db_session: Session, client_admin: TestClient, usuario_operador: Usuario, corpo: dict, motivo: str) -> None:
    demanda = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id)
    _patch(client_admin, demanda["id"], **corpo)
    fechada = _sessao(db_session, sessao["id"])
    assert fechada.status == "encerrada" and fechada.motivo_encerramento == motivo
    assert fechada.fim_em is not None and fechada.duracao_segundos is not None and fechada.duracao_segundos >= 0 and fechada.evento_fim_id
    fim = _eventos_fim(db_session, demanda["id"])
    assert len(fim) == 1 and fim[0].payload["motivoEncerramento"] == motivo and fim[0].payload["automatico"] is True and fim[0].id == fechada.evento_fim_id


def test_arquivar_demanda_encerra_a_sessao_ativa(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id)
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "duplicada"}).status_code == 200
    fechada = _sessao(db_session, sessao["id"])
    assert fechada.status == "encerrada" and fechada.motivo_encerramento == "arquivamento"


def test_transicao_encerra_todas_as_sessoes_da_demanda_e_so_dela(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    x, y = _demanda(client_admin), _demanda(client_admin)
    a = _abrir_ok(client_admin, x["id"], operadores[0].id)
    b = _abrir_ok(client_admin, x["id"], operadores[1].id)
    de_outra = _abrir_ok(client_admin, y["id"], operadores[2].id)
    _patch(client_admin, x["id"], status="pausada")
    assert _sessao(db_session, a["id"]).status == "encerrada" and _sessao(db_session, b["id"]).status == "encerrada"
    assert _sessao(db_session, de_outra["id"]).status == "ativa"  # sessão de OUTRA demanda nunca é tocada


def test_entrar_em_execucao_nao_encerra_nada(db_session: Session, client_admin: TestClient, usuario_operador: Usuario, dentro_do_expediente) -> None:
    demanda = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id)
    _patch(client_admin, demanda["id"], status="em_execucao")
    assert _sessao(db_session, sessao["id"]).status == "ativa"


def test_editar_outros_campos_nao_encerra_nada(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id)
    _patch(client_admin, demanda["id"], nome="Novo nome")
    assert _sessao(db_session, sessao["id"]).status == "ativa"


def test_repetir_a_transicao_e_idempotente(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id)
    _patch(client_admin, demanda["id"], status="pausada")
    antes = _sessao(db_session, sessao["id"])
    marcas = (antes.fim_em, antes.duracao_segundos, antes.evento_fim_id, antes.updated_at, antes.motivo_encerramento)
    _patch(client_admin, demanda["id"], status="pausada")  # repete (sem mudança de status)
    _patch(client_admin, demanda["id"], status="planejada")  # outra saída de em_execucao: nada ativo para fechar
    depois = _sessao(db_session, sessao["id"])
    assert (depois.fim_em, depois.duracao_segundos, depois.evento_fim_id, depois.updated_at, depois.motivo_encerramento) == marcas
    assert len(_eventos_fim(db_session, demanda["id"])) == 1  # um fechamento, um evento


def test_encerramento_direto_do_service_e_idempotente(db_session: Session, empresa: Empresa, usuario_operador: Usuario, client_admin: TestClient) -> None:
    demanda = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id)
    servico = SessaoTrabalhoService()
    quando = datetime.now(timezone.utc) + timedelta(seconds=90)
    primeira = servico.encerrar_ativas_da_demanda(db_session, empresa_id=empresa.id, demanda_id=demanda["id"], motivo_encerramento="pausa", fim_em=quando)
    segunda = servico.encerrar_ativas_da_demanda(db_session, empresa_id=empresa.id, demanda_id=demanda["id"], motivo_encerramento="bloqueio", fim_em=quando + timedelta(hours=5))
    assert [s.id for s in primeira] == [sessao["id"]] and segunda == []
    fechada = _sessao(db_session, sessao["id"])
    assert fechada.motivo_encerramento == "pausa" and fechada.fim_em == quando
    assert 85 <= fechada.duracao_segundos <= 95 + 5  # fim - início (início ~ agora)
    assert len(_eventos_fim(db_session, demanda["id"])) == 1


def test_encerramento_automatico_nao_cruza_empresa(db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_operador: Usuario, client_admin: TestClient) -> None:
    demanda = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id)
    fechadas = SessaoTrabalhoService().encerrar_ativas_da_demanda(
        db_session, empresa_id=outra_empresa.id, demanda_id=demanda["id"], motivo_encerramento="pausa", fim_em=datetime.now(timezone.utc)
    )
    assert fechadas == [] and _sessao(db_session, sessao["id"]).status == "ativa"


def test_cancelada_nao_e_reaberta_nem_fechada_de_novo(db_session: Session, empresa: Empresa, client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda(client_admin)
    agora = datetime.now(timezone.utc)
    db_session.add(SessaoTrabalho(
        id=str(uuid.uuid4()), empresa_id=empresa.id, demanda_id=demanda["id"], usuario_id=usuario_operador.id, evento_inicio_id=str(uuid.uuid4()),
        status="cancelada", inicio_em=agora, created_at=agora, updated_at=agora,
    ))
    db_session.flush()
    _patch(client_admin, demanda["id"], status="pausada")
    assert [s.status for s in _sessoes(db_session, demanda["id"])] == ["cancelada"]
    assert _eventos_fim(db_session, demanda["id"]) == []


# ---- troca de responsável ----------------------------------------------------------------------------------------------------------------------


def test_remover_responsavel_encerra_so_a_sessao_dele_naquela_demanda(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    a, b, c = operadores
    x, y = _demanda(client_admin, usuarioResponsavelIds=[a.id, b.id]), _demanda(client_admin, usuarioResponsavelIds=[a.id])
    sessao_a_x = _abrir_ok(client_admin, x["id"], a.id)
    sessao_b_x = _abrir_ok(client_admin, x["id"], b.id)
    _patch(client_admin, x["id"], usuarioResponsavelIds=[b.id, c.id])  # a sai, c entra
    fechada = _sessao(db_session, sessao_a_x["id"])
    assert fechada.status == "encerrada" and fechada.motivo_encerramento == "troca_responsavel"
    assert _sessao(db_session, sessao_b_x["id"]).status == "ativa"  # quem ficou segue trabalhando
    assert [s for s in _sessoes(db_session, x["id"]) if s.usuario_id == c.id] == []  # o novo responsável começa do ZERO (nada é transferido)
    # a mesma pessoa pode ter sessão em OUTRA demanda onde continua responsável (a sessão dela em y só existiria se não estivesse ativa em x)
    assert _abrir(client_admin, y["id"], a.id).status_code == 201


def test_remover_responsavel_sem_sessao_ativa_nao_faz_nada(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    a, b, _ = operadores
    x = _demanda(client_admin, usuarioResponsavelIds=[a.id, b.id])
    sessao_b = _abrir_ok(client_admin, x["id"], b.id)
    _patch(client_admin, x["id"], usuarioResponsavelIds=[b.id])  # a sai, mas a não tinha sessão
    assert _sessao(db_session, sessao_b["id"]).status == "ativa"
    assert _eventos_fim(db_session, x["id"]) == []


def test_remover_departamento_encerra_a_sessao_departamental(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    d1, d2 = _departamento(db_session, empresa), _departamento(db_session, empresa)
    x = _demanda(client_admin, departamentoResponsavelIds=[d1.id, d2.id])
    s1, s2 = _abrir_ok(client_admin, x["id"], departamento_id=d1.id), _abrir_ok(client_admin, x["id"], departamento_id=d2.id)
    _patch(client_admin, x["id"], departamentoResponsavelIds=[d2.id])
    assert _sessao(db_session, s1["id"]).motivo_encerramento == "troca_responsavel"
    assert _sessao(db_session, s2["id"]).status == "ativa"


# ------------------------------------------------------------------------------------------------------------------------------------------------
# D. workflow: mudança de etapa, aprovação e rejeição
# ------------------------------------------------------------------------------------------------------------------------------------------------


def test_concluir_etapa_encerra_a_sessao_dela_e_a_nova_nasce_ligada_a_etapa_nova(
    db_session: Session, client_admin: TestClient, usuario_operador: Usuario
) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criação"), _etapa("Revisão")])
    e1, e2 = _por_ordem(demanda)
    s1 = _abrir_ok(client_admin, demanda["id"], usuario_operador.id, etapa_id=e1["id"])
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    fechada = _sessao(db_session, s1["id"])
    assert fechada.status == "encerrada" and fechada.motivo_encerramento == "mudanca_etapa" and fechada.workflow_etapa_id == e1["id"]
    assert _ativas(db_session, demanda["id"]) == []  # a etapa nova NÃO herda a sessão
    s2 = _abrir_ok(client_admin, demanda["id"], usuario_operador.id, etapa_id=e2["id"])
    assert s2["workflowEtapaId"] == e2["id"]


def test_concluir_a_ultima_etapa_fecha_com_conclusao(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Única")])
    (e1,) = _por_ordem(demanda)
    s1 = _abrir_ok(client_admin, demanda["id"], usuario_operador.id, etapa_id=e1["id"])
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert _sessao(db_session, s1["id"]).motivo_encerramento == "conclusao"


def test_sessao_sem_etapa_nao_e_encerrada_por_mudanca_de_etapa(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    """Sessão no nível da demanda (sem etapa) não pertence à etapa que terminou — não se deduz etapa; ela acaba pelas transições da DEMANDA."""
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criação"), _etapa("Revisão")])
    e1, _ = _por_ordem(demanda)
    da_demanda = _abrir_ok(client_admin, demanda["id"], operadores[0].id)
    da_etapa = _abrir_ok(client_admin, demanda["id"], operadores[1].id, etapa_id=e1["id"])
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert _sessao(db_session, da_etapa["id"]).status == "encerrada"
    assert _sessao(db_session, da_demanda["id"]).status == "ativa"


def test_aprovar_encerra_a_sessao_da_etapa_de_aprovacao(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criação"), _etapa("Aprovação", "aprovacao"), _etapa("Publicação")])
    e1, e2, e3 = _por_ordem(demanda)
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id, etapa_id=e2["id"])
    assert client_admin.post(_url(demanda["id"], e2["id"], "aprovar")).status_code == 200
    assert _sessao(db_session, sessao["id"]).motivo_encerramento == "mudanca_etapa"
    assert _ativas(db_session, demanda["id"]) == []


def test_rejeitar_encerra_a_sessao_da_aprovacao_e_nao_abre_nenhuma_nova(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criação"), _etapa("Aprovação", "aprovacao")])
    e1, e2 = _por_ordem(demanda)
    s_exec = _abrir_ok(client_admin, demanda["id"], operadores[0].id, etapa_id=e1["id"])
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    s_aprov = _abrir_ok(client_admin, demanda["id"], operadores[1].id, etapa_id=e2["id"])
    total_antes = len(_sessoes(db_session, demanda["id"]))
    resposta = client_admin.post(_url(demanda["id"], e2["id"], "rejeitar"), json={"motivo": "Não segue o manual"})
    assert resposta.status_code == 200, resposta.text
    assert _sessao(db_session, s_exec["id"]).motivo_encerramento == "mudanca_etapa"  # já tinha fechado ao concluir
    assert _sessao(db_session, s_aprov["id"]).status == "encerrada" and _sessao(db_session, s_aprov["id"]).motivo_encerramento == "mudanca_etapa"
    # a etapa anterior foi REABERTA, mas ninguém começou a trabalhar sozinho: nenhuma sessão nova
    assert _ativas(db_session, demanda["id"]) == [] and len(_sessoes(db_session, demanda["id"])) == total_antes
    reaberta = db_session.get(DemandaWorkflowEtapa, e1["id"])
    db_session.refresh(reaberta)
    assert reaberta.status == "pendente"


def test_rejeicao_recusada_nao_encerra_sessao(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    """Rollback conjunto: a rejeição inválida (etapa que não é de aprovação) não pode deixar a sessão encerrada."""
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criação"), _etapa("Aprovação", "aprovacao")])
    e1, _ = _por_ordem(demanda)
    sessao = _abrir_ok(client_admin, demanda["id"], usuario_operador.id, etapa_id=e1["id"])
    assert client_admin.post(_url(demanda["id"], e1["id"], "rejeitar"), json={"motivo": "x"}).status_code in (409, 422)
    assert _sessao(db_session, sessao["id"]).status == "ativa"


# ------------------------------------------------------------------------------------------------------------------------------------------------
# E. agregação
# ------------------------------------------------------------------------------------------------------------------------------------------------


def _sessao_db(db: Session, empresa: Empresa, *, status: str, departamento_id: str, inicio_em: datetime, duracao: int | None = None) -> SessaoTrabalho:
    encerrada = status == "encerrada"
    sessao = SessaoTrabalho(
        id=str(uuid.uuid4()), empresa_id=empresa.id, demanda_id=str(uuid.uuid4()), departamento_id=departamento_id, evento_inicio_id=str(uuid.uuid4()),
        evento_fim_id=str(uuid.uuid4()) if encerrada else None, status=status, inicio_em=inicio_em, fim_em=inicio_em + timedelta(seconds=duracao or 0) if encerrada else None,
        duracao_segundos=duracao if encerrada else None, created_at=inicio_em, updated_at=inicio_em,
    )
    db.add(sessao)
    db.flush()
    return sessao


def test_cancelada_nao_entra_no_realizado_do_departamento(db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    as_of = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    _sessao_db(db_session, empresa, status="encerrada", departamento_id=departamento.id, inicio_em=as_of - timedelta(hours=3), duracao=600)
    _sessao_db(db_session, empresa, status="cancelada", departamento_id=departamento.id, inicio_em=as_of - timedelta(days=30))  # sem duração: antes contava ao vivo
    horas, quantidade = SessaoTrabalhoRepository().horas_departamento(db_session, empresa_id=empresa.id, departamento_id=departamento.id, as_of=as_of)
    assert quantidade == 1 and horas == pytest.approx(600 / 3600)


def test_sessao_encerrada_usa_a_duracao_persistida_e_ativa_usa_o_as_of_unico(db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    as_of = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    _sessao_db(db_session, empresa, status="encerrada", departamento_id=departamento.id, inicio_em=as_of - timedelta(days=2), duracao=1800)
    _sessao_db(db_session, empresa, status="ativa", departamento_id=departamento.id, inicio_em=as_of - timedelta(seconds=100))
    db_session.execute(text("UPDATE sessoes_trabalho SET demanda_id = demanda_id"))  # no-op: nada recalcula a duração das encerradas
    repo = SessaoTrabalhoRepository()
    h1 = repo.horas_departamento(db_session, empresa_id=empresa.id, departamento_id=departamento.id, as_of=as_of)
    h2 = repo.horas_departamento(db_session, empresa_id=empresa.id, departamento_id=departamento.id, as_of=as_of)
    assert h1 == h2 and h1[1] == 2 and h1[0] == pytest.approx((1800 + 100) / 3600)  # exato, independente do relógio da máquina
    # adiantando o as_of, SÓ a ativa cresce — a encerrada continua com a duração persistida
    adiante = repo.horas_departamento(db_session, empresa_id=empresa.id, departamento_id=departamento.id, as_of=as_of + timedelta(seconds=50))
    assert adiante[0] == pytest.approx((1800 + 150) / 3600)


def test_endpoint_de_horas_usa_um_instante_e_ignora_cancelada(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    departamento = _departamento(db_session, empresa)
    agora = datetime.now(timezone.utc)
    _sessao_db(db_session, empresa, status="encerrada", departamento_id=departamento.id, inicio_em=agora - timedelta(hours=2), duracao=3600)
    _sessao_db(db_session, empresa, status="cancelada", departamento_id=departamento.id, inicio_em=agora - timedelta(days=9))
    resposta = client_admin.get("/sessoes-trabalho/horas", params={"departamentoId": departamento.id})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["sessoesConsideradas"] == 1 and corpo["horasConsumidas"] == pytest.approx(1.0)


def test_encerrada_validas_somam_no_departamento_uma_vez_por_sessao(db_session: Session, empresa: Empresa) -> None:
    """Sessão de pessoa lotada no departamento + sessão departamental direta: cada uma conta UMA vez (OR no predicado, sem junção multiplicadora)."""
    departamento = _departamento(db_session, empresa)
    pessoa = _usuario(db_session, empresa)
    db_session.execute(text("UPDATE usuarios SET departamento_id = :d WHERE id = :u"), {"d": departamento.id, "u": pessoa.id})
    as_of = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    ini = as_of - timedelta(hours=5)
    de_pessoa = _sessao_db(db_session, empresa, status="encerrada", departamento_id=departamento.id, inicio_em=ini, duracao=60)
    de_pessoa.usuario_id = pessoa.id  # pertinente pelas DUAS regras ao mesmo tempo (lotação E vínculo direto)
    db_session.flush()
    _sessao_db(db_session, empresa, status="encerrada", departamento_id=departamento.id, inicio_em=ini, duracao=120)
    horas, quantidade = SessaoTrabalhoRepository().horas_departamento(db_session, empresa_id=empresa.id, departamento_id=departamento.id, as_of=as_of)
    assert quantidade == 2 and horas == pytest.approx(180 / 3600)


def test_migration_deixa_o_indice_unico_parcial_no_schema(db_session: Session) -> None:
    linha = db_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_sessoes_trabalho_ativa_empresa_usuario'")
    ).scalar_one_or_none()
    assert linha is not None and "UNIQUE" in linha and "(empresa_id, usuario_id)" in linha and "status" in linha and "usuario_id IS NOT NULL" in linha
    assert db_session.scalar(select(func.count()).select_from(SessaoTrabalho)) is not None
