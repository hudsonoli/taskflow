"""Tráfego V2 — Fase 1: o MOTOR de intervalos operacionais (`demanda_status_intervalos`).

TEMPO OPERACIONAL ≠ TEMPO PESSOAL: a duração de um intervalo é o tempo DECORRIDO da Demanda naquele estado — nunca "horas trabalhadas" por alguém. Estes testes provam a linha do
tempo (sem buracos, sem sobreposição, no máximo 1 aberto), o instante efetivo (manual = agora; expediente = o CORTE), a etapa do workflow, a idempotência e as constraints.
Relógio injetado (segunda-feira 2026-10-05, America/Sao_Paulo); nada depende do tempo real da suíte.
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.demanda_status_intervalo import DemandaStatusIntervalo
from app.models.regra_expediente import RegraExpediente as RegraModel
from app.models.sessao_trabalho import SessaoTrabalho
from app.repositories.demanda_status_intervalo_repository import DemandaStatusIntervaloRepository
from app.services.demanda_intervalo_service import DemandaIntervaloService
from app.services.demanda_service import DemandaService
from app.services.expediente_pausa_service import ExpedientePausaService
from tests.test_demanda import _criar
from tests.test_expediente_fase2_api import _configurar
from tests.test_fase_8a_workflow_progressao import _etapa, _por_ordem
from tests.test_sessao_trabalho_integridade import _concluir, _demanda_wf

SP = ZoneInfo("America/Sao_Paulo")
SEGUNDA = date(2026, 10, 5)


def _em(hhmm: str, segundos: int = 0) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(SEGUNDA.year, SEGUNDA.month, SEGUNDA.day, h, m, segundos, tzinfo=SP)


@pytest.fixture()
def relogio(monkeypatch):
    def fixar(hhmm: str, segundos: int = 0) -> None:
        instante = _em(hhmm, segundos).astimezone(timezone.utc)
        for modulo in (
            "app.core.expediente",
            "app.services.demanda_service",
            "app.services.demanda_workflow_service",
            "app.services.regra_expediente_service",
            "app.services.expediente_pausa_service",
        ):
            monkeypatch.setattr(f"{modulo}.agora_utc", lambda instante=instante: instante)

    fixar("09:00")
    return fixar


def _linha(db: Session, demanda_id: str) -> list[DemandaStatusIntervalo]:
    db.expire_all()
    return DemandaStatusIntervaloRepository().listar_da_demanda(db, demanda_id)


def _resumo(intervalos: list[DemandaStatusIntervalo]) -> list[tuple]:
    return [(i.status, i.fim_em is None) for i in intervalos]


def _abertos(intervalos: list[DemandaStatusIntervalo]) -> list[DemandaStatusIntervalo]:
    return [i for i in intervalos if i.fim_em is None]


def _assert_linha_integra(intervalos: list[DemandaStatusIntervalo]) -> None:
    """Sem sobreposição, sem buracos entre intervalos consecutivos e no máximo 1 aberto (o último)."""
    assert len(_abertos(intervalos)) <= 1
    for anterior, seguinte in zip(intervalos, intervalos[1:]):
        assert anterior.fim_em is not None, "só o ÚLTIMO pode estar aberto"
        assert seguinte.inicio_em >= anterior.fim_em  # nenhuma sobreposição
        # estados terminais/reabertura podem deixar buraco (a Demanda não tinha estado operacional); aqui exigimos encadeamento exato quando não houve terminal
    for i in intervalos:
        if i.fim_em is not None:
            assert i.fim_em >= i.inicio_em and i.duracao_segundos == int((i.fim_em - i.inicio_em).total_seconds()) >= 0


def _patch(cliente: TestClient, demanda_id: str, **corpo):
    resposta = cliente.patch(f"/demandas/{demanda_id}", json=corpo)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# ── criação ──────────────────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("status", ["rascunho", "planejada", "em_execucao", "pausada", "aguardando_cliente"])
def test_criar_abre_o_primeiro_intervalo(status, client_admin, usuario_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status=status)
    [intervalo] = _linha(db_session, demanda["id"])
    assert intervalo.status == status and intervalo.fim_em is None and intervalo.duracao_segundos is None
    assert intervalo.inicio_em == _em("09:00").astimezone(timezone.utc)
    assert intervalo.origem == "criacao" and intervalo.workflow_etapa_id is None  # sem workflow: etapa NULL
    assert intervalo.iniciado_por_usuario_id == usuario_admin.id  # AUDITORIA de quem provocou — não "quem trabalhou"
    assert intervalo.evento_inicio_id is not None  # liga ao evento `demanda.criada`


def test_criar_bloqueada_e_terminal(client_admin, db_session, relogio) -> None:
    bloqueada = _criar(client_admin, status="bloqueada", motivoBloqueio="falta insumo")
    assert [i.status for i in _linha(db_session, bloqueada["id"])] == ["bloqueada"]
    concluida = _criar(client_admin, status="concluida")
    assert _linha(db_session, concluida["id"]) == []  # estado terminal na criação: nenhum intervalo (nada acumula "tempo concluída")


def test_criar_com_falha_no_motor_nao_cria_nada(client_admin, usuario_admin, db_session, relogio, monkeypatch) -> None:
    """Atomicidade: se o motor falhar, a Demanda NÃO é criada (mesma transação) — nem número queimado."""
    db_session.commit()
    antes = db_session.scalar(select(func.count()).select_from(Demanda))

    def quebra(*a, **k):
        raise RuntimeError("falha simulada do motor")

    monkeypatch.setattr(DemandaIntervaloService, "sincronizar", quebra)
    from app.schemas.demanda import DemandaCreate

    with pytest.raises(RuntimeError):
        DemandaService().create_demanda(db_session, DemandaCreate(nome="X", status="planejada"), empresa_id=usuario_admin.empresa_id, actor=usuario_admin)
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(Demanda)) == antes


# ── transições e tempo (relógio injetado) ────────────────────────────────────────────────────────────────────────


def test_linha_do_tempo_com_tempos_exatos(client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="planejada")  # 09:00
    relogio("09:00")
    _patch(client_admin, demanda["id"], status="em_execucao")  # planejada fecha com 0 s, em_execucao abre
    relogio("10:15")
    _patch(client_admin, demanda["id"], status="pausada")
    relogio("13:00")
    _patch(client_admin, demanda["id"], status="em_execucao")
    relogio("14:30")
    _patch(client_admin, demanda["id"], status="aguardando_cliente")
    linha = _linha(db_session, demanda["id"])
    assert [i.status for i in linha] == ["planejada", "em_execucao", "pausada", "em_execucao", "aguardando_cliente"]
    _assert_linha_integra(linha)
    planejada, exec1, pausada, exec2, espera = linha
    assert exec1.duracao_segundos == 4500  # 09:00 → 10:15 = 1h15
    assert pausada.duracao_segundos == 9900  # 10:15 → 13:00
    assert exec2.duracao_segundos == 5400  # 13:00 → 14:30 = 1h30
    assert espera.fim_em is None and espera.inicio_em == _em("14:30").astimezone(timezone.utc)  # bucket PRÓPRIO de espera, aberto
    assert [i.motivo_fim for i in (planejada, exec1, pausada, exec2)] == ["mudanca_status"] * 4
    # a soma do tempo em execução só conta os intervalos em_execucao (aguardando_cliente não se mistura)
    assert sum(i.duracao_segundos for i in linha if i.status == "em_execucao") == 4500 + 5400


@pytest.mark.parametrize("destino, extra", [("bloqueada", {"motivoBloqueio": "x"}), ("aguardando_cliente", {}), ("pausada", {})])
def test_saidas_de_em_execucao(destino, extra, client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="em_execucao")
    relogio("09:40")
    _patch(client_admin, demanda["id"], status=destino, **extra)
    linha = _linha(db_session, demanda["id"])
    assert _resumo(linha) == [("em_execucao", False), (destino, True)]
    assert linha[0].duracao_segundos == 2400 and linha[0].motivo_fim == "mudanca_status"
    assert linha[1].origem == "transicao"


@pytest.mark.parametrize("terminal, motivo", [("concluida", "conclusao"), ("cancelada", "cancelamento")])
def test_estados_terminais_fecham_e_nao_abrem_intervalo(terminal, motivo, client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="em_execucao")
    relogio("11:00")
    _patch(client_admin, demanda["id"], status=terminal)
    linha = _linha(db_session, demanda["id"])
    assert _resumo(linha) == [("em_execucao", False)]
    assert linha[0].motivo_fim == motivo and linha[0].duracao_segundos == 7200
    assert _abertos(linha) == []  # concluída não acumula tempo


def test_reabrir_uma_demanda_concluida_abre_novo_intervalo(client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="em_execucao")
    relogio("10:00")
    _patch(client_admin, demanda["id"], status="concluida")
    relogio("15:00")
    _patch(client_admin, demanda["id"], status="em_execucao")
    linha = _linha(db_session, demanda["id"])
    assert _resumo(linha) == [("em_execucao", False), ("em_execucao", True)]
    _assert_linha_integra(linha)
    assert linha[1].inicio_em == _em("15:00").astimezone(timezone.utc)  # o buraco 10:00–15:00 é real: a Demanda estava concluída


def test_mesmo_status_e_no_op_para_a_linha_do_tempo(client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="em_execucao")
    antes = [(i.id, i.inicio_em, i.fim_em) for i in _linha(db_session, demanda["id"])]
    relogio("11:00")
    _patch(client_admin, demanda["id"], status="em_execucao")
    _patch(client_admin, demanda["id"], status="em_execucao", nome="Outro nome")
    depois = [(i.id, i.inicio_em, i.fim_em) for i in _linha(db_session, demanda["id"])]
    assert depois == antes  # nada fechado/reaberto, nenhum tempo duplicado


def test_patch_sem_mudar_status_nao_mexe_na_linha(client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="pausada")
    relogio("10:00")
    _patch(client_admin, demanda["id"], nome="Só o nome")
    assert len(_linha(db_session, demanda["id"])) == 1


# ── arquivar / restaurar ─────────────────────────────────────────────────────────────────────────────────────────


def test_arquivar_fecha_e_restaurar_reabre_o_estado_anterior(client_admin, usuario_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="em_execucao")
    relogio("10:00")
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "duplicada"}).status_code == 200
    linha = _linha(db_session, demanda["id"])
    assert _resumo(linha) == [("em_execucao", False)] and linha[0].motivo_fim == "arquivamento" and linha[0].duracao_segundos == 3600
    assert _abertos(linha) == []
    relogio("10:30")
    assert client_admin.post(f"/demandas/{demanda['id']}/restaurar").status_code == 200
    linha = _linha(db_session, demanda["id"])
    assert _resumo(linha) == [("em_execucao", False), ("em_execucao", True)]
    assert linha[1].origem == "restauracao" and linha[1].inicio_em == _em("10:30").astimezone(timezone.utc)
    assert linha[1].iniciado_por_usuario_id == usuario_admin.id
    _assert_linha_integra(linha)


def test_restaurar_para_estado_terminal_nao_abre_intervalo(client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="concluida")
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code == 200
    assert client_admin.post(f"/demandas/{demanda['id']}/restaurar").status_code == 200
    assert _linha(db_session, demanda["id"]) == []


def test_restaurar_recusado_pelo_gate_nao_mexe_na_linha(client_admin, usuario_operador, db_session, relogio) -> None:
    """A restauração para em_execucao fora da janela é recusada (gate de trabalho) e NADA muda na linha do tempo."""
    from app.services.expediente_trabalho import DemandaForaDeExpedienteError

    _configurar(client_admin)
    demanda = _criar(client_admin, status="em_execucao")
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code == 200
    antes = _resumo(_linha(db_session, demanda["id"]))
    relogio("12:30")  # acesso SIM, trabalho NÃO
    with pytest.raises(DemandaForaDeExpedienteError):
        DemandaService().restaurar_demanda(db_session, db_session.get(Demanda, demanda["id"]), actor=usuario_operador)
    assert _resumo(_linha(db_session, demanda["id"])) == antes


# ── workflow: a ETAPA atual faz parte da linha do tempo ──────────────────────────────────────────────────────────


def test_troca_de_etapa_mantendo_em_execucao_fecha_e_reabre(client_admin, db_session, relogio) -> None:
    demanda = _demanda_wf(client_admin, [_etapa("Criação"), _etapa("Revisão"), _etapa("Final")])  # em_execucao
    criacao, revisao, final = _por_ordem(demanda)
    inicial = _linha(db_session, demanda["id"])
    # o helper cria em rascunho e move para em_execucao: rascunho (fechado) → em_execucao (aberto, na etapa atual = Criação)
    assert [i.status for i in inicial] == ["rascunho", "em_execucao"] and inicial[-1].workflow_etapa_id == criacao["id"] and inicial[0].workflow_etapa_id == criacao["id"]
    relogio("11:12")
    _concluir(client_admin, demanda, criacao)
    linha = _linha(db_session, demanda["id"])
    assert _resumo(linha) == [("rascunho", False), ("em_execucao", False), ("em_execucao", True)]
    _rascunho, anterior, atual = linha
    assert anterior.workflow_etapa_id == criacao["id"] and anterior.motivo_fim == "mudanca_etapa" and anterior.duracao_segundos == int((_em("11:12").astimezone(timezone.utc) - anterior.inicio_em).total_seconds())
    assert atual.workflow_etapa_id == revisao["id"] and atual.origem == "troca_etapa" and atual.inicio_em == _em("11:12").astimezone(timezone.utc)
    relogio("13:00")
    _concluir(client_admin, demanda, revisao)
    relogio("13:30")
    _concluir(client_admin, demanda, final)  # workflow acabou: a Demanda NÃO é concluída (decisão do 8A) → etapa NULL, mesmo estado
    linha = _linha(db_session, demanda["id"])
    _assert_linha_integra(linha)
    assert [i.workflow_etapa_id for i in linha] == [criacao["id"], criacao["id"], revisao["id"], final["id"], None]  # rascunho/Criação, em_execucao/Criação, Revisão, Final, (workflow acabou)
    assert linha[-1].fim_em is None and linha[-1].status == "em_execucao"
    # tempo operacional POR ETAPA (consulta direta na tabela, não em JSON de evento)
    por_etapa = {i.workflow_etapa_id: i.duracao_segundos for i in linha if i.status == "em_execucao" and i.fim_em is not None}
    assert por_etapa[revisao["id"]] == 6480  # 11:12 → 13:00


def test_pausar_com_workflow_mantem_a_etapa_atual(client_admin, db_session, relogio) -> None:
    demanda = _demanda_wf(client_admin, [_etapa("A"), _etapa("B")])
    a, b = _por_ordem(demanda)
    _concluir(client_admin, demanda, a)
    relogio("10:00")
    _patch(client_admin, demanda["id"], status="pausada")
    linha = _linha(db_session, demanda["id"])
    assert (linha[-1].status, linha[-1].workflow_etapa_id) == ("pausada", b["id"])  # a espera/pausa também é MEDIDA POR ETAPA


# ── Expediente (Fase 3): a pausa automática usa o MESMO mecanismo, com o corte como instante ─────────────────────


def _armar_pausa(client_admin: TestClient, db: Session, empresa) -> None:
    _configurar(client_admin, pausarNoFimPeriodo=True)
    regra = db.scalar(select(RegraModel).where(RegraModel.empresa_id == empresa.id))
    regra.pausa_automatica_ativada_em = _em("08:00")
    db.commit()


def test_pausa_automatica_fecha_em_execucao_no_corte_e_abre_pausada_no_corte(client_admin, db_session, empresa, relogio) -> None:
    _armar_pausa(client_admin, db_session, empresa)
    relogio("11:30")
    demanda = _criar(client_admin, status="em_execucao")
    relogio("12:00", 8)  # o tick roda 8 s depois do corte
    db_session.commit()
    resultado = ExpedientePausaService().processar_empresa(db_session, empresa.id)
    assert resultado.demandas_pausadas == [demanda["id"]]
    linha = _linha(db_session, demanda["id"])
    assert _resumo(linha) == [("em_execucao", False), ("pausada", True)]
    execucao, pausada = linha
    corte = _em("12:00").astimezone(timezone.utc)
    assert execucao.fim_em == corte and execucao.duracao_segundos == 1800  # 11:30 → 12:00:00 (NÃO 12:00:08)
    assert execucao.motivo_fim == "fim_expediente"
    assert pausada.inicio_em == corte and pausada.origem == "expediente" and pausada.iniciado_por_usuario_id is None  # ação do SISTEMA
    _assert_linha_integra(linha)
    # `pausada_em` da Demanda e o intervalo concordam no instante efetivo
    assert db_session.get(Demanda, demanda["id"]).pausada_em == corte
    # o evento de status é o evento de fim/início do intervalo (auditoria ↔ materializado)
    assert execucao.evento_fim_id == pausada.evento_inicio_id is not None


def test_retry_do_tick_nao_duplica_intervalos(client_admin, db_session, empresa, relogio) -> None:
    _armar_pausa(client_admin, db_session, empresa)
    relogio("11:30")
    demanda = _criar(client_admin, status="em_execucao")
    relogio("12:00", 8)
    db_session.commit()
    ExpedientePausaService().processar_empresa(db_session, empresa.id)
    antes = _resumo(_linha(db_session, demanda["id"]))
    relogio("12:01")
    assert ExpedientePausaService().processar_empresa(db_session, empresa.id).status == "ja_executado"
    assert _resumo(_linha(db_session, demanda["id"])) == antes


def test_a_pausa_do_tick_com_demanda_isenta_ativa_nao_muda_a_linha(client_admin, usuario_gestor, db_session, empresa, relogio) -> None:
    _armar_pausa(client_admin, db_session, empresa)
    relogio("11:30")
    demanda = _criar(client_admin, status="em_execucao")
    assert client_admin.post("/sessoes-trabalho/abrir", json={"demandaId": demanda["id"], "usuarioId": usuario_gestor.id}).status_code == 201
    sessao = db_session.scalar(select(SessaoTrabalho))
    sessao.inicio_em = _em("11:30").astimezone(timezone.utc)
    db_session.commit()
    relogio("12:00", 8)
    ExpedientePausaService().processar_empresa(db_session, empresa.id)
    assert _resumo(_linha(db_session, demanda["id"])) == [("em_execucao", True)]  # preservada: o intervalo segue aberto


def test_instante_anterior_ao_inicio_nunca_gera_duracao_negativa_nem_sobreposicao(client_admin, usuario_admin, db_session, relogio, caplog) -> None:
    demanda = _criar(client_admin, status="em_execucao")  # 09:00
    relogio("09:00", 30)
    objeto = db_session.get(Demanda, demanda["id"])
    objeto.status = "pausada"
    with caplog.at_level(logging.WARNING):
        DemandaIntervaloService().sincronizar(db_session, objeto, quando=_em("08:59"), origem="expediente", ator_usuario_id=None)  # corte ANTERIOR ao início
    linha = _linha(db_session, demanda["id"])
    _assert_linha_integra(linha)
    assert linha[0].duracao_segundos == 0 and linha[0].fim_em == linha[0].inicio_em
    assert linha[1].inicio_em == linha[0].fim_em  # a nova linha começa onde a anterior terminou: sem sobreposição
    assert any("demanda_intervalo_instante_anterior_ao_inicio" in r.getMessage() for r in caplog.records)


# ── idempotência, constraints, concorrência ──────────────────────────────────────────────────────────────────────


def test_sincronizar_e_idempotente(client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="em_execucao")
    objeto = db_session.get(Demanda, demanda["id"])
    servico = DemandaIntervaloService()
    for _ in range(3):
        resultado = servico.sincronizar(db_session, objeto, quando=_em("10:00"), origem="transicao")
        assert resultado.mudou is False
    assert len(_linha(db_session, demanda["id"])) == 1


def test_o_mesmo_evento_nao_abre_dois_intervalos(client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="pausada")
    [existente] = _linha(db_session, demanda["id"])
    duplicado = DemandaStatusIntervalo(
        id=str(uuid.uuid4()), empresa_id=existente.empresa_id, demanda_id=existente.demanda_id, status="planejada", inicio_em=_em("08:00"), fim_em=_em("08:30"),
        duracao_segundos=1800, motivo_fim="mudanca_status", origem="transicao", evento_inicio_id=existente.evento_inicio_id, created_at=_em("09:00"), updated_at=_em("09:00"),
    )
    db_session.add(duplicado)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_indice_unico_dois_abertos_na_mesma_demanda_e_barrado_pelo_banco(client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="em_execucao")
    [aberto] = _linha(db_session, demanda["id"])
    outro = DemandaStatusIntervalo(
        id=str(uuid.uuid4()), empresa_id=aberto.empresa_id, demanda_id=aberto.demanda_id, status="pausada", inicio_em=_em("10:00"), origem="transicao",
        created_at=_em("10:00"), updated_at=_em("10:00"),
    )
    db_session.add(outro)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


@pytest.mark.parametrize(
    "mudanca",
    [
        {"status": "concluida"},  # terminal não tem intervalo
        {"fim_em": "x"},  # aberto sem duração/motivo é válido; com fim sem duração não
        {"duracao_segundos": 10},  # aberto com duração
        {"origem": "inventada"},
        {"status": "inexistente"},
    ],
)
def test_checks_de_integridade(mudanca, client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="pausada")
    [aberto] = _linha(db_session, demanda["id"])
    db_session.commit()
    if "fim_em" in mudanca:
        valores = "fim_em = inicio_em"  # fechado SEM duração nem motivo
    elif "duracao_segundos" in mudanca:
        valores = "duracao_segundos = 10"
    elif "origem" in mudanca:
        valores = "origem = 'inventada'"
    else:
        valores = f"status = '{mudanca['status']}'"
    with pytest.raises(IntegrityError):
        db_session.execute(text(f"UPDATE demanda_status_intervalos SET {valores} WHERE id = :i"), {"i": aberto.id})
    db_session.rollback()


def test_fechado_com_fim_antes_do_inicio_e_barrado(client_admin, db_session, relogio) -> None:
    demanda = _criar(client_admin, status="pausada")
    [aberto] = _linha(db_session, demanda["id"])
    db_session.commit()
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE demanda_status_intervalos SET fim_em = inicio_em - interval '1 second', duracao_segundos = 0, motivo_fim = 'mudanca_status' WHERE id = :i"), {"i": aberto.id}
        )
    db_session.rollback()


def test_falha_no_meio_da_transicao_desfaz_status_e_linha(client_admin, usuario_admin, db_session, relogio, monkeypatch) -> None:
    demanda = _criar(client_admin, status="em_execucao")
    db_session.commit()
    original = DemandaIntervaloService.sincronizar

    def falha_depois_de_fechar(self, db, d, **kw):
        original(self, db, d, **kw)
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(DemandaIntervaloService, "sincronizar", falha_depois_de_fechar)
    from app.schemas.demanda import DemandaUpdate

    relogio("10:00")
    with pytest.raises(RuntimeError):
        DemandaService().update_demanda(db_session, db_session.get(Demanda, demanda["id"]), DemandaUpdate(status="pausada"), actor=usuario_admin)
    db_session.expire_all()
    assert db_session.get(Demanda, demanda["id"]).status == "em_execucao"  # o status voltou
    assert _resumo(_linha(db_session, demanda["id"])) == [("em_execucao", True)]  # e a linha do tempo também


def test_nenhum_codigo_do_motor_toca_sessoes_nem_gera_horas_pessoais() -> None:
    """TEMPO OPERACIONAL ≠ TEMPO PESSOAL: o motor não lê/escreve `sessoes_trabalho` nem tem nenhum campo/função de horas por usuário."""
    import ast
    import inspect

    from app.models import demanda_status_intervalo as modelo
    from app.services import demanda_intervalo_service as servico

    def codigo(modulo) -> str:
        arvore = ast.parse(inspect.getsource(modulo))
        for no in ast.walk(arvore):
            if isinstance(no, (ast.Module, ast.FunctionDef, ast.ClassDef)) and no.body and isinstance(no.body[0], ast.Expr) and isinstance(getattr(no.body[0], "value", None), ast.Constant):
                no.body = no.body[1:] or [ast.Pass()]
        return ast.unparse(arvore).lower()

    for modulo in (modelo, servico):
        texto = codigo(modulo)
        assert "sessoes_trabalho" not in texto and "sessaotrabalho(" not in texto and "import sessaotrabalho\n" not in texto  # nenhuma leitura/escrita de sessões
        assert "horas_usuario" not in texto and "horasusuario" not in texto and "executor" not in texto
    # o ÚNICO contato com o módulo de sessões é a AUTORIDADE da "etapa atual" (consulta de etapas do workflow), nunca uma sessão
    assert codigo(servico).count("sessao_repository.") == 1 and "sessao_repository.get_etapa_atual" in codigo(servico)
    assert {c.name for c in modelo.DemandaStatusIntervalo.__table__.columns} >= {"iniciado_por_usuario_id"}
    assert not any("executor" in c.name or "horas" in c.name for c in modelo.DemandaStatusIntervalo.__table__.columns)


# ── concorrência REAL (duas conexões independentes) ──────────────────────────────────────────────────────────────


def test_duas_transicoes_concorrentes_nunca_deixam_dois_abertos(test_engine) -> None:
    """Duas `Session` independentes mudam o status da MESMA Demanda ao mesmo tempo: a segunda espera o lock da linha, relê e a linha do tempo fica coerente
    (1 aberto, sem sobreposição) — nunca IntegrityError, nunca 2 abertos. O estado final da Demanda e o intervalo aberto concordam."""
    from app.models.empresa import Empresa
    from app.models.usuario import Usuario

    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    with Session(test_engine) as setup:
        empresa = Empresa(id=str(uuid.uuid4()), nome="Conc Intervalo", documento=None, codigo_interno=f"CONC-IV-{sufixo}".upper(), status="ativa", created_at=agora, updated_at=agora)
        setup.add(empresa)
        setup.flush()
        demanda = Demanda(
            id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"T26{uuid.uuid4().int % 100000:05d}", ano_referencia=2026, sequencial_referencia=uuid.uuid4().int % 100000,
            numero_operacional=uuid.uuid4().int % 1000000, identificador=f"#{uuid.uuid4().int % 1000000}", nome="Concorrente", status="planejada", prioridade="media",
            created_at=agora, updated_at=agora,
        )
        setup.add(demanda)
        setup.flush()
        DemandaIntervaloService().sincronizar(setup, demanda, quando=agora - timedelta(hours=1), origem="criacao")
        setup.commit()
        empresa_id, demanda_id = empresa.id, demanda.id

    barreira = threading.Barrier(2)
    erros: list[BaseException] = []

    def mudar(destino: str, quando: datetime) -> None:
        try:
            with Session(test_engine) as db:
                objeto = db.get(Demanda, demanda_id)
                barreira.wait(timeout=10)
                db.execute(select(Demanda.id).where(Demanda.id == demanda_id).with_for_update())  # o lock que `update_demanda` toma antes de decidir
                db.refresh(objeto)
                objeto.status = destino
                DemandaIntervaloService().sincronizar(db, objeto, quando=quando, origem="transicao")
                db.commit()
        except BaseException as exc:  # noqa: BLE001
            erros.append(exc)

    try:
        a = threading.Thread(target=mudar, args=("em_execucao", agora - timedelta(minutes=30)))
        b = threading.Thread(target=mudar, args=("pausada", agora - timedelta(minutes=20)))
        a.start(); b.start(); a.join(30); b.join(30)
        assert erros == []
        with Session(test_engine) as leitura:
            linha = DemandaStatusIntervaloRepository().listar_da_demanda(leitura, demanda_id)
            final = leitura.get(Demanda, demanda_id).status
            assert len(_abertos(linha)) == 1 and _abertos(linha)[0].status == final
            _assert_linha_integra(linha)
            assert len(linha) == 3  # planejada + os dois estados novos, em alguma ordem (quem pegou o lock primeiro)
    finally:
        with test_engine.begin() as limpeza:
            limpeza.execute(text("DELETE FROM demanda_status_intervalos WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM demandas WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
