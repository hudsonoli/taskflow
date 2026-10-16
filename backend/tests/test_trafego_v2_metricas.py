"""Tráfego V2 — Fase 2: camada de MÉTRICAS OPERACIONAIS (`GET /trafego/operacional/agora` e `/gargalos`).

TEMPO OPERACIONAL ≠ TEMPO PESSOAL. Estes testes provam: o escopo e os KPIs do AGORA, a idade do estado, o recorte dos intervalos ao período, a definição de `n`, a fila/WIP com idade NA
ETAPA, a cobertura parcial, o isolamento entre empresas, a composição dos filtros, o RBAC reaproveitado e — principalmente — que nada do tempo pessoal (`sessoes_trabalho`) entra.
Os dados são sintéticos (ORM direto) e o "agora" do serviço é injetado: a suíte nunca depende do relógio real nem de produção.
"""

from __future__ import annotations

import itertools
import random
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_status_intervalo import DemandaStatusIntervalo
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.demanda_workflow_etapa_departamento_responsavel import DemandaWorkflowEtapaDepartamentoResponsavel
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel
from app.models.empresa import Empresa
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.models.usuario_permissao import UsuarioPermissao
from app.services.regra_expediente_service import RegraExpedienteService
from tests.test_d1_2a_cliente_projeto import _projeto
from tests.test_demanda import _cliente, _criar
from tests.test_sessao_trabalho import _client_para, _departamento, _usuario

SP = ZoneInfo("America/Sao_Paulo")
AGORA = datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc)  # quarta 12:00 em São Paulo
_SEQ = itertools.count(1)


def _t(dia: int, hora: int = 0, minuto: int = 0) -> datetime:
    """Instante UTC em outubro de 2026."""
    return datetime(2026, 10, dia, hora, minuto, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def relogio(monkeypatch):
    """O "agora" das métricas é fixo; devolve um setter para os testes que precisam mover o relógio (inclusive o do motor de intervalos)."""

    def fixar(instante: datetime) -> None:
        for modulo in (
            "app.services.trafego_operacional_service",
            "app.core.expediente",
            "app.services.demanda_service",
            "app.services.demanda_workflow_service",
            "app.services.regra_expediente_service",
        ):
            monkeypatch.setattr(f"{modulo}.agora_utc", lambda instante=instante: instante)

    fixar(AGORA)
    return fixar


# ── construtores sintéticos (ORM direto) ─────────────────────────────────────────────────────────────────────────


def _demanda(
    db: Session,
    empresa: Empresa,
    *,
    status: str = "em_execucao",
    prazo: datetime | None = None,
    cliente_id: str | None = None,
    projeto_id: str | None = None,
    nome: str | None = None,
) -> Demanda:
    n = next(_SEQ)
    agora = datetime.now(timezone.utc)
    demanda = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_referencia=f"T26{n:07d}"[:16],
        ano_referencia=26,
        sequencial_referencia=n,
        numero_operacional=10_000 + n,
        nome=nome or f"Demanda sintética {n}",
        status=status,
        prioridade="media",
        cliente_id=cliente_id,
        projeto_id=projeto_id,
        prazo_etapa_atual=prazo,
        created_at=agora,
        updated_at=agora,
    )
    db.add(demanda)
    db.flush()
    return demanda


def _etapa(db: Session, demanda: Demanda, ordem: int, nome: str, *, tipo: str = "execucao", concluida: bool = False) -> DemandaWorkflowEtapa:
    agora = datetime.now(timezone.utc)
    etapa = DemandaWorkflowEtapa(
        id=str(uuid.uuid4()),
        demanda_id=demanda.id,
        ordem=ordem,
        nome=nome,
        tipo=tipo,
        quantidade_antes_deadline=1,
        unidade_prazo="dias_corridos",
        status="concluida" if concluida else "pendente",
        concluida_em=agora if concluida else None,
        created_at=agora,
        updated_at=agora,
    )
    db.add(etapa)
    db.flush()
    return etapa


def _resp_etapa(db: Session, etapa: DemandaWorkflowEtapa, usuario: Usuario) -> None:
    db.add(DemandaWorkflowEtapaResponsavel(demanda_workflow_etapa_id=etapa.id, usuario_id=usuario.id, created_at=datetime.now(timezone.utc)))
    db.flush()


def _dep_etapa(db: Session, etapa: DemandaWorkflowEtapa, departamento) -> None:
    db.add(DemandaWorkflowEtapaDepartamentoResponsavel(demanda_workflow_etapa_id=etapa.id, departamento_id=departamento.id, created_at=datetime.now(timezone.utc)))
    db.flush()


def _resp_demanda(db: Session, demanda: Demanda, usuario: Usuario) -> None:
    db.add(DemandaResponsavel(demanda_id=demanda.id, usuario_id=usuario.id, created_at=datetime.now(timezone.utc)))
    db.flush()


def _intervalo(
    db: Session,
    demanda: Demanda,
    status: str,
    inicio: datetime,
    fim: datetime | None = None,
    *,
    etapa: DemandaWorkflowEtapa | None = None,
    origem: str = "transicao",
) -> DemandaStatusIntervalo:
    agora = datetime.now(timezone.utc)
    intervalo = DemandaStatusIntervalo(
        id=str(uuid.uuid4()),
        empresa_id=demanda.empresa_id,
        demanda_id=demanda.id,
        status=status,
        workflow_etapa_id=etapa.id if etapa is not None else None,
        inicio_em=inicio,
        fim_em=fim,
        duracao_segundos=int((fim - inicio).total_seconds()) if fim is not None else None,
        motivo_fim="mudanca_status" if fim is not None else None,
        origem=origem,
        created_at=agora,
        updated_at=agora,
    )
    db.add(intervalo)
    db.flush()
    return intervalo


def _get(cliente: TestClient, caminho: str, **params):
    return cliente.get(f"/trafego/operacional/{caminho}", params={k: v for k, v in params.items() if v is not None})


def _iso(instante: datetime) -> str:
    return instante.isoformat()


def _chaves(valor) -> set[str]:
    """Todas as chaves de um JSON, recursivamente."""
    achadas: set[str] = set()
    if isinstance(valor, dict):
        for chave, sub in valor.items():
            achadas.add(chave)
            achadas |= _chaves(sub)
    elif isinstance(valor, list):
        for sub in valor:
            achadas |= _chaves(sub)
    return achadas


