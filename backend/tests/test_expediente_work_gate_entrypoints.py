"""Gate de TRABALHO nos três caminhos que colocam uma Demanda em `em_execucao`: PATCH (update), POST (create já em execução) e restaurar (arquivada que estava em
execução). TODOS passam pela MESMA autoridade (`DemandaService._ensure_dentro_expediente`): janela de trabalho nominal, fuso da empresa, dias especiais e isenções
(gestor, admin, conta de sistema, `acesso_fora_expediente`). Recusa = o MESMO 409 FORA_DE_EXPEDIENTE de sempre, sem efeito colateral.

Relógio fixo: segunda-feira 2026-10-05 (09–12 / 13–18), via `app.core.expediente.agora_utc`.
"""

from __future__ import annotations

import inspect
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.schemas.demanda import DemandaCreate, DemandaUpdate
from app.services import demanda_service as modulo_demanda_service
from app.services.demanda_service import DemandaForaDeExpedienteError, DemandaService
from tests.test_demanda import _criar
from tests.test_expediente_fase2_api import SEGUNDA, _configurar, relogio  # noqa: F401  (fixture `relogio` reaproveitada)

DENTRO = "10:00"
FORA = "12:30"  # acesso SIM, trabalho NÃO (a tolerância legada não vale mais)


# ── os três caminhos, com o MESMO ator ───────────────────────────────────────────────────────────────────────────


def _update(db: Session, ator: Usuario, admin: Usuario, cliente_admin: TestClient) -> None:
    demanda = db.get(Demanda, _criar(cliente_admin)["id"])
    DemandaService().update_demanda(db, demanda, DemandaUpdate(status="em_execucao"), actor=ator)


def _create(db: Session, ator: Usuario, admin: Usuario, cliente_admin: TestClient) -> None:
    DemandaService().create_demanda(db, DemandaCreate(nome="Nasce em execução", status="em_execucao"), empresa_id=ator.empresa_id, actor=ator)


def _restore_com_relogio(db: Session, ator: Usuario, admin: Usuario, cliente_admin: TestClient, relogio, hora_do_teste: str) -> None:
    """Arquiva (por quem pode, dentro do horário) uma Demanda que ESTAVA em execução e tenta restaurá-la na hora do teste."""
    relogio(DENTRO)
    demanda = db.get(Demanda, _criar(cliente_admin, status="em_execucao")["id"])
    service = DemandaService()
    service.arquivar_demanda(db, demanda, motivo_arquivamento="teste", actor_usuario_id=admin.id)
    assert demanda.status == "arquivada" and demanda.status_anterior_arquivamento == "em_execucao"
    relogio(hora_do_teste)
    service.restaurar_demanda(db, demanda, actor=ator)


def _tentar(caminho: str, db, ator, admin, cliente_admin, relogio, hora: str) -> None:
    if caminho == "restore":
        _restore_com_relogio(db, ator, admin, cliente_admin, relogio, hora)
        return
    relogio(hora)
    {"update": _update, "create": _create}[caminho](db, ator, admin, cliente_admin)


CAMINHOS = ["update", "create", "restore"]


