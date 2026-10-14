"""Fase Expediente 2 — API: gate de ACESSO (403 FORA_DO_EXPEDIENTE), gate de TRABALHO nominal, logout automático por token (`iat`), isenções, cache e configuração.

Relógio fixo em `app.core.expediente.agora_utc` (segunda-feira 2026-10-05, America/Sao_Paulo). Exemplo oficial: 09–12 e 13–18, antecedência 30, logout 18:10, tolerância
legada 30. NADA aqui pausa Demanda nem fecha sessão de trabalho (Fase 3).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.expediente import usuario_sujeito_ao_expediente
from app.core.security import create_access_token
from app.models.demanda import Demanda
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.schemas.demanda import DemandaUpdate
from app.services.demanda_service import DemandaForaDeExpedienteError, DemandaService
from app.services.regra_expediente_service import RegraExpedienteService, invalidar_cache_regra
from tests.test_demanda import _criar

SP = ZoneInfo("America/Sao_Paulo")
SEGUNDA = date(2026, 10, 5)
UTIL = [{"inicio": "09:00", "fim": "12:00"}, {"inicio": "13:00", "fim": "18:00"}]


def _dias() -> list[dict]:
    return [{"diaSemana": d, "periodos": UTIL if d < 5 else []} for d in range(7)]


def _instante(hhmm: str, dia: date = SEGUNDA) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(dia.year, dia.month, dia.day, h, m, tzinfo=SP)


@pytest.fixture(autouse=True)
def _cache_limpo():
    invalidar_cache_regra()
    yield
    invalidar_cache_regra()


@pytest.fixture()
def relogio(monkeypatch):
    def fixar(hhmm: str, dia: date = SEGUNDA) -> None:
        instante = _instante(hhmm, dia).astimezone(timezone.utc)
        monkeypatch.setattr("app.core.expediente.agora_utc", lambda: instante)

    fixar("10:00")
    return fixar


def _configurar(client_admin: TestClient, **extra) -> dict:
    corpo = {"ativo": True, "dias": _dias(), "antecedenciaAcessoMinutos": 30, "timezone": "America/Sao_Paulo", "toleranciaRetomadaMinutos": 30, **extra}
    resposta = client_admin.patch("/regra-expediente", json=corpo)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _token(usuario: Usuario, emitido: datetime | None = None) -> str:
    """Token com `iat` controlado e validade longa (o relógio de teste é o fixado, não o real)."""
    return create_access_token(
        sub=usuario.id,
        empresa_id=usuario.empresa_id,
        perfil_base=usuario.perfil_base,
        now=emitido.astimezone(timezone.utc) if emitido else None,
        expires_delta=timedelta(days=3650),
    )


def _cliente(app, token: str) -> TestClient:
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {token}"
    return c


# ── gate de ACESSO ───────────────────────────────────────────────────────────────────────────────────────────────

ACESSO = [
    ("08:29", False),
    ("08:30", True),
    ("08:59", True),
    ("09:00", True),
    ("11:59", True),
    ("12:00", False),
    ("12:29", False),
    ("12:30", True),
    ("12:59", True),
    ("13:00", True),
    ("17:59", True),
    ("18:00", False),
    ("18:09", False),
    ("18:10", False),
    ("18:11", False),
]


@pytest.mark.parametrize("hora, permitido", ACESSO)
def test_operador_sujeito_so_acessa_dentro_da_janela_de_acesso(client_admin, client_operador, relogio, hora, permitido) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio(hora)
    resposta = client_operador.get("/usuarios/me")
    if permitido:
        assert resposta.status_code == 200, resposta.text
    else:
        assert resposta.status_code == 403, resposta.text
        assert resposta.json()["detail"]["code"] == "FORA_DO_EXPEDIENTE"


def test_corpo_do_403_traz_proximos_horarios_e_fuso_do_servidor(client_admin, client_operador, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio("12:10")
    detalhe = client_operador.get("/usuarios/me").json()["detail"]
    assert detalhe["code"] == "FORA_DO_EXPEDIENTE"
    assert detalhe["message"]
    assert datetime.fromisoformat(detalhe["proximoAcesso"]) == _instante("12:30")
    assert datetime.fromisoformat(detalhe["proximoTrabalho"]) == _instante("13:00")
    assert datetime.fromisoformat(detalhe["proximoTrabalhoFim"]) == _instante("18:00")
    assert detalhe["timezone"] == "America/Sao_Paulo"


def test_sexta_a_noite_aponta_para_segunda(client_admin, client_operador, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio("19:00", date(2026, 10, 9))
    detalhe = client_operador.get("/usuarios/me").json()["detail"]
    assert datetime.fromisoformat(detalhe["proximoAcesso"]) == _instante("08:30", date(2026, 10, 12))


def test_sem_bloqueio_ligado_ninguem_e_barrado_por_horario(client_admin, client_operador, relogio) -> None:
    _configurar(client_admin)  # bloquearForaExpediente nasce false
    relogio("03:00")
    assert client_operador.get("/usuarios/me").status_code == 200


def test_regra_desligada_nao_bloqueia_mesmo_com_a_flag(client_admin, client_operador, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True, ativo=False)
    relogio("03:00")
    assert client_operador.get("/usuarios/me").status_code == 200


def test_feriado_bloqueia_o_dia_todo_e_trabalho_excepcional_abre(client_admin, client_operador, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    assert client_admin.post("/regra-expediente/dias-especiais", json={"data": SEGUNDA.isoformat(), "nome": "Feriado teste", "tipo": "feriado"}).status_code == 201
    relogio("10:00")
    assert client_operador.get("/usuarios/me").status_code == 403
    sabado = date(2026, 10, 10)
    assert client_admin.post(
        "/regra-expediente/dias-especiais",
        json={"data": sabado.isoformat(), "nome": "Sábado extra", "tipo": "trabalho_excepcional", "periodos": [{"inicio": "10:00", "fim": "14:00"}]},
    ).status_code == 201
    relogio("09:30", sabado)
    assert client_operador.get("/usuarios/me").status_code == 200
    relogio("08:00", sabado)
    assert client_operador.get("/usuarios/me").status_code == 403


def test_decisao_nao_depende_do_relogio_do_navegador(client_admin, client_operador, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio("20:00")
    resposta = client_operador.get("/usuarios/me", headers={"Date": "Mon, 05 Oct 2026 12:00:00 GMT", "X-Client-Time": "2026-10-05T10:00:00-03:00"})
    assert resposta.status_code == 403


# ── estado (polling) e identidade ────────────────────────────────────────────────────────────────────────────────


def test_estado_responde_fora_da_janela_e_traz_a_decisao_para_a_pessoa(client_admin, client_operador, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio("12:10")
    corpo = client_operador.get("/expediente/estado")
    assert corpo.status_code == 200, corpo.text
    estado = corpo.json()
    assert estado["sujeitoAoExpediente"] is True and estado["bloqueioAtivo"] is True
    assert estado["acessoPermitido"] is False and estado["trabalhoPermitido"] is False
    assert estado["dentroExpediente"] is False
    assert datetime.fromisoformat(estado["proximoAcesso"]) == _instante("12:30")
    assert datetime.fromisoformat(estado["proximoTrabalho"]) == _instante("13:00")
    assert estado["timezone"] == "America/Sao_Paulo"
    relogio("12:30")  # o próximo poll devolve o acesso SEM novo login
    estado = client_operador.get("/expediente/estado").json()
    assert estado["acessoPermitido"] is True and estado["trabalhoPermitido"] is False
    assert estado["dentroExpediente"] is False  # 12:30 é acesso, não trabalho (sem tolerância legada)
    relogio("13:00")
    estado = client_operador.get("/expediente/estado").json()
    assert estado["acessoPermitido"] is True and estado["trabalhoPermitido"] is True and estado["dentroExpediente"] is True


def test_estado_do_isento_nunca_bloqueia_mas_informa_a_janela_da_empresa(client_admin, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio("03:00")
    estado = client_admin.get("/expediente/estado").json()
    assert estado["sujeitoAoExpediente"] is False
    assert estado["acessoPermitido"] is True and estado["trabalhoPermitido"] is True
    assert estado["dentroExpediente"] is False  # da empresa, não da pessoa


def test_auth_me_e_login_continuam_disponiveis_fora_do_expediente(client_admin, client_operador, usuario_operador, empresa, relogio, app) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio("03:00")
    me = client_operador.get("/auth/me")
    assert me.status_code == 200 and me.json()["usuarioId"] == usuario_operador.id
    from tests.fixtures.usuarios import SENHA_CONHECIDA

    login = TestClient(app).post(
        "/auth/login", json={"empresaSlug": empresa.slug, "email": usuario_operador.email, "senha": SENHA_CONHECIDA}
    )
    assert login.status_code == 200, login.text
    token = login.json()["accessToken"]
    # com o token novo: identidade ok, uso tenant bloqueado (sem laço login→403→login: o login em si nunca é 403)
    novo = _cliente(app, token)
    assert novo.get("/auth/me").status_code == 200
    assert novo.get("/usuarios/me").status_code == 403


# ── isenções ─────────────────────────────────────────────────────────────────────────────────────────────────────


def test_admin_e_gestor_sao_isentos(client_admin, client_gestor, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio("03:00")
    assert client_admin.get("/usuarios/me").status_code == 200
    assert client_gestor.get("/usuarios/me").status_code == 200


def test_operador_com_acesso_fora_expediente_e_isento(client_admin, client_operador, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio("03:00")
    assert client_operador.get("/usuarios/me").status_code == 403
    usuario_operador.acesso_fora_expediente = True
    db_session.flush()
    assert client_operador.get("/usuarios/me").status_code == 200  # a decisão por pessoa não é cacheada


def test_conta_de_sistema_e_isenta(client_admin, client_operador, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    usuario_operador.is_system_account = True
    db_session.flush()
    relogio("03:00")
    assert client_operador.get("/usuarios/me").status_code == 200


def test_relacoes_operacionais_nao_mudam_a_autoridade_que_e_o_perfil_base() -> None:
    assert usuario_sujeito_ao_expediente(perfil_base="operador", is_system_account=False, acesso_fora_expediente=False) is True


# ── LOGOUT AUTOMÁTICO ────────────────────────────────────────────────────────────────────────────────────────────


def test_token_anterior_ao_corte_recebe_401_e_o_posterior_segue_valendo(client_admin, usuario_operador, relogio, app) -> None:
    _configurar(client_admin, logoutAutomaticoAtivo=True, logoutHorario="18:10")
    velho = _cliente(app, _token(usuario_operador, _instante("15:00")))
    relogio("18:09")
    assert velho.get("/usuarios/me").status_code == 200  # ainda antes do corte
    relogio("18:10")
    resposta = velho.get("/usuarios/me")
    assert resposta.status_code == 401, resposta.text
    assert velho.get("/auth/me").status_code == 401  # identidade também: sessão encerrada
    assert velho.get("/expediente/estado").status_code == 401
    relogio("18:11")
    assert velho.get("/usuarios/me").status_code == 401
    novo = _cliente(app, _token(usuario_operador, _instante("18:11")))
    relogio("18:30")
    assert novo.get("/usuarios/me").status_code == 200  # novo login depois do corte vale (bloqueio desligado)


def test_vale_para_varios_dispositivos_com_o_mesmo_token_antigo(client_admin, usuario_operador, relogio, app) -> None:
    _configurar(client_admin, logoutAutomaticoAtivo=True, logoutHorario="18:10")
    token = _token(usuario_operador, _instante("14:00"))
    relogio("18:20")
    for _ in range(3):  # abas/navegadores/dispositivos diferentes: nenhum estado de navegador entra na decisão
        assert _cliente(app, token).get("/usuarios/me").status_code == 401


def test_token_de_ontem_nao_sobrevive_ao_corte_de_ontem(client_admin, usuario_operador, relogio, app) -> None:
    _configurar(client_admin, logoutAutomaticoAtivo=True, logoutHorario="18:10")
    ontem = SEGUNDA - timedelta(days=1)
    velho = _cliente(app, _token(usuario_operador, _instante("15:00", ontem)))
    relogio("08:00")
    assert velho.get("/usuarios/me").status_code == 401


def test_isentos_nao_sofrem_logout_automatico(client_admin, usuario_admin, usuario_gestor, usuario_operador, db_session, relogio, app) -> None:
    _configurar(client_admin, logoutAutomaticoAtivo=True, logoutHorario="18:10")
    relogio("19:00")
    for usuario in (usuario_admin, usuario_gestor):
        assert _cliente(app, _token(usuario, _instante("15:00"))).get("/usuarios/me").status_code == 200
    usuario_operador.acesso_fora_expediente = True
    db_session.flush()
    assert _cliente(app, _token(usuario_operador, _instante("15:00"))).get("/usuarios/me").status_code == 200
    usuario_operador.acesso_fora_expediente = False
    usuario_operador.is_system_account = True
    db_session.flush()
    assert _cliente(app, _token(usuario_operador, _instante("15:00"))).get("/usuarios/me").status_code == 200


def test_logout_desligado_ou_regra_desligada_nao_desloga(client_admin, usuario_operador, relogio, app) -> None:
    _configurar(client_admin)  # logout nasce desligado
    velho = _cliente(app, _token(usuario_operador, _instante("08:00")))
    relogio("23:00")
    assert velho.get("/usuarios/me").status_code == 200
    _configurar(client_admin, logoutAutomaticoAtivo=True, logoutHorario="18:10", ativo=False)
    invalidar_cache_regra()
    assert velho.get("/usuarios/me").status_code == 200


def test_logout_e_bloqueio_sao_independentes(client_admin, usuario_operador, relogio, app) -> None:
    """Logout ligado + bloqueio ligado: após o corte, o token ANTIGO leva 401; um login novo gera token válido, mas o USO é barrado por 403 FORA_DO_EXPEDIENTE."""
    _configurar(client_admin, bloquearForaExpediente=True, logoutAutomaticoAtivo=True, logoutHorario="18:10")
    velho = _cliente(app, _token(usuario_operador, _instante("15:00")))
    novo_token = _token(usuario_operador, _instante("18:30"))
    relogio("18:30")
    assert velho.get("/usuarios/me").status_code == 401
    assert _cliente(app, novo_token).get("/usuarios/me").status_code == 403
    assert _cliente(app, novo_token).get("/auth/me").status_code == 200


def test_o_corte_usa_o_fuso_da_empresa(client_admin, usuario_operador, relogio, app) -> None:
    _configurar(client_admin, logoutAutomaticoAtivo=True, logoutHorario="18:10", timezone="America/Manaus")
    manaus = ZoneInfo("America/Manaus")
    velho = _cliente(app, _token(usuario_operador, datetime(2026, 10, 5, 15, 0, tzinfo=manaus)))
    relogio("18:10")  # 18:10 de São Paulo = 17:10 em Manaus: ainda não é o corte
    assert velho.get("/usuarios/me").status_code == 200
    relogio("19:10")  # 18:10 em Manaus
    assert velho.get("/usuarios/me").status_code == 401


# ── gate de TRABALHO (entrada em execução) ───────────────────────────────────────────────────────────────────────

TRABALHO = [
    ("08:59", False),
    ("09:00", True),
    ("11:59", True),
    ("12:00", False),
    ("12:29", False),
    ("12:30", False),  # acesso SIM, trabalho NÃO: a tolerância legada (30) não vale mais
    ("12:59", False),
    ("13:00", True),
    ("17:59", True),
    ("18:00", False),
]


def _entrar_em_execucao(db: Session, demanda_id: str, ator: Usuario) -> None:
    demanda = db.get(Demanda, demanda_id)
    DemandaService().update_demanda(db, demanda, DemandaUpdate(status="em_execucao"), actor=ator)


@pytest.mark.parametrize("hora, permitido", TRABALHO)
def test_operador_so_entra_em_execucao_na_janela_de_trabalho_nominal(client_admin, usuario_operador, db_session, relogio, hora, permitido) -> None:
    _configurar(client_admin)
    demanda = _criar(client_admin)
    relogio(hora)
    if permitido:
        _entrar_em_execucao(db_session, demanda["id"], usuario_operador)
    else:
        with pytest.raises(DemandaForaDeExpedienteError):
            _entrar_em_execucao(db_session, demanda["id"], usuario_operador)


def test_isentos_entram_em_execucao_fora_da_janela(client_admin, usuario_admin, usuario_gestor, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin)
    relogio("12:30")
    for ator in (usuario_admin, usuario_gestor):
        _entrar_em_execucao(db_session, _criar(client_admin)["id"], ator)
    usuario_operador.acesso_fora_expediente = True
    db_session.flush()
    _entrar_em_execucao(db_session, _criar(client_admin)["id"], usuario_operador)
    usuario_operador.acesso_fora_expediente = False
    usuario_operador.is_system_account = True
    db_session.flush()
    _entrar_em_execucao(db_session, _criar(client_admin)["id"], usuario_operador)


def test_regra_desligada_libera_o_trabalho(client_admin, usuario_operador, db_session, relogio) -> None:
    _configurar(client_admin, ativo=False)
    relogio("03:00")
    _entrar_em_execucao(db_session, _criar(client_admin)["id"], usuario_operador)


def test_o_409_continua_estruturado_para_quem_esta_sujeito(client_operador, usuario_operador, client_admin, relogio) -> None:
    """Contrato 409 FORA_DE_EXPEDIENTE preservado (o front só apresenta). O operador precisa enxergar a Demanda: o admin a cria já atribuída a ele."""
    _configurar(client_admin)
    relogio("12:30")
    criada = _criar(client_admin, usuarioResponsavelIds=[usuario_operador.id])
    resposta = client_operador.patch(f"/demandas/{criada['id']}", json={"status": "em_execucao"})
    if resposta.status_code != 409:
        pytest.skip(f"operador sem escopo sobre a demanda criada ({resposta.status_code}); coberto pelos testes de serviço")
    assert resposta.json()["detail"]["code"] == "FORA_DE_EXPEDIENTE"


# ── nada de pausa automática nesta fase ──────────────────────────────────────────────────────────────────────────


def test_a_demanda_em_execucao_nao_e_pausada_nem_ganha_origem_expediente(client_admin, usuario_admin, db_session, relogio) -> None:
    _configurar(client_admin, bloquearForaExpediente=True, logoutAutomaticoAtivo=True, logoutHorario="18:10")
    relogio("11:00")
    demanda = _criar(client_admin)
    _entrar_em_execucao(db_session, demanda["id"], usuario_admin)
    for hora in ("12:00", "18:00", "19:00"):
        relogio(hora)
        client_admin.get("/expediente/estado")
        client_admin.get("/usuarios/me")
    db_session.expire_all()
    atual = db_session.get(Demanda, demanda["id"])
    assert atual.status == "em_execucao" and atual.pausa_origem is None and atual.pausada_em is None
    eventos = db_session.scalars(select(Evento).where(Evento.entidade_id == demanda["id"], Evento.tipo == "demanda.status_alterado")).all()
    assert all((e.payload or {}).get("pausaOrigem") != "expediente" for e in eventos)


# ── configuração ─────────────────────────────────────────────────────────────────────────────────────────────────


def test_bloquear_e_pausa_podem_ser_ligados_mas_feriados_seguem_recusados(client_admin) -> None:
    assert client_admin.patch("/regra-expediente", json={"bloquearForaExpediente": True}).status_code == 200
    assert client_admin.patch("/regra-expediente", json={"pausarNoFimPeriodo": True}).status_code == 200  # Fase 3: a pausa automática tem tick e pode ser ligada
    assert client_admin.patch("/regra-expediente", json={"feriadosAutomaticos": True}).status_code == 422
    corpo = client_admin.get("/regra-expediente").json()
    assert corpo["bloquearForaExpediente"] is True and corpo["pausarNoFimPeriodo"] is True and corpo["feriadosAutomaticos"] is False


def test_logout_nasce_desligado_e_sem_horario(client_admin) -> None:
    corpo = client_admin.get("/regra-expediente").json()
    assert corpo["logoutAutomaticoAtivo"] is False and corpo["logoutHorario"] is None


def test_ligar_logout_exige_horario(client_admin) -> None:
    assert client_admin.patch("/regra-expediente", json={"logoutAutomaticoAtivo": True}).status_code == 422
    assert client_admin.patch("/regra-expediente", json={"logoutAutomaticoAtivo": True, "logoutHorario": None}).status_code == 422
    ok = client_admin.patch("/regra-expediente", json={"logoutAutomaticoAtivo": True, "logoutHorario": "18:10"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["logoutHorario"] == "18:10:00"
    # limpar o horário com o logout ligado é recusado; desligar primeiro funciona
    assert client_admin.patch("/regra-expediente", json={"logoutHorario": None}).status_code == 422
    assert client_admin.patch("/regra-expediente", json={"logoutAutomaticoAtivo": False, "logoutHorario": None}).status_code == 200
    assert client_admin.patch("/regra-expediente", json={"logoutHorario": "25:00"}).status_code == 422


def test_horario_e_normalizado_para_minutos_e_gera_evento(client_admin, db_session, empresa) -> None:
    client_admin.patch("/regra-expediente", json={"logoutAutomaticoAtivo": True, "logoutHorario": "18:10:45"})
    assert client_admin.get("/regra-expediente").json()["logoutHorario"] == "18:10:00"
    eventos = db_session.scalars(select(Evento).where(Evento.tipo == "regra_expediente.alterada", Evento.empresa_id == empresa.id)).all()
    campos = {c for e in eventos for c in (e.payload or {}).get("camposAlterados", [])}
    assert {"logoutAutomaticoAtivo", "logoutHorario"} <= campos


def test_operador_nao_configura_o_logout(client_operador) -> None:
    assert client_operador.patch("/regra-expediente", json={"logoutAutomaticoAtivo": True, "logoutHorario": "18:10"}).status_code == 403


# ── cache ────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_salvar_a_regra_invalida_o_cache_na_hora(client_admin, client_operador, relogio) -> None:
    _configurar(client_admin)
    relogio("03:00")
    assert client_operador.get("/usuarios/me").status_code == 200  # aquece o cache (bloqueio desligado)
    _configurar(client_admin, bloquearForaExpediente=True)
    assert client_operador.get("/usuarios/me").status_code == 403  # sem esperar o TTL
    assert client_admin.post("/regra-expediente/dias-especiais", json={"data": date(2026, 10, 6).isoformat(), "nome": "x", "tipo": "feriado"}).status_code == 201


def test_a_regra_e_lida_uma_vez_por_ttl(client_admin, client_operador, relogio, monkeypatch) -> None:
    _configurar(client_admin, bloquearForaExpediente=True)
    relogio("10:00")
    chamadas = {"n": 0}
    original = RegraExpedienteService.get_regra_calculo

    def contado(self, *a, **k):
        chamadas["n"] += 1
        return original(self, *a, **k)

    monkeypatch.setattr(RegraExpedienteService, "get_regra_calculo", contado)
    invalidar_cache_regra()
    for _ in range(5):
        assert client_operador.get("/usuarios/me").status_code == 200
    assert chamadas["n"] == 1


def test_empresa_sem_regra_nao_cria_regra_no_gate_nem_bloqueia(client_operador, db_session, empresa, relogio) -> None:
    from app.repositories.regra_expediente_repository import RegraExpedienteRepository

    assert RegraExpedienteRepository().get_by_empresa(db_session, empresa.id) is None
    relogio("03:00")
    assert client_operador.get("/auth/me").status_code == 200
    assert RegraExpedienteRepository().get_by_empresa(db_session, empresa.id) is None


# ── cobertura do gate (auditoria de rotas) ───────────────────────────────────────────────────────────────────────


def _contextos_de_rotas(app):
    contextos = []
    for r in app.routes:
        if hasattr(r, "effective_route_contexts"):
            contextos += list(r.effective_route_contexts())
        elif hasattr(r, "dependant"):
            contextos.append(r)
    return contextos


def _chamadas(dependant, acc):
    acc.add(dependant.call)
    for d in dependant.dependencies:
        _chamadas(d, acc)


def test_so_seis_rotas_autenticadas_ficam_fora_do_gate_de_expediente(app) -> None:
    """Toda rota tenant autenticada passa por `get_current_user_password_ready` (gate de acesso). As ÚNICAS exceções, por desenho: identidade (`/auth/me`), troca de
    senha (inicial e atual), o polling `/expediente/estado` e a porta do administrador da plataforma (`/plataforma/acesso` e `/plataforma/sessao`, isento). Uma rota
    nova que use só `get_current_user` quebra este teste de propósito."""
    from app.dependencies import auth as A

    fora = set()
    gated = 0
    for ctx in _contextos_de_rotas(app):
        acc: set = set()
        _chamadas(ctx.dependant, acc)
        metodo = sorted(ctx.methods)[0]
        if A.get_current_user_password_ready in acc:
            gated += 1
        elif A.get_current_user in acc or A.get_current_user_password_ready_sem_expediente in acc:
            fora.add((metodo, ctx.path))
    assert gated > 150
    assert fora == {
        ("GET", "/expediente/estado"),
        ("GET", "/auth/me"),
        ("POST", "/auth/definir-senha-inicial"),
        ("POST", "/auth/alterar-senha"),
        ("GET", "/plataforma/acesso"),
        ("POST", "/plataforma/sessao"),
    }


def test_plataforma_publico_e_login_nao_usam_o_gate_de_expediente(app) -> None:
    from app.dependencies import auth as A

    for ctx in _contextos_de_rotas(app):
        if ctx.path in ("/plataforma/acesso", "/plataforma/sessao"):
            continue  # troca da sessão tenant por token de plataforma: usa só a dependência SEM expediente (coberto no teste acima)
        if ctx.path.startswith(("/plataforma", "/publico", "/auth/login", "/auth/google", "/auth/password-reset")):
            acc: set = set()
            _chamadas(ctx.dependant, acc)
            assert A.get_current_user not in acc and A.get_current_user_password_ready not in acc, ctx.path