def _etapa_por_nome(corpo: dict, nome: str) -> dict:
    [linha] = [e for e in corpo["etapas"] if e["etapaNome"].strip().lower() == nome.lower()]
    return linha


# ── AGORA ────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_agora_empresa_vazia(client_admin) -> None:
    corpo = _get(client_admin, "agora").json()
    assert corpo["kpis"] == {"emExecucao": 0, "atrasadas": 0, "vencemHoje": 0, "semResponsavel": 0, "semPrazo": 0, "semEtapaAtual": 0}
    assert corpo["emExecucao"] == [] and corpo["emExecucaoTotal"] == 0 and corpo["truncado"] is False
    assert corpo["escopoStatus"] == ["planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"]
    assert corpo["agoraServidor"].startswith("2026-10-14T15:00:00")


def _cenario_agora(db: Session, empresa: Empresa):
    usuario_a, usuario_b = _usuario(db, empresa), _usuario(db, empresa)
    cliente, departamento = _cliente(db, empresa), _departamento(db, empresa)
    projeto = _projeto(db, empresa, cliente_id=cliente.id)
    prazo_atrasado = AGORA - timedelta(hours=1)  # 11:00 SP — hoje, já vencido
    prazo_hoje = datetime(2026, 10, 14, 18, 0, tzinfo=SP)  # hoje, ainda no prazo
    a = _demanda(db, empresa, prazo=prazo_atrasado, cliente_id=cliente.id, projeto_id=projeto.id, nome="A atrasada")
    _resp_demanda(db, a, usuario_a)
    _intervalo(db, a, "em_execucao", AGORA - timedelta(hours=2))
    b = _demanda(db, empresa, prazo=prazo_hoje, nome="B workflow")
    b1 = _etapa(db, b, 1, "Criacao", concluida=True)
    b2 = _etapa(db, b, 2, "Revisao", tipo="aprovacao")
    _resp_etapa(db, b2, usuario_b)
    _dep_etapa(db, b2, departamento)
    _resp_demanda(db, b, usuario_a)  # responsável da DEMANDA não conta quando há etapa atual: vale o da etapa
    _intervalo(db, b, "em_execucao", AGORA - timedelta(minutes=30), etapa=b2)
    c = _demanda(db, empresa, status="pausada", nome="C pausada sem dono")
    _intervalo(db, c, "pausada", AGORA - timedelta(days=1))
    d = _demanda(db, empresa, status="planejada", prazo=AGORA + timedelta(days=1), nome="D planejada")
    _intervalo(db, d, "planejada", AGORA - timedelta(hours=3))
    i = _demanda(db, empresa, nome="I workflow concluído")
    _etapa(db, i, 1, "Unica", concluida=True)
    _intervalo(db, i, "em_execucao", AGORA - timedelta(hours=5))
    # fora do escopo de triagem (nenhum conta em nenhum KPI, mesmo com prazo vencido)
    for status in ("rascunho", "concluida", "cancelada", "arquivada"):
        fora = _demanda(db, empresa, status=status, prazo=AGORA - timedelta(days=10))
        if status == "rascunho":
            _intervalo(db, fora, "rascunho", AGORA - timedelta(days=2))
    return {"a": a, "b": b, "b2": b2, "c": c, "d": d, "i": i, "usuario_a": usuario_a, "usuario_b": usuario_b, "departamento": departamento, "cliente": cliente, "projeto": projeto}


def test_agora_kpis_escopo_e_lista(client_admin, db_session, empresa) -> None:
    ctx = _cenario_agora(db_session, empresa)
    corpo = _get(client_admin, "agora").json()
    assert corpo["kpis"] == {
        "emExecucao": 3,  # A, B, I
        "atrasadas": 1,  # só A (rascunho/terminais com prazo vencido ficam de fora)
        "vencemHoje": 2,  # A (11:00, já vencida) e B (18:00) — dia LOCAL da empresa
        "semResponsavel": 3,  # C, D e I (B tem responsável NA ETAPA; A na Demanda)
        "semPrazo": 2,  # C e I
        "semEtapaAtual": 1,  # I: workflow concluído e Demanda ainda aberta (pendência conhecida, não erro)
    }
    assert corpo["emExecucaoTotal"] == 3
    # atrasadas primeiro; depois a mais antiga no estado: A (2 h, atrasada), I (5 h), B (30 min)
    assert [linha["demandaId"] for linha in corpo["emExecucao"]] == [ctx["a"].id, ctx["i"].id, ctx["b"].id]


def test_agora_linha_da_demanda(client_admin, db_session, empresa) -> None:
    ctx = _cenario_agora(db_session, empresa)
    linhas = {linha["demandaId"]: linha for linha in _get(client_admin, "agora").json()["emExecucao"]}
    a = linhas[ctx["a"].id]
    assert a["titulo"] == "A atrasada" and a["status"] == "em_execucao" and a["atrasada"] is True
    assert a["idadeEstadoSegundos"] == 7200 and a["inicioEstadoAtual"].startswith("2026-10-14T13:00:00")
    assert a["projeto"] == {"id": ctx["projeto"].id, "nome": ctx["projeto"].nome} and a["cliente"]["id"] == ctx["cliente"].id
    assert a["etapaAtual"] is None and a["origemResponsaveis"] == "demanda"
    assert [r["usuarioId"] for r in a["responsaveis"]] == [ctx["usuario_a"].id]
    assert set(a["responsaveis"][0]) == {"usuarioId", "nome"}  # nada além de id e nome
    assert {"codigoReferencia", "numeroOperacional", "identificador"} <= set(a)
    b = linhas[ctx["b"].id]
    assert b["atrasada"] is False and b["idadeEstadoSegundos"] == 1800
    assert b["etapaAtual"] == {"id": ctx["b2"].id, "nome": "Revisao", "tipo": "aprovacao", "departamentos": [{"id": ctx["departamento"].id, "nome": ctx["departamento"].nome}]}
    assert b["origemResponsaveis"] == "etapa_atual" and [r["usuarioId"] for r in b["responsaveis"]] == [ctx["usuario_b"].id]  # NÃO o responsável da Demanda
    assert linhas[ctx["i"].id]["etapaAtual"] is None  # workflow concluído: etapaAtual null, sem erro


