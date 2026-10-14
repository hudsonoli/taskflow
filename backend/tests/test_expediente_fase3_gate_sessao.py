"""Fase Expediente 3 — abrir SESSÃO pessoal é TRABALHO: passa pela MESMA autoridade de horário (`garantir_trabalho_permitido`) que PATCH/criar/restaurar, e a mudança de status
trava a Demanda ANTES do gate (serializa com o tick). Estrutura: o tick não faz logout, não retoma e não usa agendador externo.
"""

from __future__ import annotations

import inspect
import pathlib
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import demanda_service as modulo_demanda
from app.services import expediente_pausa_service as modulo_pausa
from app.services.demanda_service import DemandaService
from tests.test_demanda import _criar
from tests.test_expediente_fase2_api import _configurar

SP = ZoneInfo("America/Sao_Paulo")
SEGUNDA = date(2026, 10, 5)


@pytest.fixture()
def relogio(monkeypatch):
    def fixar(hhmm: str, segundos: int = 0) -> None:
        h, m = (int(x) for x in hhmm.split(":"))
        instante = datetime(2026, 10, 5, h, m, segundos, tzinfo=SP).astimezone(timezone.utc)
        monkeypatch.setattr("app.core.expediente.agora_utc", lambda: instante)

    fixar("10:30")
    return fixar


def _abrir(client: TestClient, demanda_id: str, **alvo):
    return client.post("/sessoes-trabalho/abrir", json={"demandaId": demanda_id, **alvo})


# ── gate ao abrir sessão ─────────────────────────────────────────────────────────────────────────────────────────


def test_dentro_da_janela_abre(client_admin, usuario_operador, relogio) -> None:
    _configurar(client_admin)
    demanda_id = _criar(client_admin, status="em_execucao")["id"]
    assert _abrir(client_admin, demanda_id, usuarioId=usuario_operador.id).status_code == 201


@pytest.mark.parametrize("hora, segundos", [("12:00", 10), ("12:30", 0), ("12:59", 59), ("18:00", 0), ("03:00", 0)])
def test_fora_da_janela_o_operador_nao_inicia_sessao_mesmo_com_a_demanda_ainda_em_execucao(hora, segundos, client_admin, usuario_operador, relogio) -> None:
    """A corrida das 12:00:10: a Demanda ainda está `em_execucao` porque o tick não rodou — a sessão nova NÃO abre."""
    _configurar(client_admin)
    demanda_id = _criar(client_admin, status="em_execucao")["id"]
    relogio(hora, segundos)
    resposta = _abrir(client_admin, demanda_id, usuarioId=usuario_operador.id)
    assert resposta.status_code == 409, resposta.text
    detalhe = resposta.json()["detail"]
    assert detalhe["code"] == "FORA_DE_EXPEDIENTE"  # o MESMO contrato do PATCH — nenhum código novo
    assert "manhaInicio" in detalhe["expediente"]


def test_sessao_recusada_nao_cria_sessao_nem_deixa_evento_de_inicio(client_admin, usuario_operador, db_session, relogio) -> None:
    from sqlalchemy import func, select

    from app.models.evento import Evento
    from app.models.sessao_trabalho import SessaoTrabalho

    _configurar(client_admin)
    demanda_id = _criar(client_admin, status="em_execucao")["id"]
    db_session.commit()
    eventos = db_session.scalar(select(func.count()).select_from(Evento).where(Evento.tipo == "sessao_trabalho_iniciada"))
    relogio("12:30")
    assert _abrir(client_admin, demanda_id, usuarioId=usuario_operador.id).status_code == 409
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(SessaoTrabalho)) == 0
    assert db_session.scalar(select(func.count()).select_from(Evento).where(Evento.tipo == "sessao_trabalho_iniciada")) == eventos


