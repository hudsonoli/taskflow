"""Fase Expediente 3 — o TICK: pausa automática no fim dos períodos, com relógio injetado e banco real.

Exemplo oficial: 09–12 / 13–18 (seg–sex). Segunda-feira 2026-10-05, fuso America/Sao_Paulo. A pausa NÃO faz logout, NÃO retoma e NÃO mexe em sessão de isento.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.expediente import chave_de_execucao, correlation_id_da_execucao
from app.models.demanda import Demanda
from app.models.evento import Evento
from app.models.regra_expediente import RegraExpediente as RegraModel
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.services.expediente_pausa_service import ExpedientePausaService
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_demanda import _criar
from tests.test_expediente_fase2_api import _configurar

SP = ZoneInfo("America/Sao_Paulo")
SEGUNDA = date(2026, 10, 5)


def _em(hhmm: str, segundos: int = 0, dia: date = SEGUNDA) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(dia.year, dia.month, dia.day, h, m, segundos, tzinfo=SP)


@pytest.fixture()
def relogio(monkeypatch):
    def fixar(hhmm: str, segundos: int = 0, dia: date = SEGUNDA) -> None:
        instante = _em(hhmm, segundos, dia).astimezone(timezone.utc)
        for modulo in ("app.core.expediente", "app.services.regra_expediente_service", "app.services.expediente_pausa_service"):
            monkeypatch.setattr(f"{modulo}.agora_utc", lambda instante=instante: instante)

    fixar("10:30")
    return fixar


@pytest.fixture()
def cenario(client_admin: TestClient, db_session: Session, empresa, relogio):
    """Pausa automática LIGADA e armada às 08:00 de segunda; relógio em 10:30."""
    _configurar(client_admin, pausarNoFimPeriodo=True)
    regra = db_session.scalar(select(RegraModel).where(RegraModel.empresa_id == empresa.id))
    regra.pausa_automatica_ativada_em = _em("08:00")
    db_session.commit()
    return regra


def _executar(db: Session, empresa, hora: str, segundos: int = 0, relogio=None):
    if relogio:
        relogio(hora, segundos)
    db.commit()
    return ExpedientePausaService().processar_empresa(db, empresa.id)


def _demanda_em_execucao(client_admin: TestClient, **extra) -> str:
    return _criar(client_admin, status="em_execucao", **extra)["id"]


def _abrir_sessao(client_admin: TestClient, db: Session, demanda_id: str, usuario_id: str, inicio: datetime | None = None) -> str:
    """Abre pela API real e FIXA o início no relógio injetado (a rota grava o instante real da máquina; os cortes dos testes vivem em 2026-10-05)."""
    resposta = client_admin.post("/sessoes-trabalho/abrir", json={"demandaId": demanda_id, "usuarioId": usuario_id})
    assert resposta.status_code == 201, resposta.text
    sessao = db.get(SessaoTrabalho, resposta.json()["id"])
    sessao.inicio_em = (inicio or _em("10:30")).astimezone(timezone.utc)
    db.commit()
    return sessao.id


def _demanda(db: Session, demanda_id: str) -> Demanda:
    db.expire_all()
    return db.get(Demanda, demanda_id)


def _sessao(db: Session, sessao_id: str) -> SessaoTrabalho:
    db.expire_all()
    return db.get(SessaoTrabalho, sessao_id)


def _eventos(db: Session, tipo: str, **filtros) -> list[Evento]:
    db.expire_all()
    consulta = select(Evento).where(Evento.tipo == tipo)
    for campo, valor in filtros.items():
        consulta = consulta.where(getattr(Evento, campo) == valor)
    return list(db.scalars(consulta.order_by(Evento.created_at)).all())


STATUS = "demanda.status_alterado"
RESUMO = "expediente.pausa_automatica_aplicada"
MARCA = "expediente.pausa_automatica_executada"


def _status_automaticos(db: Session, demanda_id: str) -> list[Evento]:
    return [e for e in _eventos(db, STATUS, entidade_id=demanda_id) if (e.payload or {}).get("origem") == "expediente"]


# ── flag OFF / sem corte / sem demandas ──────────────────────────────────────────────────────────────────────────


def test_flag_desligada_nao_faz_nada(client_admin, db_session, empresa, relogio) -> None:
    _configurar(client_admin)  # pausarNoFimPeriodo nasce false
    demanda_id = _demanda_em_execucao(client_admin)
    resultado = _executar(db_session, empresa, "12:00", 30, relogio)
    assert resultado.status == "sem_corte"
    assert _demanda(db_session, demanda_id).status == "em_execucao"
    assert ExpedientePausaService().executar_tick(lambda: Session(bind=db_session.get_bind(), join_transaction_mode="create_savepoint"), None) == []


def test_sem_demandas_registra_a_conclusao_mas_nao_avisa_ninguem(cenario, client_admin, db_session, empresa, relogio) -> None:
    resultado = _executar(db_session, empresa, "12:00", 5, relogio)
    assert resultado.status == "executado" and resultado.demandas_pausadas == [] and resultado.avisos == {}
    assert len(_eventos(db_session, MARCA)) == 1
    assert _eventos(db_session, RESUMO) == []  # 0 pausadas: nenhum resumo (nenhum aviso)


@pytest.mark.parametrize("hora, segundos, executa", [("11:59", 59, False), ("12:00", 0, True), ("12:00", 30, True), ("12:01", 0, True), ("12:30", 0, True), ("12:59", 0, True), ("13:00", 0, False)])
def test_matriz_do_tick_no_banco(hora, segundos, executa, cenario, client_admin, db_session, empresa, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    resultado = _executar(db_session, empresa, hora, segundos, relogio)
    assert (resultado.status == "executado") is executa
    assert (_demanda(db_session, demanda_id).status == "pausada") is executa


# ── uma Demanda, sem sessão ──────────────────────────────────────────────────────────────────────────────────────


def test_demanda_sem_sessao_e_pausada_no_instante_do_corte(cenario, client_admin, db_session, empresa, usuario_operador, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin, usuarioResponsavelIds=[usuario_operador.id])
    resultado = _executar(db_session, empresa, "12:00", 42, relogio)  # o tick rodou 42 s depois
    demanda = _demanda(db_session, demanda_id)
    assert resultado.demandas_pausadas == [demanda_id]
    assert demanda.status == "pausada" and demanda.pausa_origem == "expediente"
    assert demanda.pausada_em == _em("12:00")  # o CORTE, não 12:00:42
    # evento de status: sem usuário ator, com origem e correlation_id da execução
    [evento] = _status_automaticos(db_session, demanda_id)
    chave = chave_de_execucao(empresa.id, _em("12:00"))
    assert evento.usuario_id is None
    assert evento.correlation_id == correlation_id_da_execucao(chave)
    assert evento.occurred_at == _em("12:00").astimezone(timezone.utc)
    assert evento.payload["de"] == "em_execucao" and evento.payload["para"] == "pausada" and evento.payload["pausaOrigem"] == "expediente"
    assert evento.payload["automatico"] is True and evento.payload["chaveExecucao"] == chave
    assert evento.metadata_ == {"origem": "sistema", "fonte": "expediente"}


def test_a_pausa_manual_continua_manual(cenario, client_admin, db_session, empresa, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    assert client_admin.patch(f"/demandas/{demanda_id}", json={"status": "pausada"}).json()["pausaOrigem"] == "manual"
    _executar(db_session, empresa, "12:00", 1, relogio)
    demanda = _demanda(db_session, demanda_id)
    assert demanda.status == "pausada" and demanda.pausa_origem == "manual"  # o tick só toca em `em_execucao`
    assert _status_automaticos(db_session, demanda_id) == []


def test_nao_retoma_no_periodo_seguinte(cenario, client_admin, db_session, empresa, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    _executar(db_session, empresa, "12:00", 1, relogio)
    for hora in ("13:00", "13:01", "17:59"):
        assert _executar(db_session, empresa, hora, 0, relogio).status == "sem_corte"
        assert _demanda(db_session, demanda_id).status == "pausada"
    assert _demanda(db_session, demanda_id).pausa_origem == "expediente"


# ── sessões: sujeitos × isentos ──────────────────────────────────────────────────────────────────────────────────


def test_sessao_do_operador_e_encerrada_no_corte_com_motivo_proprio(cenario, client_admin, db_session, empresa, usuario_operador, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    sessao_id = _abrir_sessao(client_admin, db_session, demanda_id, usuario_operador.id)
    inicio = _sessao(db_session, sessao_id).inicio_em
    _executar(db_session, empresa, "12:00", 40, relogio)
    sessao = _sessao(db_session, sessao_id)
    assert sessao.status == "encerrada" and sessao.motivo_encerramento == "fim_expediente"
    assert sessao.fim_em == _em("12:00").astimezone(timezone.utc)
    assert sessao.duracao_segundos == int((_em("12:00").astimezone(timezone.utc) - inicio).total_seconds()) >= 0
    [fim] = [e for e in _eventos(db_session, "sessao_trabalho_encerrada", entidade_id=demanda_id)]
    assert fim.usuario_id is None and fim.payload["automatico"] is True and fim.payload["origem"] == "expediente"
    assert fim.payload["motivoEncerramento"] == "fim_expediente" and fim.payload["sessaoUsuarioId"] == usuario_operador.id
    assert fim.correlation_id == correlation_id_da_execucao(chave_de_execucao(empresa.id, _em("12:00")))
    assert _demanda(db_session, demanda_id).status == "pausada"


def test_isento_com_sessao_ativa_segura_a_demanda_em_execucao(cenario, client_admin, db_session, empresa, usuario_gestor, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin, usuarioResponsavelIds=[usuario_gestor.id])
    sessao_id = _abrir_sessao(client_admin, db_session, demanda_id, usuario_gestor.id)
    resultado = _executar(db_session, empresa, "12:00", 5, relogio)
    assert resultado.demandas_preservadas == [demanda_id] and resultado.demandas_pausadas == []
    assert _demanda(db_session, demanda_id).status == "em_execucao"
    assert _sessao(db_session, sessao_id).status == "ativa"  # a sessão do isento é preservada
    assert _status_automaticos(db_session, demanda_id) == [] and _eventos(db_session, RESUMO) == []


def test_operador_e_gestor_na_mesma_demanda(cenario, client_admin, db_session, empresa, usuario_operador, usuario_gestor, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin, usuarioResponsavelIds=[usuario_operador.id, usuario_gestor.id])
    sessao_operador = _abrir_sessao(client_admin, db_session, demanda_id, usuario_operador.id)
    sessao_gestor = _abrir_sessao(client_admin, db_session, demanda_id, usuario_gestor.id)
    _executar(db_session, empresa, "12:00", 5, relogio)
    assert _sessao(db_session, sessao_operador).status == "encerrada"  # a do operador acaba
    assert _sessao(db_session, sessao_gestor).status == "ativa"  # a do gestor continua
    assert _demanda(db_session, demanda_id).status == "em_execucao"
    # o aviso fala de TAREFA pausada: o operador (sessão fechada, tarefa ainda em execução) NÃO recebe resumo
    assert _eventos(db_session, RESUMO) == []


def test_gestor_responsavel_sem_sessao_nao_segura_a_demanda(cenario, client_admin, db_session, empresa, usuario_gestor, relogio) -> None:
    """Não se infere atividade só porque o gestor é responsável: é preciso uma sessão pessoal ATIVA do isento."""
    demanda_id = _demanda_em_execucao(client_admin, usuarioResponsavelIds=[usuario_gestor.id])
    _executar(db_session, empresa, "12:00", 5, relogio)
    assert _demanda(db_session, demanda_id).status == "pausada"
    [resumo] = _eventos(db_session, RESUMO)
    assert resumo.entidade_id == usuario_gestor.id  # responsável atual de uma tarefa realmente pausada


def test_operador_liberado_e_tratado_como_isento(cenario, client_admin, db_session, empresa, usuario_operador, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    sessao_id = _abrir_sessao(client_admin, db_session, demanda_id, usuario_operador.id)
    usuario_operador.acesso_fora_expediente = True
    db_session.commit()
    _executar(db_session, empresa, "12:00", 5, relogio)
    assert _sessao(db_session, sessao_id).status == "ativa" and _demanda(db_session, demanda_id).status == "em_execucao"


def test_sessao_de_isento_inativo_nao_segura_e_e_encerrada_junto(cenario, client_admin, db_session, empresa, usuario_gestor, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    sessao_id = _abrir_sessao(client_admin, db_session, demanda_id, usuario_gestor.id)
    usuario_gestor.status = "inativo"
    db_session.commit()
    _executar(db_session, empresa, "12:00", 5, relogio)
    assert _demanda(db_session, demanda_id).status == "pausada"
    assert _sessao(db_session, sessao_id).status == "encerrada"  # nunca "sessão ativa + Demanda pausada"


def test_varias_demandas_e_pessoas(cenario, client_admin, db_session, empresa, usuario_operador, usuario_gestor, relogio) -> None:
    outro = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="op2")
    a = _demanda_em_execucao(client_admin, usuarioResponsavelIds=[usuario_operador.id])
    b = _demanda_em_execucao(client_admin, usuarioResponsavelIds=[outro.id])
    c = _demanda_em_execucao(client_admin, usuarioResponsavelIds=[usuario_gestor.id])
    _abrir_sessao(client_admin, db_session, a, usuario_operador.id)
    _abrir_sessao(client_admin, db_session, c, usuario_gestor.id)  # c fica em execução (isento ativo)
    resultado = _executar(db_session, empresa, "12:00", 5, relogio)
    assert sorted(resultado.demandas_pausadas) == sorted([a, b]) and resultado.demandas_preservadas == [c]
    assert _demanda(db_session, c).status == "em_execucao"
    resumos = {e.entidade_id: e.payload["quantidade"] for e in _eventos(db_session, RESUMO)}
    assert resumos == {usuario_operador.id: 1, outro.id: 1}  # só quem tem tarefa realmente pausada; nada global
    assert len(_status_automaticos(db_session, a)) == 1 and len(_status_automaticos(db_session, b)) == 1


def test_demanda_de_outra_empresa_nunca_e_tocada(cenario, client_admin, db_session, empresa, outra_empresa, relogio) -> None:
    admin_b = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="adminb")
    db_session.commit()
    from tests.test_sessao_trabalho_integridade import client_do_  # type: ignore

    demanda_b = _criar(client_do_(admin_b, db_session), status="em_execucao")["id"]
    _executar(db_session, empresa, "12:00", 5, relogio)
    assert _demanda(db_session, demanda_b).status == "em_execucao"


# ── resumo / feedback ────────────────────────────────────────────────────────────────────────────────────────────


def test_estado_devolve_a_ultima_pausa_automatica_so_para_quem_foi_afetado(cenario, client_admin, client_operador, db_session, empresa, usuario_operador, relogio) -> None:
    _demanda_em_execucao(client_admin, usuarioResponsavelIds=[usuario_operador.id])
    antes = client_operador.get("/expediente/estado").json()
    assert antes["ultimaPausaAutomatica"] is None
    _executar(db_session, empresa, "12:00", 5, relogio)
    estado = client_operador.get("/expediente/estado").json()
    ultima = estado["ultimaPausaAutomatica"]
    assert ultima["quantidade"] == 1 and datetime.fromisoformat(ultima["em"]) == _em("12:00")
    [resumo] = _eventos(db_session, RESUMO)
    assert ultima["eventoId"] == resumo.id
    assert resumo.payload["quantidade"] == 1 and resumo.usuario_id is None
    # quem não foi afetado não vê nada
    assert client_admin.get("/expediente/estado").json()["ultimaPausaAutomatica"] is None


def test_o_resumo_so_existe_com_quantidade_maior_que_zero(cenario, client_admin, db_session, empresa, usuario_operador, relogio) -> None:
    _executar(db_session, empresa, "12:00", 5, relogio)  # nada em execução
    assert _eventos(db_session, RESUMO) == []
    _executar(db_session, empresa, "18:00", 5, relogio)
    assert _eventos(db_session, RESUMO) == []


# ── idempotência, lock, restart ──────────────────────────────────────────────────────────────────────────────────


def test_retry_nao_repete_pausa_fechamento_evento_nem_aviso(cenario, client_admin, db_session, empresa, usuario_operador, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin, usuarioResponsavelIds=[usuario_operador.id])
    _abrir_sessao(client_admin, db_session, demanda_id, usuario_operador.id)
    primeiro = _executar(db_session, empresa, "12:00", 5, relogio)
    contagem = lambda: (  # noqa: E731
        len(_status_automaticos(db_session, demanda_id)),
        len(_eventos(db_session, "sessao_trabalho_encerrada", entidade_id=demanda_id)),
        len(_eventos(db_session, RESUMO)),
        len(_eventos(db_session, MARCA)),
    )
    assert primeiro.status == "executado" and contagem() == (1, 1, 1, 1)
    for hora, seg in (("12:00", 20), ("12:01", 0), ("12:30", 0)):
        assert _executar(db_session, empresa, hora, seg, relogio).status == "ja_executado"
    assert contagem() == (1, 1, 1, 1)


def test_corte_ja_concluido_nao_repausa_o_que_um_isento_reabriu(cenario, client_admin, db_session, empresa, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    _executar(db_session, empresa, "12:00", 5, relogio)
    assert client_admin.patch(f"/demandas/{demanda_id}", json={"status": "em_execucao"}).status_code == 200  # admin (isento) reabre depois do corte
    _executar(db_session, empresa, "12:30", 0, relogio)  # novo tick dentro da janela de catch-up: o registro de conclusão impede repetir
    assert _demanda(db_session, demanda_id).status == "em_execucao"


def test_advisory_lock_ocupado_por_outra_instancia_adia_o_corte(cenario, client_admin, db_session, empresa, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    chave = chave_de_execucao(empresa.id, _em("12:00"))
    db_session.commit()
    outra = db_session.get_bind().engine.connect() if hasattr(db_session.get_bind(), "engine") else None
    assert outra is not None
    outra.execute(text("SELECT pg_advisory_lock(hashtextextended(:c, 0))"), {"c": chave})  # "outra instância" segurando o MESMO corte
    try:
        # o Session de teste usa a MESMA conexão do lock? Não: `outra` é uma conexão distinta → o try-lock da sessão de teste falha
        resultado = _executar(db_session, empresa, "12:00", 5, relogio)
        assert resultado.status == "lock_ocupado"
        assert _demanda(db_session, demanda_id).status == "em_execucao" and _eventos(db_session, MARCA) == []
    finally:
        outra.execute(text("SELECT pg_advisory_unlock(hashtextextended(:c, 0))"), {"c": chave})
        outra.close()
    assert _executar(db_session, empresa, "12:00", 10, relogio).status == "executado"  # liberado: o próximo tick executa
    assert _demanda(db_session, demanda_id).status == "pausada"


def test_lock_de_outro_corte_nao_atrapalha(cenario, client_admin, db_session, empresa, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    db_session.commit()
    outra = db_session.get_bind().engine.connect()
    outra.execute(text("SELECT pg_advisory_lock(hashtextextended(:c, 0))"), {"c": chave_de_execucao(empresa.id, _em("18:00"))})
    try:
        assert _executar(db_session, empresa, "12:00", 5, relogio).status == "executado"
    finally:
        outra.execute(text("SELECT pg_advisory_unlock(hashtextextended(:c, 0))"), {"c": chave_de_execucao(empresa.id, _em("18:00"))})
        outra.close()
    assert _demanda(db_session, demanda_id).status == "pausada"


def test_restart_no_intervalo_ainda_processa_e_depois_do_proximo_periodo_nao(cenario, client_admin, db_session, empresa, relogio, caplog) -> None:
    a = _demanda_em_execucao(client_admin)
    with caplog.at_level(logging.WARNING):
        assert _executar(db_session, empresa, "12:20", 0, relogio).status == "executado"  # restart às 12:20 → processa o corte das 12:00
    assert _demanda(db_session, a).pausada_em == _em("12:00")  # o corte, não 12:20
    assert any("expediente_corte_perdido_processado_em_catch_up" in r.getMessage() for r in caplog.records)  # observabilidade
    # novo dia: demanda iniciada às 13:05 por um isento; restart às 13:10 NÃO retro-pausa as 12:00 (novo período já começou)
    relogio("13:05")
    b = _demanda_em_execucao(client_admin)
    assert _executar(db_session, empresa, "13:10", 0, relogio).status == "sem_corte"
    assert _demanda(db_session, b).status == "em_execucao"


def test_corte_das_18h_com_restart_as_1830(cenario, client_admin, db_session, empresa, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    assert _executar(db_session, empresa, "18:30", 0, relogio).status == "executado"
    assert _demanda(db_session, demanda_id).pausada_em == _em("18:00")


def test_ligar_a_flag_as_1215_nao_pausa_o_corte_das_1200_e_o_das_18h_vale(client_admin, db_session, empresa, relogio) -> None:
    _configurar(client_admin)  # flag desligada
    demanda_id = _demanda_em_execucao(client_admin)
    relogio("12:15")
    assert client_admin.patch("/regra-expediente", json={"pausarNoFimPeriodo": True}).status_code == 200
    regra = db_session.scalar(select(RegraModel).where(RegraModel.empresa_id == empresa.id))
    assert regra.pausa_automatica_ativada_em == _em("12:15")  # a armadura é um instante confiável PERSISTIDO (nada de memória de processo)
    assert _executar(db_session, empresa, "12:20", 0, relogio).status == "sem_corte"
    assert _demanda(db_session, demanda_id).status == "em_execucao"
    assert _executar(db_session, empresa, "18:00", 5, relogio).status == "executado"
    assert _demanda(db_session, demanda_id).status == "pausada"
    # desligar limpa; religar rearma
    assert client_admin.patch("/regra-expediente", json={"pausarNoFimPeriodo": False}).status_code == 200
    db_session.expire_all()
    assert db_session.scalar(select(RegraModel.pausa_automatica_ativada_em).where(RegraModel.empresa_id == empresa.id)) is None


def test_editar_o_calendario_com_a_pausa_ligada_rearma(cenario, client_admin, db_session, empresa, relogio) -> None:
    relogio("12:40")
    assert client_admin.post("/regra-expediente/dias-especiais", json={"data": SEGUNDA.isoformat(), "nome": "Recesso", "tipo": "recesso"}).status_code == 201
    regra = db_session.scalar(select(RegraModel).where(RegraModel.empresa_id == empresa.id))
    db_session.refresh(regra)
    assert regra.pausa_automatica_ativada_em == _em("12:40")


def test_feriado_nao_tem_corte(cenario, client_admin, db_session, empresa, relogio) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    assert client_admin.post("/regra-expediente/dias-especiais", json={"data": SEGUNDA.isoformat(), "nome": "Feriado", "tipo": "feriado"}).status_code == 201
    regra = db_session.scalar(select(RegraModel).where(RegraModel.empresa_id == empresa.id))
    regra.pausa_automatica_ativada_em = _em("08:00")
    db_session.commit()
    resultado = _executar(db_session, empresa, "12:05", 0, relogio)
    assert resultado.status in ("sem_corte",) and _demanda(db_session, demanda_id).status == "em_execucao"


# ── defesa contra duração negativa ───────────────────────────────────────────────────────────────────────────────


def test_sessao_iniciada_depois_do_corte_nunca_tem_fim_antes_do_inicio(cenario, client_admin, db_session, empresa, usuario_operador, relogio, caplog) -> None:
    demanda_id = _demanda_em_execucao(client_admin)
    sessao_id = _abrir_sessao(client_admin, db_session, demanda_id, usuario_operador.id)
    sessao = _sessao(db_session, sessao_id)
    sessao.inicio_em = _em("12:10").astimezone(timezone.utc)  # estado "impossível": começou DEPOIS do corte das 12:00
    db_session.commit()
    with caplog.at_level(logging.WARNING):
        _executar(db_session, empresa, "12:20", 0, relogio)
    sessao = _sessao(db_session, sessao_id)
    assert sessao.status == "encerrada" and sessao.fim_em >= sessao.inicio_em and sessao.duracao_segundos == 0
    assert any("sessao_trabalho_fim_anterior_ao_inicio" in r.getMessage() for r in caplog.records)


# ── atomicidade por Demanda ──────────────────────────────────────────────────────────────────────────────────────


def test_demanda_que_falha_nao_impede_as_outras_nem_marca_o_corte_como_concluido(cenario, client_admin, db_session, empresa, monkeypatch, relogio) -> None:
    ok = _demanda_em_execucao(client_admin)
    ruim = _demanda_em_execucao(client_admin)
    servico = ExpedientePausaService()
    original = servico._processar_demanda

    def com_falha(db, demanda, *a, **k):
        if demanda.id == ruim:
            raise RuntimeError("falha simulada")
        return original(db, demanda, *a, **k)

    monkeypatch.setattr(servico, "_processar_demanda", com_falha)
    relogio("12:00", 5)
    db_session.commit()
    resultado = servico.processar_empresa(db_session, empresa.id)
    assert resultado.status == "parcial" and resultado.falhas == 1
    assert _demanda(db_session, ok).status == "pausada"
    assert _demanda(db_session, ruim).status == "em_execucao" and _status_automaticos(db_session, ruim) == []  # o savepoint desfez tudo da demanda que falhou
    assert _eventos(db_session, MARCA) == []  # não concluído: a próxima rodada refaz só o que faltou
    monkeypatch.setattr(servico, "_processar_demanda", original)
    segunda = servico.processar_empresa(db_session, empresa.id)
    assert segunda.status == "executado" and segunda.demandas_pausadas == [ruim]
    assert len(_status_automaticos(db_session, ok)) == 1  # a que já tinha sido pausada não duplica


# ── sem logout ───────────────────────────────────────────────────────────────────────────────────────────────────


def test_a_pausa_nao_faz_logout_nem_invalida_tokens(cenario, client_admin, client_operador, db_session, empresa, usuario_operador, relogio) -> None:
    _demanda_em_execucao(client_admin, usuarioResponsavelIds=[usuario_operador.id])
    assert client_operador.get("/usuarios/me").status_code == 200
    _executar(db_session, empresa, "12:00", 5, relogio)
    assert client_operador.get("/usuarios/me").status_code == 200  # mesma sessão/token: a pausa é independente do logout automático
    assert client_operador.get("/expediente/estado").status_code == 200


def test_o_tick_de_producao_nao_sobe_na_suite() -> None:
    from app.core.expediente_tick import tick_habilitado

    assert tick_habilitado() is False