def test_agora_departamento_sozinho_nao_e_responsavel(client_admin, db_session, empresa) -> None:
    """Responsável = PESSOA. Etapa atual atribuída só a um departamento (fila de departamento) continua "sem responsável"."""
    demanda = _demanda(db_session, empresa)
    etapa = _etapa(db_session, demanda, 1, "Redacao")
    _dep_etapa(db_session, etapa, _departamento(db_session, empresa))
    _intervalo(db_session, demanda, "em_execucao", AGORA - timedelta(hours=1), etapa=etapa)
    corpo = _get(client_admin, "agora").json()
    assert corpo["kpis"]["semResponsavel"] == 1 and corpo["emExecucao"][0]["responsaveis"] == []
    _resp_etapa(db_session, etapa, _usuario(db_session, empresa))
    assert _get(client_admin, "agora").json()["kpis"]["semResponsavel"] == 0


def test_agora_sem_intervalo_aberto_nao_inventa_idade(client_admin, db_session, empresa) -> None:
    sem = _demanda(db_session, empresa, nome="sem intervalo")
    [linha] = _get(client_admin, "agora").json()["emExecucao"]
    assert linha["demandaId"] == sem.id and linha["inicioEstadoAtual"] is None and linha["idadeEstadoSegundos"] is None


def test_agora_limite_e_truncado(client_admin, db_session, empresa) -> None:
    for _ in range(3):
        _intervalo(db_session, _demanda(db_session, empresa), "em_execucao", AGORA - timedelta(hours=1))
    corpo = _get(client_admin, "agora", limite=2).json()
    assert len(corpo["emExecucao"]) == 2 and corpo["emExecucaoTotal"] == 3 and corpo["truncado"] is True and corpo["limite"] == 2
    assert _get(client_admin, "agora", limite=0).status_code == 422 and _get(client_admin, "agora", limite=201).status_code == 422


def test_agora_vence_hoje_usa_o_fuso_da_empresa(client_admin, db_session, empresa) -> None:
    """O dia é o da EMPRESA — não o do container nem o do navegador. Dois prazos futuros: Q = 22:30 de hoje em São Paulo (01:30Z de amanhã em UTC) e P = 05:00Z de 15/10
    (02:00 de AMANHÃ em São Paulo, mas ainda "hoje" para quem está em Auckland, UTC+13)."""
    _demanda(db_session, empresa, status="planejada", prazo=datetime(2026, 10, 14, 22, 30, tzinfo=SP))  # Q
    _demanda(db_session, empresa, status="planejada", prazo=datetime(2026, 10, 15, 5, 0, tzinfo=timezone.utc))  # P
    corpo = _get(client_admin, "agora").json()
    assert corpo["fusoEmpresa"] == "America/Sao_Paulo" and corpo["diaLocal"] == "2026-10-14"
    assert corpo["hojeInicio"].startswith("2026-10-14T03:00:00") and corpo["hojeFim"].startswith("2026-10-15T03:00:00")
    assert corpo["kpis"]["vencemHoje"] == 1  # só Q
    regra = RegraExpedienteService().get_ou_criar(db_session, empresa_id=empresa.id)
    regra.timezone = "Pacific/Auckland"
    db_session.flush()
    corpo = _get(client_admin, "agora").json()
    assert corpo["fusoEmpresa"] == "Pacific/Auckland" and corpo["diaLocal"] == "2026-10-15"  # 15:00Z já é madrugada de 15/10 lá
    assert corpo["hojeInicio"].startswith("2026-10-14T11:00:00") and corpo["hojeFim"].startswith("2026-10-15T11:00:00")
    assert corpo["kpis"]["vencemHoje"] == 2  # Q e P


def test_agora_isolamento_entre_empresas(client_admin, db_session, empresa, outra_empresa) -> None:
    alheia = _demanda(db_session, outra_empresa, prazo=AGORA - timedelta(hours=3), nome="alheia")
    _intervalo(db_session, alheia, "em_execucao", AGORA - timedelta(hours=9))
    propria = _demanda(db_session, empresa, nome="propria")
    _intervalo(db_session, propria, "em_execucao", AGORA - timedelta(hours=1))
    corpo = _get(client_admin, "agora").json()
    assert [linha["demandaId"] for linha in corpo["emExecucao"]] == [propria.id]
    assert corpo["kpis"]["emExecucao"] == 1 and corpo["kpis"]["atrasadas"] == 0 and corpo["kpis"]["semResponsavel"] == 1


# ── TEMPO OPERACIONAL ≠ PESSOAL ──────────────────────────────────────────────────────────────────────────────────


def test_oito_horas_em_execucao_sem_nenhuma_sessao_pessoal(client_admin, db_session, empresa) -> None:
    demanda = _demanda(db_session, empresa)
    _intervalo(db_session, demanda, "em_execucao", AGORA - timedelta(hours=8))
    [linha] = _get(client_admin, "agora").json()["emExecucao"]
    assert linha["idadeEstadoSegundos"] == 8 * 3600  # o ESTADO da Demanda dura 8 h — ninguém "trabalhou" 8 h
    corpo = _get(client_admin, "gargalos").json()
    assert corpo["semEtapa"]["tempoExecucaoTotalSegundos"] == 8 * 3600
    for resposta in (_get(client_admin, "agora").json(), corpo):
        proibidas = {c for c in _chaves(resposta) if any(p in c.lower() for p in ("horas", "sessao", "executor", "trabalhad", "pessoal"))}
        assert not proibidas, proibidas


def test_sessao_pessoal_nao_soma_nem_substitui_o_tempo_operacional(client_admin, db_session, empresa) -> None:
    usuario = _usuario(db_session, empresa)
    demanda = _demanda(db_session, empresa)
    _intervalo(db_session, demanda, "em_execucao", AGORA - timedelta(hours=8))
    antes = (_get(client_admin, "agora").json(), _get(client_admin, "gargalos").json())
    agora_db = datetime.now(timezone.utc)
    db_session.add(
        SessaoTrabalho(
            id=str(uuid.uuid4()), empresa_id=empresa.id, demanda_id=demanda.id, usuario_id=usuario.id, evento_inicio_id=str(uuid.uuid4()), evento_fim_id=str(uuid.uuid4()),
            status="encerrada", created_at=agora_db, updated_at=agora_db, inicio_em=AGORA - timedelta(hours=4), fim_em=AGORA - timedelta(hours=2), duracao_segundos=7200,
        )
    )
    db_session.flush()
    depois = (_get(client_admin, "agora").json(), _get(client_admin, "gargalos").json())
    assert depois == antes  # a sessão de 2 h NÃO altera nada: continua 8 h operacionais
    assert depois[1]["semEtapa"]["tempoExecucaoTotalSegundos"] == 8 * 3600