def test_isentos_abrem_sessao_fora_da_janela(client_admin, usuario_gestor, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    demanda_id = _criar(client_admin, status="em_execucao")["id"]
    relogio("12:30")
    assert _abrir(client_admin, demanda_id, usuarioId=usuario_gestor.id).status_code == 201  # quem está sujeito é a PESSOA da sessão
    outra = _criar(client_admin, status="em_execucao")["id"]
    usuario_operador.acesso_fora_expediente = True
    db_session.flush()
    assert _abrir(client_admin, outra, usuarioId=usuario_operador.id).status_code == 201


def test_sessao_so_de_departamento_e_tratada_como_sujeita(client_admin, relogio, db_session, empresa) -> None:
    from tests.test_sessao_trabalho_integridade import _departamento  # type: ignore  # noqa: PLC0415

    _configurar(client_admin)
    demanda_id = _criar(client_admin, status="em_execucao")["id"]
    departamento = _departamento(db_session, empresa)
    assert _abrir(client_admin, demanda_id, departamentoId=departamento.id).status_code == 201  # dentro da janela
    outra = _criar(client_admin, status="em_execucao")["id"]
    relogio("12:30")
    assert _abrir(client_admin, outra, departamentoId=departamento.id).status_code == 409  # fora: sem pessoa isenta para liberar


def test_regra_desligada_libera_a_sessao(client_admin, usuario_operador, relogio) -> None:
    _configurar(client_admin, ativo=False)
    demanda_id = _criar(client_admin, status="em_execucao")["id"]
    relogio("03:00")
    assert _abrir(client_admin, demanda_id, usuarioId=usuario_operador.id).status_code == 201


# ── a mudança de status trava a Demanda ANTES do gate ────────────────────────────────────────────────────────────


def test_update_demanda_trava_a_linha_antes_de_decidir_o_horario(client_admin, usuario_admin, db_session, relogio, monkeypatch) -> None:
    _configurar(client_admin)
    demanda_id = _criar(client_admin)["id"]
    ordem: list[str] = []
    servico = DemandaService()
    original_lock = servico.repository.bloquear_demanda_para_atualizacao

    def lock(db, demanda):
        ordem.append("lock")
        return original_lock(db, demanda)

    monkeypatch.setattr(servico.repository, "bloquear_demanda_para_atualizacao", lock)
    original_gate = modulo_demanda.garantir_trabalho_permitido

    def gate(*a, **k):
        ordem.append("gate")
        return original_gate(*a, **k)

    monkeypatch.setattr(modulo_demanda, "garantir_trabalho_permitido", gate)
    from app.models.demanda import Demanda
    from app.schemas.demanda import DemandaUpdate

    servico.update_demanda(db_session, db_session.get(Demanda, demanda_id), DemandaUpdate(status="em_execucao"), actor=usuario_admin)
    assert ordem[:2] == ["lock", "gate"]


# ── o tick é só pausa: sem logout, sem retomada, sem agendador externo ────────────────────────────────────────────


def _codigo_sem_docstrings(modulo) -> str:
    """O código do módulo SEM comentários e docstrings (só o que executa)."""
    import ast

    arvore = ast.parse(inspect.getsource(modulo))
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and no.body and isinstance(no.body[0], ast.Expr) and isinstance(getattr(no.body[0], "value", None), ast.Constant) and isinstance(no.body[0].value.value, str):
            no.body = no.body[1:] or [ast.Pass()]
    return ast.unparse(arvore)


def test_o_tick_nao_faz_logout_nem_retoma_nem_usa_agendador_externo() -> None:
    from app.core import expediente_tick as modulo_tick

    codigo = _codigo_sem_docstrings(modulo_pausa).lower()
    assert "logout" not in codigo and "get_current_user" not in codigo and "ultimo_corte_logout" not in codigo
    # nenhuma transição PARA em_execucao (nada de retomar): o serviço só escreve "pausada"
    assert not re.search(r"\.status = ['\"]em_execucao['\"]", codigo)
    assert "demanda.status = 'pausada'" in codigo
    tick = _codigo_sem_docstrings(modulo_tick).lower()
    assert "apscheduler" not in tick and "redis" not in tick and "asyncio" in tick
    raiz = pathlib.Path(modulo_pausa.__file__).resolve().parents[2]
    requisitos = (raiz / "requirements.txt").read_text(encoding="utf-8").lower() if (raiz / "requirements.txt").exists() else ""
    assert "apscheduler" not in requisitos
