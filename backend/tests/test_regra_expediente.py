"""Testes de Regra de Expediente (Fase 2G.3) — singleton por Empresa, persistido, com dias
da semana. Mesmo padrão de test_tipo_tarefa.py/test_grupo_cliente.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.expediente import JanelaDia
from app.core.expediente import RegraExpediente as RegraExpedienteCalculo
from app.core.expediente import duracao_horas_dia, esta_dentro_expediente
from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.services.regra_expediente_service import RegraExpedienteService
from tests.fixtures.usuarios import _criar_usuario_com_credencial

DIAS_UTEIS_PADRAO = {0, 1, 2, 3, 4}  # segunda..sexta
DIAS_FOLGA_PADRAO = {5, 6}  # sábado, domingo


def _cliente_para_outra_empresa(
    app, db_session: Session, outra_empresa: Empresa, perfil_base: str = "admin"
) -> TestClient:
    """`app` é a fixture de conftest.py (get_db já trocado pela sessão transacional do
    teste) — nunca importar app.main.app direto, senão o cliente usa outra sessão e a
    Empresa/Usuario criados aqui ficam invisíveis pra ele (mesmo padrão de
    test_demanda_comentario.py::_client_para). Só flush, nunca commit — commit encerraria a
    transação que isola este teste dos demais."""
    usuario = _criar_usuario_com_credencial(
        db_session, empresa=outra_empresa, perfil_base=perfil_base, email_prefixo=perfil_base
    )
    db_session.flush()
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=perfil_base)
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


# --------------------------------------------------------------------------------------
# Inicialização / singleton
# --------------------------------------------------------------------------------------


def test_primeira_leitura_cria_regra_padrao(client_admin: TestClient) -> None:
    resposta = client_admin.get("/regra-expediente")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["ativo"] is True
    assert len(corpo["dias"]) == 7
    assert corpo["empresaId"]


def test_segunda_a_sexta_ativos_sabado_domingo_inativos_no_padrao(client_admin: TestClient) -> None:
    corpo = client_admin.get("/regra-expediente").json()
    por_dia = {dia["diaSemana"]: dia for dia in corpo["dias"]}
    for dia_semana in DIAS_UTEIS_PADRAO:
        assert por_dia[dia_semana]["ativo"] is True, f"dia {dia_semana} deveria ser útil"
        assert por_dia[dia_semana]["manhaInicio"] is not None
    for dia_semana in DIAS_FOLGA_PADRAO:
        assert por_dia[dia_semana]["ativo"] is False, f"dia {dia_semana} deveria ser folga"
        assert por_dia[dia_semana]["manhaInicio"] is None


def test_singleton_segunda_leitura_nao_duplica(client_admin: TestClient) -> None:
    primeira = client_admin.get("/regra-expediente").json()
    segunda = client_admin.get("/regra-expediente").json()
    assert primeira["id"] == segunda["id"]


def test_singleton_criacao_concorrente_nao_duplica(db_session: Session, empresa: Empresa) -> None:
    """Duas chamadas 'simultâneas' (sequenciais no teste, mas simulando a corrida) de
    get_ou_criar não podem produzir duas linhas — UNIQUE(empresa_id) + IntegrityError
    tratado."""
    service = RegraExpedienteService()
    primeira = service.get_ou_criar(db_session, empresa_id=empresa.id)
    segunda = service.get_ou_criar(db_session, empresa_id=empresa.id)
    assert primeira.id == segunda.id


def test_outra_empresa_tem_regra_independente(
    app, client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    minha = client_admin.get("/regra-expediente").json()

    cliente_outra = _cliente_para_outra_empresa(app, db_session, outra_empresa)
    da_outra = cliente_outra.get("/regra-expediente").json()

    assert minha["id"] != da_outra["id"]
    assert minha["empresaId"] != da_outra["empresaId"]


def test_editar_no_admin_nao_afeta_outra_empresa(
    app, client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    cliente_outra = _cliente_para_outra_empresa(app, db_session, outra_empresa)
    da_outra_antes = cliente_outra.get("/regra-expediente").json()

    resposta = client_admin.patch("/regra-expediente", json={"toleranciaRetomadaMinutos": 45})
    assert resposta.status_code == 200, resposta.text

    da_outra_depois = cliente_outra.get("/regra-expediente").json()
    assert da_outra_depois["toleranciaRetomadaMinutos"] == da_outra_antes["toleranciaRetomadaMinutos"]


# --------------------------------------------------------------------------------------
# RBAC
# --------------------------------------------------------------------------------------


def test_admin_le_e_edita(client_admin: TestClient) -> None:
    assert client_admin.get("/regra-expediente").status_code == 200
    resposta = client_admin.patch("/regra-expediente", json={"ativo": True})
    assert resposta.status_code == 200, resposta.text


def test_gestor_le_e_edita(client_gestor: TestClient) -> None:
    assert client_gestor.get("/regra-expediente").status_code == 200
    resposta = client_gestor.patch("/regra-expediente", json={"toleranciaRetomadaMinutos": 10})
    assert resposta.status_code == 200, resposta.text


def test_operador_nao_le_nem_edita(client_operador: TestClient) -> None:
    assert client_operador.get("/regra-expediente").status_code == 403
    assert client_operador.patch("/regra-expediente", json={"ativo": True}).status_code == 403


# --------------------------------------------------------------------------------------
# Edição — validação de janela
# --------------------------------------------------------------------------------------


def _dia_valido(dia_semana: int, **overrides) -> dict:
    base = {
        "diaSemana": dia_semana,
        "ativo": True,
        "manhaInicio": "09:00",
        "manhaFim": "12:00",
        "tardeInicio": "14:00",
        "tardeFim": "19:00",
    }
    base.update(overrides)
    return base


def _sete_dias(**overrides_por_dia) -> list[dict]:
    return [_dia_valido(dia, **overrides_por_dia.get(dia, {})) for dia in range(7)]


def test_editar_dias_valido(client_admin: TestClient) -> None:
    dias = _sete_dias()
    dias[5] = {"diaSemana": 5, "ativo": False}  # sábado de folga
    dias[6] = {"diaSemana": 6, "ativo": False}  # domingo de folga
    resposta = client_admin.patch("/regra-expediente", json={"dias": dias})
    assert resposta.status_code == 200, resposta.text
    por_dia = {dia["diaSemana"]: dia for dia in resposta.json()["dias"]}
    assert por_dia[5]["ativo"] is False
    assert por_dia[5]["manhaInicio"] is None


def test_janela_invalida_inicio_depois_do_fim_rejeitada(client_admin: TestClient) -> None:
    dias = _sete_dias()
    dias[0] = _dia_valido(0, manhaInicio="12:00", manhaFim="09:00")
    resposta = client_admin.patch("/regra-expediente", json={"dias": dias})
    assert resposta.status_code == 422, resposta.text


def test_sobreposicao_manha_tarde_rejeitada(client_admin: TestClient) -> None:
    dias = _sete_dias()
    dias[0] = _dia_valido(0, manhaFim="15:00", tardeInicio="14:00")  # manhã invade a tarde
    resposta = client_admin.patch("/regra-expediente", json={"dias": dias})
    assert resposta.status_code == 422, resposta.text


def test_dia_ativo_sem_janela_rejeitado(client_admin: TestClient) -> None:
    dias = _sete_dias()
    dias[0] = {"diaSemana": 0, "ativo": True}  # ativo mas sem horários
    resposta = client_admin.patch("/regra-expediente", json={"dias": dias})
    assert resposta.status_code == 422, resposta.text


def test_dias_incompletos_rejeitado(client_admin: TestClient) -> None:
    dias = _sete_dias()[:6]  # só 6 dias
    resposta = client_admin.patch("/regra-expediente", json={"dias": dias})
    assert resposta.status_code == 422, resposta.text


def test_tolerancia_negativa_rejeitada(client_admin: TestClient) -> None:
    resposta = client_admin.patch("/regra-expediente", json={"toleranciaRetomadaMinutos": -1})
    assert resposta.status_code == 422, resposta.text


def test_evento_alterada_publicado(client_admin: TestClient, db_session: Session) -> None:
    regra_antes = client_admin.get("/regra-expediente").json()
    resposta = client_admin.patch("/regra-expediente", json={"toleranciaRetomadaMinutos": 15})
    assert resposta.status_code == 200, resposta.text

    eventos = (
        db_session.query(Evento)
        .filter(Evento.entidade_tipo == "regra_expediente", Evento.entidade_id == regra_antes["id"])
        .all()
    )
    assert len(eventos) == 1
    assert eventos[0].tipo == "regra_expediente.alterada"
    assert "toleranciaRetomadaMinutos" in eventos[0].payload["camposAlterados"]


# --------------------------------------------------------------------------------------
# Cálculo puro — dentro/fora do expediente considerando dia da semana
# --------------------------------------------------------------------------------------


def _regra_padrao_calculo() -> RegraExpedienteCalculo:
    util = JanelaDia(ativo=True, manha_inicio="09:00", manha_fim="12:00", tarde_inicio="14:00", tarde_fim="19:00")
    folga = JanelaDia(ativo=False)
    return RegraExpedienteCalculo(
        ativo=True,
        tolerancia_retomada_minutos=0,
        dias={0: util, 1: util, 2: util, 3: util, 4: util, 5: folga, 6: folga},
    )


@pytest.mark.parametrize(
    ("descricao", "quando", "esperado"),
    [
        ("segunda dentro da manhã", datetime(2026, 8, 24, 10, 0), True),  # 2026-08-24 = segunda
        ("segunda no intervalo do almoço", datetime(2026, 8, 24, 12, 30), False),
        ("segunda dentro da tarde", datetime(2026, 8, 24, 15, 0), True),
        ("segunda antes do expediente", datetime(2026, 8, 24, 7, 0), False),
        ("segunda depois do expediente", datetime(2026, 8, 24, 20, 0), False),
        ("sábado 10h fora (dia inativo)", datetime(2026, 8, 22, 10, 0), False),  # 2026-08-22 = sábado
        ("domingo fora (dia inativo)", datetime(2026, 8, 23, 10, 0), False),  # 2026-08-23 = domingo
    ],
)
def test_esta_dentro_expediente_considerando_dia_da_semana(descricao, quando, esperado) -> None:
    assert esta_dentro_expediente(quando, regra=_regra_padrao_calculo()) is esperado, descricao


def test_regra_ativo_false_libera_qualquer_hora_mesmo_fim_de_semana() -> None:
    """Semântica preservada da fase anterior (não alterada nesta fase, ver item 16 da
    instrução): `ativo=False` desliga o portão inteiro, não representa 'sempre fora'."""
    regra = _regra_padrao_calculo()
    desativada = RegraExpedienteCalculo(ativo=False, tolerancia_retomada_minutos=0, dias=regra.dias)
    sabado_de_madrugada = datetime(2026, 8, 22, 3, 0)
    assert esta_dentro_expediente(sabado_de_madrugada, regra=desativada) is True


# --------------------------------------------------------------------------------------
# duracao_horas_dia — fonte real de `horasUteisHoje` (GET /expediente/estado). 0.0 é um
# resultado válido (dia sem expediente), não um erro — ver correção da rodada de
# revalidação: o consumidor (capacidadeAproximada no frontend) não pode confundir "0 real"
# com "sem dado ainda".
# --------------------------------------------------------------------------------------


def test_duracao_horas_dia_dia_util_retorna_horas_reais() -> None:
    dia = JanelaDia(ativo=True, manha_inicio="09:00", manha_fim="12:00", tarde_inicio="14:00", tarde_fim="19:00")
    assert duracao_horas_dia(dia) == 8.0  # 3h de manhã + 5h de tarde


def test_duracao_horas_dia_dia_inativo_retorna_zero_como_valor_real() -> None:
    """0.0 aqui significa "hoje não é dia útil" — não "erro" nem "sem dado". O controle de
    expediente pode estar `ativo=True` e ainda assim hoje ser sábado/domingo: a capacidade
    aproximada deve refletir 0h, não cair em nenhum padrão de 8h só porque bateu em zero."""
    assert duracao_horas_dia(JanelaDia(ativo=False)) == 0.0


def test_duracao_horas_dia_janela_incompleta_retorna_zero() -> None:
    """Defensivo: `ativo=True` mas com algum horário faltando não deveria acontecer (o CHECK
    do banco e a validação do schema impedem), mas se acontecer a função não deve inventar
    duração parcial — 0.0, o mesmo valor real de "sem expediente hoje"."""
    dia = JanelaDia(ativo=True, manha_inicio="09:00", manha_fim="12:00", tarde_inicio=None, tarde_fim=None)
    assert duracao_horas_dia(dia) == 0.0


# --------------------------------------------------------------------------------------
# GET /expediente/estado — leitura operacional
# --------------------------------------------------------------------------------------


def test_estado_operador_autenticado_pode_ler(client_operador: TestClient) -> None:
    resposta = client_operador.get("/expediente/estado")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert "ativo" in corpo
    assert "dentroExpediente" in corpo
    assert "agora" in corpo
    assert "toleranciaRetomadaMinutos" in corpo
    assert "horasUteisHoje" in corpo


def test_estado_sem_auth_401(client: TestClient) -> None:
    resposta = client.get("/expediente/estado")
    assert resposta.status_code == 401, resposta.text


def test_estado_usa_app_timezone_nao_utc(client_admin: TestClient) -> None:
    corpo = client_admin.get("/expediente/estado").json()
    agora = datetime.fromisoformat(corpo["agora"])
    assert agora.tzinfo is not None
    assert agora.utcoffset() != timezone.utc.utcoffset(None), (
        "esperado o offset de APP_TIMEZONE (America/Sao_Paulo por padrão), não UTC puro"
    )


def test_estado_reflete_empresa_do_usuario(
    app, client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    # Empresa do client_admin: regra padrão (segunda a sexta úteis).
    # Outra empresa: desativa a regra inteira (sempre "dentro").
    cliente_outra = _cliente_para_outra_empresa(app, db_session, outra_empresa)
    resposta_desativar = cliente_outra.patch("/regra-expediente", json={"ativo": False})
    assert resposta_desativar.status_code == 200, resposta_desativar.text

    estado_outra = cliente_outra.get("/expediente/estado").json()
    assert estado_outra["ativo"] is False
    assert estado_outra["dentroExpediente"] is True  # regra desativada -> sempre dentro

    # A empresa do client_admin não foi tocada — sua regra padrão continua ativa (o resultado
    # em si depende da hora real do teste, então só confirmamos que as duas respostas podem
    # divergir, i.e., não é a MESMA regra sendo lida).
    estado_admin = client_admin.get("/expediente/estado").json()
    minha_regra = client_admin.get("/regra-expediente").json()
    assert minha_regra["ativo"] is True
    assert estado_admin["toleranciaRetomadaMinutos"] == minha_regra["toleranciaRetomadaMinutos"]