def test_nenhuma_consulta_toca_sessoes_trabalho(client_admin, db_session, empresa) -> None:
    _cenario_agora(db_session, empresa)
    statements: list[str] = []

    def _captura(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _captura)
    try:
        assert _get(client_admin, "agora").status_code == 200 and _get(client_admin, "gargalos").status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", _captura)
    assert statements and not [s for s in statements if "sessoes_trabalho" in s]


# ── GARGALOS: recorte, n e filtros ───────────────────────────────────────────────────────────────────────────────


def _cenario_gargalos(db: Session, empresa: Empresa):
    d1, d2 = _departamento(db, empresa), _departamento(db, empresa)
    c1, c2 = _cliente(db, empresa), _cliente(db, empresa)
    p1, p2 = _projeto(db, empresa, cliente_id=c1.id), _projeto(db, empresa, cliente_id=c2.id)
    # X — etapa "Redacao" (departamento d1, cliente c1): atravessa o INÍCIO do período, tem 2 ciclos e atravessa o FIM
    x = _demanda(db, empresa, cliente_id=c1.id, projeto_id=p1.id)
    ex = _etapa(db, x, 1, "Redacao")
    _dep_etapa(db, ex, d1)
    _intervalo(db, x, "em_execucao", _t(9, 20), _t(10, 10), etapa=ex)  # 10 h dentro (20:00 de 09 → 10:00 de 10; só 00:00→10:00 conta)
    _intervalo(db, x, "pausada", _t(10, 10), _t(10, 12), etapa=ex)  # 2 h
    _intervalo(db, x, "em_execucao", _t(10, 12), _t(11, 0), etapa=ex)  # 12 h (2º ciclo, MESMA etapa)
    _intervalo(db, x, "aguardando_cliente", _t(11, 0), _t(13, 0), etapa=ex)  # termina DEPOIS do período → só 24 h contam
    # Y — OUTRA Demanda, MESMA definição de etapa (nome com caixa/espaços diferentes), departamento d2, cliente c2
    y = _demanda(db, empresa, cliente_id=c2.id, projeto_id=p2.id)
    ey = _etapa(db, y, 1, "  REDACAO ")
    _dep_etapa(db, ey, d2)
    _intervalo(db, y, "em_execucao", _t(11, 0), _t(11, 6), etapa=ey)  # 6 h
    _intervalo(db, y, "bloqueada", _t(11, 6), _t(11, 8), etapa=ey)  # 2 h
    # Z — etapa "Revisao" (aprovacao), departamento d1, cliente c1
    z = _demanda(db, empresa, cliente_id=c1.id, projeto_id=p1.id)
    ez = _etapa(db, z, 1, "Revisao", tipo="aprovacao")
    _dep_etapa(db, ez, d1)
    _intervalo(db, z, "em_execucao", _t(10, 0), _t(10, 1), etapa=ez)  # 1 h
    # W — etapa "Revisao" com intervalo ABERTO desde 13/10 00:00 (só entra em períodos que alcançam 13/10)
    w = _demanda(db, empresa, cliente_id=c2.id, projeto_id=p2.id)
    ew = _etapa(db, w, 1, "Revisao", tipo="aprovacao")
    _dep_etapa(db, ew, d2)
    _intervalo(db, w, "em_execucao", _t(13, 0), None, etapa=ew)
    # V — inteiramente ANTES do período e o mais antigo da empresa (define `medicaoDesde`)
    v = _demanda(db, empresa)
    ev = _etapa(db, v, 1, "Redacao")
    _intervalo(db, v, "em_execucao", _t(1, 0), _t(2, 0), etapa=ev, origem="migracao")
    # S — sem workflow: intervalo sem etapa
    s = _demanda(db, empresa)
    _intervalo(db, s, "em_execucao", _t(10, 0), _t(10, 0, 5))
    return {"x": x, "ex": ex, "ey": ey, "ez": ez, "d1": d1, "d2": d2, "c1": c1, "c2": c2, "p1": p1, "p2": p2}


P1 = {"inicio": _iso(_t(10, 0)), "fim": _iso(_t(12, 0))}


def test_gargalos_recorte_ciclos_n_media_e_maior(client_admin, db_session, empresa) -> None:
    _cenario_gargalos(db_session, empresa)
    corpo = _get(client_admin, "gargalos", **P1).json()
    redacao = _etapa_por_nome(corpo, "redacao")
    # X e Y são DEFINIÇÕES iguais (normalização) e 2 ocorrências — não 6, que seria a contagem bruta de intervalos
    assert redacao["n"] == 2 and redacao["tipo"] == "execucao"
    assert redacao["nExecucao"] == 2
    assert redacao["tempoExecucaoTotalSegundos"] == (10 + 12 + 6) * 3600  # X: 10 h recortada + 12 h; Y: 6 h
    assert redacao["tempoExecucaoMedioSegundos"] == 14 * 3600  # 28 h ÷ 2 ocorrências
    assert redacao["tempoExecucaoMaiorSegundos"] == 22 * 3600  # a ocorrência X (os 2 ciclos somados)
    assert (redacao["nPausado"], redacao["tempoPausadoTotalSegundos"], redacao["tempoPausadoMedioSegundos"]) == (1, 2 * 3600, 2 * 3600)
    assert (redacao["nBloqueado"], redacao["tempoBloqueadoTotalSegundos"], redacao["tempoBloqueadoMaiorSegundos"]) == (1, 2 * 3600, 2 * 3600)
    assert (redacao["nAguardandoCliente"], redacao["tempoAguardandoClienteTotalSegundos"], redacao["tempoAguardandoClienteMaiorSegundos"]) == (1, 24 * 3600, 24 * 3600)
    revisao = _etapa_por_nome(corpo, "revisao")
    assert revisao["n"] == 1 and revisao["tempoExecucaoTotalSegundos"] == 3600 and revisao["tipo"] == "aprovacao"  # o intervalo aberto de W começa em 13/10: fora do período
    assert corpo["semEtapa"]["n"] == 1 and corpo["semEtapa"]["tempoExecucaoTotalSegundos"] == 300
    # ordenação documentada: maior tempo médio em execução primeiro
    assert [e["etapaNome"].strip().lower() for e in corpo["etapas"]] == ["redacao", "revisao"] and corpo["etapasTotal"] == 2