# ── matriz: operador dentro / fora / liberado, gestor, admin ─────────────────────────────────────────────────────


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_operador_dentro_da_janela_entra_em_execucao(caminho, client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    _tentar(caminho, db_session, usuario_operador, usuario_admin, client_admin, relogio, DENTRO)


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_operador_fora_da_janela_e_recusado_com_o_mesmo_erro(caminho, client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    with pytest.raises(DemandaForaDeExpedienteError) as erro:
        _tentar(caminho, db_session, usuario_operador, usuario_admin, client_admin, relogio, FORA)
    assert "Fora do expediente" in str(erro.value)


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_operador_liberado_entra_em_execucao_fora_da_janela(caminho, client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    usuario_operador.acesso_fora_expediente = True
    db_session.flush()
    _tentar(caminho, db_session, usuario_operador, usuario_admin, client_admin, relogio, FORA)


@pytest.mark.parametrize("caminho", CAMINHOS)
@pytest.mark.parametrize("perfil", ["gestor", "admin"])
def test_gestor_e_admin_sao_isentos(caminho, perfil, client_admin, usuario_admin, usuario_gestor, db_session, relogio) -> None:
    _configurar(client_admin)
    ator = usuario_gestor if perfil == "gestor" else usuario_admin
    _tentar(caminho, db_session, ator, usuario_admin, client_admin, relogio, FORA)


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_conta_de_sistema_e_isenta(caminho, client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    usuario_operador.is_system_account = True
    db_session.flush()
    _tentar(caminho, db_session, usuario_operador, usuario_admin, client_admin, relogio, FORA)


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_regra_desligada_libera(caminho, client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin, ativo=False)
    _tentar(caminho, db_session, usuario_operador, usuario_admin, client_admin, relogio, "03:00")


# ── dias especiais ───────────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_feriado_bloqueia_o_dia_todo_para_o_operador(caminho, client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    if caminho == "restore":
        # a demanda é criada e arquivada ANTES de o feriado existir (senão o admin isento também a criaria igual, mas o fluxo fica mais claro assim)
        relogio(DENTRO)
        demanda = db_session.get(Demanda, _criar(client_admin, status="em_execucao")["id"])
        DemandaService().arquivar_demanda(db_session, demanda, motivo_arquivamento="teste", actor_usuario_id=usuario_admin.id)
        assert client_admin.post("/regra-expediente/dias-especiais", json={"data": SEGUNDA.isoformat(), "nome": "Feriado", "tipo": "feriado"}).status_code == 201
        with pytest.raises(DemandaForaDeExpedienteError) as erro:
            DemandaService().restaurar_demanda(db_session, demanda, actor=usuario_operador)
        assert "hoje não é dia útil" in str(erro.value)
        return
    assert client_admin.post("/regra-expediente/dias-especiais", json={"data": SEGUNDA.isoformat(), "nome": "Feriado", "tipo": "feriado"}).status_code == 201
    with pytest.raises(DemandaForaDeExpedienteError) as erro:
        _tentar(caminho, db_session, usuario_operador, usuario_admin, client_admin, relogio, DENTRO)
    assert "hoje não é dia útil" in str(erro.value)


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_trabalho_excepcional_no_sabado_vale_nos_tres_caminhos(caminho, client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    sabado = date(2026, 10, 10)
    assert client_admin.post(
        "/regra-expediente/dias-especiais",
        json={"data": sabado.isoformat(), "nome": "Sábado extra", "tipo": "trabalho_excepcional", "periodos": [{"inicio": "10:00", "fim": "14:00"}]},
    ).status_code == 201
    if caminho == "restore":
        relogio("10:30", sabado)
        demanda = db_session.get(Demanda, _criar(client_admin, status="em_execucao")["id"])
        DemandaService().arquivar_demanda(db_session, demanda, motivo_arquivamento="teste", actor_usuario_id=usuario_admin.id)
        DemandaService().restaurar_demanda(db_session, demanda, actor=usuario_operador)  # dentro do período excepcional
        assert demanda.status == "em_execucao"
        relogio("15:00", sabado)  # depois do período: fechado de novo
        DemandaService().arquivar_demanda(db_session, demanda, motivo_arquivamento="teste", actor_usuario_id=usuario_admin.id)
        with pytest.raises(DemandaForaDeExpedienteError):
            DemandaService().restaurar_demanda(db_session, demanda, actor=usuario_operador)
        return
    relogio("10:30", sabado)
    {"update": _update, "create": _create}[caminho](db_session, usuario_operador, usuario_admin, client_admin)
    relogio("15:00", sabado)
    with pytest.raises(DemandaForaDeExpedienteError):
        {"update": _update, "create": _create}[caminho](db_session, usuario_operador, usuario_admin, client_admin)


# ── atomicidade ──────────────────────────────────────────────────────────────────────────────────────────────────


def _total(db: Session, modelo) -> int:
    return db.scalar(select(func.count()).select_from(modelo))


def test_create_recusado_nao_cria_nada_nem_queima_numero(client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    relogio(DENTRO)
    primeira = _criar(client_admin)
    demandas, eventos = _total(db_session, Demanda), _total(db_session, Evento)
    relogio(FORA)
    with pytest.raises(DemandaForaDeExpedienteError):
        _create(db_session, usuario_operador, usuario_admin, client_admin)
    assert _total(db_session, Demanda) == demandas  # nenhuma Demanda parcial
    assert _total(db_session, Evento) == eventos  # nenhum evento de criação
    relogio(DENTRO)
    seguinte = _criar(client_admin)
    assert seguinte["numeroOperacional"] == primeira["numeroOperacional"] + 1  # nenhum número foi queimado pela tentativa recusada
    assert seguinte["sequencialReferencia"] == primeira["sequencialReferencia"] + 1


def test_restore_recusado_nao_muda_nenhum_dado(client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    relogio(DENTRO)
    demanda = db_session.get(Demanda, _criar(client_admin, status="em_execucao")["id"])
    DemandaService().arquivar_demanda(db_session, demanda, motivo_arquivamento="duplicada", actor_usuario_id=usuario_admin.id)
    db_session.flush()
    antes = (demanda.status, demanda.status_anterior_arquivamento, demanda.arquivado_at, demanda.motivo_arquivamento, demanda.restaurado_at, demanda.updated_at)
    eventos = _total(db_session, Evento)
    relogio(FORA)
    with pytest.raises(DemandaForaDeExpedienteError):
        DemandaService().restaurar_demanda(db_session, demanda, actor=usuario_operador)
    db_session.refresh(demanda)
    assert (demanda.status, demanda.status_anterior_arquivamento, demanda.arquivado_at, demanda.motivo_arquivamento, demanda.restaurado_at, demanda.updated_at) == antes
    assert demanda.status == "arquivada"  # nunca restaurada em silêncio com outro status
    assert _total(db_session, Evento) == eventos  # nenhum `demanda.restaurada`
    # e depois, DENTRO da janela, a mesma restauração funciona
    relogio(DENTRO)
    DemandaService().restaurar_demanda(db_session, demanda, actor=usuario_operador)
    assert demanda.status == "em_execucao" and demanda.status_anterior_arquivamento is None


def test_restaurar_para_outro_status_continua_livre_a_qualquer_hora(client_admin, usuario_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    relogio(DENTRO)
    demanda = db_session.get(Demanda, _criar(client_admin, status="pausada")["id"])
    DemandaService().arquivar_demanda(db_session, demanda, motivo_arquivamento="x", actor_usuario_id=usuario_admin.id)
    relogio("03:00")
    DemandaService().restaurar_demanda(db_session, demanda, actor=usuario_operador)
    assert demanda.status == "pausada"


# ── contrato HTTP (o mesmo 409 estruturado) ──────────────────────────────────────────────────────────────────────


def _conceder_permissao_da_rota(app, caminho: str, metodo: str, usuario: Usuario):
    """O operador comum não tem a permissão de criar/arquivar por padrão (RBAC). Para provar o CONTRATO HTTP do gate de horário com um usuário sujeito, a dependência de
    permissão da rota é trocada por uma que devolve o próprio operador (as demais dependências — token, gate de acesso — continuam valendo)."""
    from app.api.routes import demandas as rotas

    rota = next(r for r in rotas.router.routes if hasattr(r, "dependant") and r.path == f"/demandas{caminho}" and metodo in r.methods)
    chamada = next(d.call for d in rota.dependant.dependencies if getattr(d, "name", "") == "current_user")
    app.dependency_overrides[chamada] = lambda: usuario
    return chamada


def test_post_demandas_em_execucao_fora_da_janela_devolve_o_409_estruturado(app, client_admin, client_operador, usuario_operador, relogio) -> None:
    _configurar(client_admin)
    chamada = _conceder_permissao_da_rota(app, "", "POST", usuario_operador)
    try:
        relogio(FORA)
        resposta = client_operador.post("/demandas", json={"nome": "Direto em execução", "status": "em_execucao"})
        assert resposta.status_code == 409, resposta.text
        detalhe = resposta.json()["detail"]
        assert detalhe["code"] == "FORA_DE_EXPEDIENTE"  # o MESMO código do PATCH — nenhum código novo para create/restore
        assert "manhaInicio" in detalhe["expediente"]
        # sem efeito colateral: nada foi criado
        # operador dentro da janela: cria
        relogio(DENTRO)
        assert client_operador.post("/demandas", json={"nome": "Direto em execução", "status": "em_execucao"}).status_code == 201
    finally:
        app.dependency_overrides.pop(chamada, None)
    # admin é isento: cria fora da janela
    relogio(FORA)
    assert client_admin.post("/demandas", json={"nome": "Admin direto", "status": "em_execucao"}).status_code == 201


def test_post_restaurar_devolve_o_409_estruturado_e_nada_muda(app, client_admin, client_operador, usuario_operador, relogio) -> None:
    _configurar(client_admin)
    relogio(DENTRO)
    criada = _criar(client_admin, status="em_execucao", usuarioResponsavelIds=[usuario_operador.id])  # no escopo do operador
    assert client_admin.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "teste"}).status_code == 200
    relogio(FORA)
    chamada = _conceder_permissao_da_rota(app, "/{demanda_id}/restaurar", "POST", usuario_operador)
    try:
        resposta = client_operador.post(f"/demandas/{criada['id']}/restaurar")
    finally:
        app.dependency_overrides.pop(chamada, None)
    assert resposta.status_code == 409, resposta.text
    assert resposta.json()["detail"]["code"] == "FORA_DE_EXPEDIENTE"
    assert client_admin.get(f"/demandas/{criada['id']}").json()["status"] == "arquivada"  # nada mudou
    # admin (isento) restaura fora da janela
    assert client_admin.post(f"/demandas/{criada['id']}/restaurar").status_code == 200


# ── autoridade única ─────────────────────────────────────────────────────────────────────────────────────────────


def test_so_existe_uma_autoridade_de_horario_para_entrar_em_execucao() -> None:
    """Create, update, restore e iniciar-trabalho (que valida B ANTES de pausar a Demanda anterior) chamam `_ensure_dentro_expediente`; nenhum deles decide horário por conta própria."""
    codigo = inspect.getsource(modulo_demanda_service.DemandaService)
    assert codigo.count("self._ensure_dentro_expediente(") == 4
    for metodo in ("create_demanda", "update_demanda", "restaurar_demanda", "iniciar_trabalho"):
        fonte = inspect.getsource(getattr(DemandaService, metodo))
        assert "_ensure_dentro_expediente(" in fonte, metodo
        assert "esta_dentro_janela_trabalho" not in fonte and "momento_local" not in fonte, metodo