def test_gargalos_intervalo_que_cobre_o_periodo_inteiro_e_fronteiras(client_admin, db_session, empresa) -> None:
    cobre, antes, depois = (_demanda(db_session, empresa) for _ in range(3))
    for demanda, ini, fim in ((cobre, _t(8, 0), _t(14, 0)), (antes, _t(9, 0), _t(10, 0)), (depois, _t(12, 0), _t(13, 0))):
        _intervalo(db_session, demanda, "em_execucao", ini, fim, etapa=_etapa(db_session, demanda, 1, "Cobertura"))
    corpo = _get(client_admin, "gargalos", **P1).json()
    linha = _etapa_por_nome(corpo, "cobertura")
    # só o que atravessa o período inteiro conta (48 h do recorte); um intervalo que TERMINA no início ou COMEÇA no fim do período não tem nenhum segundo dentro dele
    assert linha["n"] == 1 and linha["tempoExecucaoTotalSegundos"] == 48 * 3600


def test_gargalos_etapas_homonimas_na_mesma_demanda_sao_duas_ocorrencias(client_admin, db_session, empresa) -> None:
    """Identidade materializada, não só nome: duas etapas "Alteracao" da MESMA Demanda (ex.: refação) são duas ocorrências da mesma definição."""
    demanda = _demanda(db_session, empresa)
    primeira, segunda = _etapa(db_session, demanda, 1, "Alteracao"), _etapa(db_session, demanda, 2, "Alteracao")
    _intervalo(db_session, demanda, "em_execucao", _t(10, 0), _t(10, 2), etapa=primeira)
    _intervalo(db_session, demanda, "em_execucao", _t(10, 2), _t(10, 6), etapa=segunda)
    linha = _etapa_por_nome(_get(client_admin, "gargalos", **P1).json(), "alteracao")
    assert linha["n"] == 2 and linha["nExecucao"] == 2 and linha["tempoExecucaoTotalSegundos"] == 6 * 3600
    assert linha["tempoExecucaoMedioSegundos"] == 3 * 3600 and linha["tempoExecucaoMaiorSegundos"] == 4 * 3600


def test_gargalos_intervalo_aberto_conta_ate_o_fim_efetivo(client_admin, db_session, empresa) -> None:
    ctx = _cenario_gargalos(db_session, empresa)
    # o fim pedido está NO FUTURO: conta só até o agora do servidor (14/10 15:00) — 39 h desde 13/10 00:00
    corpo = _get(client_admin, "gargalos", inicio=_iso(_t(13, 0)), fim=_iso(_t(15, 12))).json()
    assert corpo["periodo"]["fimEfetivo"].startswith("2026-10-14T15:00:00") and corpo["periodo"]["fim"].startswith("2026-10-15T12:00:00")
    revisao = _etapa_por_nome(corpo, "revisao")
    assert revisao["tempoExecucaoTotalSegundos"] == 39 * 3600 and revisao["n"] == 1
    # nada foi gravado: o intervalo continua aberto no banco
    db_session.expire_all()
    from sqlalchemy import select

    assert db_session.scalars(select(DemandaStatusIntervalo).where(DemandaStatusIntervalo.fim_em.is_(None), DemandaStatusIntervalo.empresa_id == empresa.id)).all()
    assert ctx


def test_gargalos_periodo_padrao_e_limites(client_admin, db_session, empresa) -> None:
    corpo = _get(client_admin, "gargalos").json()
    inicio, fim = datetime.fromisoformat(corpo["periodo"]["inicio"]), datetime.fromisoformat(corpo["periodo"]["fim"])
    assert fim == AGORA and fim - inicio == timedelta(days=30)  # padrão: últimos 30 dias
    assert _get(client_admin, "gargalos", inicio=_iso(AGORA - timedelta(days=90)), fim=_iso(AGORA)).status_code == 200  # 90 dias é o teto
    assert _get(client_admin, "gargalos", inicio=_iso(AGORA - timedelta(days=90, seconds=1)), fim=_iso(AGORA)).status_code == 422
    assert _get(client_admin, "gargalos", inicio=_iso(_t(12, 0)), fim=_iso(_t(10, 0))).status_code == 422
    assert _get(client_admin, "gargalos", inicio=_iso(_t(10, 0)), fim=_iso(_t(10, 0))).status_code == 422
    assert _get(client_admin, "gargalos", inicio="2026-10-10T00:00:00", fim="2026-10-11T00:00:00").status_code == 422  # sem timezone
    assert _get(client_admin, "gargalos", departamentoId="nao-e-uuid").status_code == 422
    # só `fim`: o início é fim − 30 dias
    corpo = _get(client_admin, "gargalos", fim=_iso(_t(12, 0))).json()
    assert datetime.fromisoformat(corpo["periodo"]["fim"]) - datetime.fromisoformat(corpo["periodo"]["inicio"]) == timedelta(days=30)


def test_gargalos_cobertura_parcial(client_admin, db_session, empresa) -> None:
    vazia = _get(client_admin, "gargalos").json()
    assert vazia["medicaoDesde"] is None and vazia["coberturaParcial"] is True  # nada medido: não finge histórico
    assert vazia["etapas"] == [] and vazia["fila"] == []
    _cenario_gargalos(db_session, empresa)  # o intervalo mais antigo é de 01/10 00:00
    dentro = _get(client_admin, "gargalos", **P1).json()
    assert dentro["medicaoDesde"].startswith("2026-10-01T00:00:00") and dentro["coberturaParcial"] is False
    antes = _get(client_admin, "gargalos", inicio=_iso(_t(1, 0) - timedelta(days=5)), fim=_iso(_t(2, 0))).json()
    assert antes["coberturaParcial"] is True
    exato = _get(client_admin, "gargalos", inicio=_iso(_t(1, 0)), fim=_iso(_t(3, 0))).json()
    assert exato["coberturaParcial"] is False  # começar exatamente na medição não é parcial


def test_gargalos_filtros_compoem(client_admin, db_session, empresa) -> None:
    ctx = _cenario_gargalos(db_session, empresa)
    d1, d2, c1, c2, p1, p2 = (ctx[k].id for k in ("d1", "d2", "c1", "c2", "p1", "p2"))

    def etapas(**filtros):
        corpo = _get(client_admin, "gargalos", **P1, **filtros).json()
        return {e["etapaNome"].strip().lower(): e["n"] for e in corpo["etapas"]}, corpo

    assert etapas(departamentoId=d1)[0] == {"redacao": 1, "revisao": 1}  # X e Z
    assert etapas(departamentoId=d2)[0] == {"redacao": 1}  # só Y (W é de d2 mas está fora do período)
    assert etapas(clienteId=c1)[0] == {"redacao": 1, "revisao": 1}
    assert etapas(clienteId=c2)[0] == {"redacao": 1}
    assert etapas(projetoId=p1)[0] == {"redacao": 1, "revisao": 1} and etapas(projetoId=p2)[0] == {"redacao": 1}
    # combinações: período + departamento + cliente
    assert etapas(departamentoId=d1, clienteId=c1)[0] == {"redacao": 1, "revisao": 1}
    assert etapas(departamentoId=d1, clienteId=c2)[0] == {}
    assert etapas(departamentoId=d1, clienteId=c1, projetoId=p2)[0] == {}
    # filtro por etapa (id materializado → expande para a DEFINIÇÃO): Redacao de TODAS as Demandas, sem Revisao
    por_etapa, corpo = etapas(workflowEtapaId=ctx["ex"].id)
    assert por_etapa == {"redacao": 2} and corpo["filtros"]["workflowEtapaId"] == ctx["ex"].id
    assert etapas(workflowEtapaId=ctx["ex"].id, departamentoId=d2)[0] == {"redacao": 1}
    # o filtro por departamento é DA ETAPA: intervalos sem etapa ficam de fora
    assert etapas(departamentoId=d1)[1]["semEtapa"]["n"] == 0
    assert etapas()[1]["semEtapa"]["n"] == 1


def test_gargalos_isolamento_entre_empresas(client_admin, db_session, empresa, outra_empresa) -> None:
    _cenario_gargalos(db_session, empresa)
    antes = _get(client_admin, "gargalos", **P1).json()
    alheio = _cenario_gargalos(db_session, outra_empresa)  # MESMOS nomes de etapa e mesmas janelas, empresa diferente
    for _ in range(5):
        extra = _demanda(db_session, outra_empresa)
        _intervalo(db_session, extra, "em_execucao", _t(10, 0), _t(11, 0))
    depois = _get(client_admin, "gargalos", **P1).json()
    assert depois["etapas"] == antes["etapas"] and depois["semEtapa"] == antes["semEtapa"] and depois["fila"] == antes["fila"] and depois["atual"] == antes["atual"]
    assert depois["medicaoDesde"] == antes["medicaoDesde"]
    # filtros apontando para entidades da OUTRA empresa não vazam nada, e a etapa alheia é 404 (igual a inexistente)
    assert _get(client_admin, "gargalos", **P1, departamentoId=alheio["d1"].id).json()["etapas"] == []
    assert _get(client_admin, "gargalos", **P1, workflowEtapaId=alheio["ex"].id).status_code == 404
    assert _get(client_admin, "gargalos", **P1, workflowEtapaId=str(uuid.uuid4())).status_code == 404


# ── GARGALOS: fila / WIP ─────────────────────────────────────────────────────────────────────────────────────────


def _cenario_fila(db: Session, empresa: Empresa):
    f1 = _demanda(db, empresa)  # Redacao: execução → pausa → execução, tudo na MESMA etapa e contíguo
    e1 = _etapa(db, f1, 1, "Redacao")
    _intervalo(db, f1, "em_execucao", _t(12, 0), _t(12, 6), etapa=e1)
    _intervalo(db, f1, "pausada", _t(12, 6), _t(12, 10), etapa=e1)
    _intervalo(db, f1, "em_execucao", _t(12, 10), None, etapa=e1)
    f2 = _demanda(db, empresa, status="bloqueada")  # chegou em Redacao vindo de OUTRA etapa
    e0 = _etapa(db, f2, 1, "Criacao", concluida=True)
    e2 = _etapa(db, f2, 2, "Redacao")
    _intervalo(db, f2, "em_execucao", _t(11, 0), _t(13, 0), etapa=e0)
    _intervalo(db, f2, "bloqueada", _t(13, 0), None, etapa=e2)
    f3 = _demanda(db, empresa, status="aguardando_cliente")  # DEVOLVIDA: Redacao → Revisao → Redacao (a contagem recomeça na devolução)
    e3 = _etapa(db, f3, 1, "Redacao")
    e3r = _etapa(db, f3, 2, "Revisao", tipo="aprovacao")
    _intervalo(db, f3, "em_execucao", _t(10, 0), _t(11, 0), etapa=e3)
    _intervalo(db, f3, "em_execucao", _t(11, 0), _t(12, 12), etapa=e3r)
    _intervalo(db, f3, "aguardando_cliente", _t(12, 12), None, etapa=e3)
    f4 = _demanda(db, empresa, status="planejada")  # só o intervalo inicial da migração: a idade é TRUNCADA pela medição
    e4 = _etapa(db, f4, 1, "Revisao", tipo="aprovacao")
    _intervalo(db, f4, "planejada", _t(5, 0), None, etapa=e4, origem="migracao")
    f6 = _demanda(db, empresa)  # workflow concluído, Demanda aberta (pendência conhecida)
    _etapa(db, f6, 1, "Unica", concluida=True)
    _intervalo(db, f6, "em_execucao", _t(13, 0))
    f7 = _demanda(db, empresa, status="pausada")  # nunca teve workflow
    _intervalo(db, f7, "pausada", _t(13, 0))
    f8 = _demanda(db, empresa, status="rascunho")  # fora do escopo
    _intervalo(db, f8, "rascunho", _t(6, 0))
    return {"e1": e1, "e2": e2, "e3": e3, "e4": e4}


def test_fila_wip_idade_na_etapa_e_estado(client_admin, db_session, empresa) -> None:
    _cenario_fila(db_session, empresa)
    corpo = _get(client_admin, "gargalos", **P1).json()
    por_nome = {f["etapaNome"]: f for f in corpo["fila"]}
    redacao = por_nome["Redacao"]
    assert (redacao["wip"], redacao["emExecucao"], redacao["bloqueadas"], redacao["aguardandoCliente"], redacao["pausadas"], redacao["planejadas"]) == (3, 1, 1, 1, 0, 0)
    # idade NA ETAPA do mais antigo: f1 (execução+pausa+execução contíguas) desde 12/10 00:00 → 2 d 15 h; f3 NÃO conta 10/10 (voltou de Revisao); f2 só desde 13/10
    assert redacao["maisAntigaDesde"].startswith("2026-10-12T00:00:00") and redacao["maisAntigaSegundos"] == (2 * 24 + 15) * 3600
    assert redacao["maisAntigaTruncadaPelaMedicao"] is False
    # idade no ESTADO atual do mais antigo: f1 em_execucao desde 12/10 10:00 (2 d 5 h) — pergunta diferente da idade na etapa
    assert redacao["idadeEstadoMaisAntigoSegundos"] == (2 * 24 + 5) * 3600
    revisao = por_nome["Revisao"]
    assert revisao["wip"] == 1 and revisao["planejadas"] == 1 and revisao["tipo"] == "aprovacao"
    assert revisao["maisAntigaTruncadaPelaMedicao"] is True and revisao["maisAntigaDesde"].startswith("2026-10-05T00:00:00")  # começa na migração: idade real pode ser maior
    assert corpo["atual"] == {"wip": 6, "planejadas": 1, "emExecucao": 2, "pausadas": 1, "bloqueadas": 1, "aguardandoCliente": 1}  # rascunho fora
    assert corpo["filaSemEtapa"] == {"workflowConcluido": 1, "semWorkflow": 1}
    assert [f["etapaNome"] for f in corpo["fila"]] == ["Redacao", "Revisao"] and corpo["filaTotal"] == 2  # maior WIP primeiro


def test_fila_devolucao_recomeca_a_contagem(client_admin, db_session, empresa) -> None:
    ctx = _cenario_fila(db_session, empresa)
    departamento = _departamento(db_session, empresa)
    _dep_etapa(db_session, ctx["e3"], departamento)  # isola a Demanda DEVOLVIDA (f3): Redacao → Revisao → Redacao
    [redacao] = _get(client_admin, "gargalos", **P1, departamentoId=departamento.id).json()["fila"]
    assert redacao["wip"] == 1 and redacao["aguardandoCliente"] == 1
    # a contagem é desde o RETORNO (12/10 12:00), não desde a primeira passagem (10/10 00:00): a etapa intermediária interrompeu a sequência
    assert redacao["maisAntigaDesde"].startswith("2026-10-12T12:00:00") and redacao["maisAntigaSegundos"] == 51 * 3600


def test_fila_respeita_filtros_e_departamento(client_admin, db_session, empresa) -> None:
    ctx = _cenario_fila(db_session, empresa)
    departamento = _departamento(db_session, empresa)
    _dep_etapa(db_session, ctx["e1"], departamento)  # só a etapa de f1 pertence ao departamento
    corpo = _get(client_admin, "gargalos", **P1, departamentoId=departamento.id).json()
    [redacao] = corpo["fila"]
    assert redacao["wip"] == 1 and redacao["emExecucao"] == 1 and redacao["departamentos"] == [{"id": departamento.id, "nome": departamento.nome}]
    assert corpo["atual"]["wip"] == 1 and corpo["filaSemEtapa"] == {"workflowConcluido": 0, "semWorkflow": 0}


def test_fila_isolamento_entre_empresas(client_admin, db_session, empresa, outra_empresa) -> None:
    _cenario_fila(db_session, empresa)
    antes = _get(client_admin, "gargalos", **P1).json()["fila"]
    _cenario_fila(db_session, outra_empresa)
    assert _get(client_admin, "gargalos", **P1).json()["fila"] == antes


# ── motor + métricas de ponta a ponta ────────────────────────────────────────────────────────────────────────────


def test_integra_com_o_motor_de_intervalos(client_admin, db_session, relogio) -> None:
    """Intervalos criados pelo MOTOR (não pelo teste): 09:00 planejada, 09:00 em execução, 10:15 pausa, 13:00 retoma; agora = 14:30."""
    segunda = datetime(2026, 10, 5, tzinfo=SP)

    def em(h: int, m: int = 0) -> datetime:
        return segunda.replace(hour=h, minute=m).astimezone(timezone.utc)

    relogio(em(9))
    demanda = _criar(client_admin, status="planejada")
    for hora, status in ((em(9), "em_execucao"), (em(10, 15), "pausada"), (em(13), "em_execucao")):
        relogio(hora)
        assert client_admin.patch(f"/demandas/{demanda['id']}", json={"status": status}).status_code == 200
    relogio(em(14, 30))
    [linha] = _get(client_admin, "agora").json()["emExecucao"]
    assert linha["demandaId"] == demanda["id"] and linha["idadeEstadoSegundos"] == 5400  # 13:00 → 14:30
    corpo = _get(client_admin, "gargalos", inicio=_iso(segunda.astimezone(timezone.utc)), fim=_iso(em(23, 59))).json()
    assert corpo["semEtapa"]["tempoExecucaoTotalSegundos"] == 4500 + 5400 and corpo["semEtapa"]["tempoPausadoTotalSegundos"] == 9900
    assert corpo["semEtapa"]["n"] == 1 and corpo["semEtapa"]["tempoExecucaoMedioSegundos"] == 9900  # UMA Demanda, dois ciclos de execução = uma ocorrência


# ── RBAC reaproveitado ───────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("caminho", ["agora", "gargalos"])
def test_rbac_admin_e_gestor_acessam_operador_nao(caminho, client_admin, client_gestor, client_operador, usuario_operador, db_session, client_sem_token) -> None:
    assert _get(client_admin, caminho).status_code == 200
    assert _get(client_gestor, caminho).status_code == 200
    assert _get(client_operador, caminho).status_code == 403
    # a concessão explícita de `trafego.gerenciar` NÃO libera operador (mesmo piso de /sessoes-trabalho)
    agora_db = datetime.now(timezone.utc)
    db_session.add(
        UsuarioPermissao(
            id=str(uuid.uuid4()), empresa_id=usuario_operador.empresa_id, usuario_id=usuario_operador.id, permissao="trafego.gerenciar", efeito="conceder", created_at=agora_db, updated_at=agora_db
        )
    )
    db_session.flush()
    assert _get(client_operador, caminho).status_code == 403
    assert _get(client_sem_token, caminho).status_code in (401, 403)


@pytest.fixture()
def client_sem_token(app) -> TestClient:
    return TestClient(app)


def test_empresa_nao_e_parametro(client_admin, db_session, empresa, outra_empresa) -> None:
    """A empresa vem do token: um `empresaId` na query é ignorado, nunca troca o tenant."""
    alheia = _demanda(db_session, outra_empresa)
    _intervalo(db_session, alheia, "em_execucao", AGORA - timedelta(hours=1))
    assert _get(client_admin, "agora", empresaId=outra_empresa.id).json()["emExecucaoTotal"] == 0


# ── volume lógico e número de queries ────────────────────────────────────────────────────────────────────────────


def _contar_queries(db_session: Session, chamada) -> int:
    n = []

    def _captura(conn, cursor, statement, parameters, context, executemany):
        n.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _captura)
    try:
        chamada()
    finally:
        event.remove(engine, "before_cursor_execute", _captura)
    return len(n)


def _popular_volume(db: Session, empresa: Empresa, *, demandas: int, semente: int) -> dict[str, dict]:
    """Dataset sintético: `demandas` Demandas, 5 definições de etapa, 3 departamentos, 4 clientes, vários ciclos por etapa. Devolve o ESPERADO por definição calculado em Python (independente do SQL)."""
    rng = random.Random(semente)
    deps = [_departamento(db, empresa) for _ in range(3)]
    clientes = [_cliente(db, empresa) for _ in range(4)]
    nomes = ["Briefing", "Redacao", "Arte", "Revisao", "Aprovacao"]
    inicio, fim = _t(10, 0), _t(14, 0)  # período consultado nos testes de volume (termina antes do agora, 14/10 15:00)
    esperado: dict[str, dict] = {nome: {"ocorrencias": 0, "exec": {}, "total_exec": 0, "maior_exec": 0, "n_exec": 0} for nome in nomes}
    for _ in range(demandas):
        d = _demanda(db, empresa, cliente_id=rng.choice(clientes).id, status="pausada")
        cursor = _t(8, 0) + timedelta(minutes=rng.randint(0, 3000))
        for ordem, nome in enumerate(rng.sample(nomes, rng.randint(1, 3)), start=1):
            etapa = _etapa(db, d, ordem, nome)
            _dep_etapa(db, etapa, rng.choice(deps))
            exec_etapa = 0
            for ciclo in range(rng.randint(1, 3)):
                for status in ("em_execucao", "pausada"):
                    duracao = timedelta(minutes=rng.randint(10, 900))
                    _intervalo(db, d, status, cursor, cursor + duracao, etapa=etapa)
                    if status == "em_execucao":
                        recorte = max(timedelta(0), min(cursor + duracao, fim) - max(cursor, inicio))
                        exec_etapa += int(recorte.total_seconds())
                    cursor += duracao
            registro = esperado[nome]
            if exec_etapa > 0:
                registro["n_exec"] += 1
                registro["total_exec"] += exec_etapa
                registro["maior_exec"] = max(registro["maior_exec"], exec_etapa)
        _intervalo(db, d, "pausada", cursor)
    return esperado


def test_volume_logico_agregacao_bate_com_calculo_independente(client_admin, db_session, empresa, outra_empresa) -> None:
    esperado = _popular_volume(db_session, empresa, demandas=120, semente=7)
    _popular_volume(db_session, outra_empresa, demandas=60, semente=99)  # a OUTRA empresa não pode interferir
    corpo = _get(client_admin, "gargalos", inicio=_iso(_t(10, 0)), fim=_iso(_t(14, 0)), limite=200).json()
    achado = {e["etapaNome"]: e for e in corpo["etapas"]}
    for nome, exp in esperado.items():
        if exp["n_exec"] == 0:
            continue
        linha = achado[nome]
        assert linha["nExecucao"] == exp["n_exec"], nome
        assert linha["tempoExecucaoTotalSegundos"] == exp["total_exec"], nome
        assert linha["tempoExecucaoMaiorSegundos"] == exp["maior_exec"], nome
        assert linha["tempoExecucaoMedioSegundos"] == exp["total_exec"] // exp["n_exec"], nome


def _em_execucao_extras(db: Session, empresa: Empresa, quantidade: int) -> None:
    """Demandas em execução COM etapa, responsável e departamento — para o AGORA exercitar as consultas auxiliares (uma por tipo, nunca uma por linha)."""
    departamento = _departamento(db, empresa)
    for n in range(quantidade):
        d = _demanda(db, empresa, prazo=AGORA - timedelta(hours=n))
        etapa = _etapa(db, d, 1, "Redacao")
        _resp_etapa(db, etapa, _usuario(db, empresa))
        _dep_etapa(db, etapa, departamento)
        _intervalo(db, d, "em_execucao", AGORA - timedelta(hours=n + 1), etapa=etapa)
    for n in range(quantidade):  # e algumas SEM etapa (responsáveis da Demanda)
        d = _demanda(db, empresa)
        _resp_demanda(db, d, _usuario(db, empresa))
        _intervalo(db, d, "em_execucao", AGORA - timedelta(hours=n + 1))


def test_numero_de_queries_nao_cresce_com_o_volume(client_admin, db_session, empresa) -> None:
    _popular_volume(db_session, empresa, demandas=5, semente=1)
    _em_execucao_extras(db_session, empresa, 2)
    _get(client_admin, "agora")  # aquece o cache da regra de expediente / autenticação
    pequeno = (_contar_queries(db_session, lambda: _get(client_admin, "agora")), _contar_queries(db_session, lambda: _get(client_admin, "gargalos", inicio=_iso(_t(10, 0)), fim=_iso(_t(14, 0)))))
    _popular_volume(db_session, empresa, demandas=150, semente=2)
    _em_execucao_extras(db_session, empresa, 20)
    grande = (_contar_queries(db_session, lambda: _get(client_admin, "agora")), _contar_queries(db_session, lambda: _get(client_admin, "gargalos", inicio=_iso(_t(10, 0)), fim=_iso(_t(14, 0)))))
    assert pequeno == grande  # sem N+1: o mesmo número de consultas com 5 ou 155 Demandas
    assert grande[0] <= 8 and grande[1] <= 8  # teto documentado: AGORA = 6 de métricas, GARGALOS = 5, mais autenticação/permissão
