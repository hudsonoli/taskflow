"""D2-D3C1 — `GET /sessoes-trabalho/trafego/indicadores`: métricas de `TrafegoResumoCards` +
`TempoOperacionalCard` agregadas no servidor, sem o cap de 100 da listagem.

A semântica preservada é a que `TrafegoView` aplicava no cliente (`listSessoesTrabalho` +
`filterSessoes` + `buildResumo`). Por isso, além dos casos calculados à mão, há um teste de
PARIDADE que porta essas três funções para Python (`_referencia_cliente`) e compara o resultado
com o do servidor para várias combinações de filtros — a prova de que nada mudou na regra.
"""

from __future__ import annotations

import math
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.sessao_trabalho import SessaoTrabalho
from app.repositories.sessao_trabalho_repository import _ACENTOS_DESTINO, _ACENTOS_ORIGEM, _remove_acentos
from tests.helpers.api import get

PERIODO = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
DENTRO = PERIODO + timedelta(hours=1)  # encerrada que entra no período


def _url(periodo: datetime = PERIODO, **params: str | None) -> str:
    consulta = {"periodoInicio": periodo.isoformat().replace("+00:00", "Z")}
    consulta.update({chave: valor for chave, valor in params.items() if valor is not None})
    return "/sessoes-trabalho/trafego/indicadores?" + urlencode(consulta)


def _sessao(
    db: Session,
    empresa: Empresa,
    *,
    status: str = "encerrada",
    duracao: int = 0,
    inicio_em: datetime | None = None,
    usuario_id: str | None = None,
    departamento_id: str | None = None,
    demanda_id: str | None = None,
) -> SessaoTrabalho:
    agora = datetime.now(timezone.utc)
    encerrada = status == "encerrada"
    sessao = SessaoTrabalho(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        demanda_id=demanda_id or str(uuid.uuid4()),
        usuario_id=usuario_id,
        departamento_id=departamento_id,
        evento_inicio_id=str(uuid.uuid4()),
        evento_fim_id=str(uuid.uuid4()) if encerrada else None,
        status=status,
        created_at=agora,
        updated_at=agora,
        inicio_em=inicio_em if inicio_em is not None else (DENTRO if encerrada else agora),
        fim_em=agora if encerrada else None,
        duracao_segundos=duracao if encerrada else None,
    )
    db.add(sessao)
    db.flush()
    return sessao


def _usuario_id(db: Session, empresa: Empresa) -> str:
    from app.models.usuario import Usuario

    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"u-{sufixo}",
        nome=f"Usuário {sufixo}",
        email=f"u-{sufixo}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario.id


def _departamento_id(db: Session, empresa: Empresa) -> str:
    from app.models.departamento import Departamento

    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=f"Depto {sufixo}",
        nome_normalizado=f"depto-{sufixo}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento.id


def _criar_demanda(client: TestClient, nome: str) -> dict:
    resposta = client.post("/demandas", json={"nome": nome})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _indicadores(app, token: str, **params: str | None) -> dict:
    resposta = get(TestClient(app), _url(**params), token=token)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


ZERO = {
    "sessoesAtivas": 0,
    "sessoesEncerradas": 0,
    "demandasDistintas": 0,
    "usuariosDistintos": 0,
    "departamentosDistintos": 0,
    "tempoOperacionalEstimadoSegundos": 0,
    "tempoMedioSessaoSegundos": 0,
    "maiorSessaoSegundos": 0,
    "maiorSessaoAtivaSegundos": 0,
}


# --------------------------------------------------------------------------------------
# RBAC / tenant
# --------------------------------------------------------------------------------------

def test_admin_e_gestor_acessam(app, token_admin: str, token_gestor: str) -> None:
    assert get(TestClient(app), _url(), token=token_admin).status_code == 200
    assert get(TestClient(app), _url(), token=token_gestor).status_code == 200


def test_operador_e_403(app, token_operador: str) -> None:
    assert get(TestClient(app), _url(), token=token_operador).status_code == 403


def test_sem_token_e_401(app) -> None:
    assert get(TestClient(app), _url()).status_code == 401


def test_tenant_isolado(app, db_session: Session, outra_empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, outra_empresa, duracao=3600, usuario_id=_usuario_id(db_session, outra_empresa))
    _sessao(db_session, outra_empresa, status="ativa", inicio_em=datetime.now(timezone.utc) - timedelta(hours=1))
    assert _indicadores(app, token_admin) == ZERO


# --------------------------------------------------------------------------------------
# Métricas — casos calculados à mão
# --------------------------------------------------------------------------------------

def test_sem_sessoes_tudo_zero(app, token_admin: str) -> None:
    assert _indicadores(app, token_admin) == ZERO


def test_uma_encerrada(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    usuario, departamento = _usuario_id(db_session, empresa), _departamento_id(db_session, empresa)
    _sessao(db_session, empresa, duracao=3600, usuario_id=usuario, departamento_id=departamento)

    assert _indicadores(app, token_admin) == {
        "sessoesAtivas": 0,
        "sessoesEncerradas": 1,
        "demandasDistintas": 1,
        "usuariosDistintos": 1,
        "departamentosDistintos": 1,
        "tempoOperacionalEstimadoSegundos": 3600,
        "tempoMedioSessaoSegundos": 3600,
        "maiorSessaoSegundos": 3600,
        "maiorSessaoAtivaSegundos": 0,
    }


def test_uma_ativa_conta_o_tempo_decorrido(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, status="ativa", inicio_em=datetime.now(timezone.utc) - timedelta(seconds=600))

    corpo = _indicadores(app, token_admin)
    assert corpo["sessoesAtivas"] == 1
    assert corpo["sessoesEncerradas"] == 0
    # `NOW()` do Postgres congela no início da transação do teste (em produção cada requisição
    # tem a sua): o decorrido pode ficar alguns segundos abaixo — tolerância, não regra.
    assert 570 <= corpo["tempoOperacionalEstimadoSegundos"] <= 610
    assert corpo["tempoMedioSessaoSegundos"] == corpo["tempoOperacionalEstimadoSegundos"]
    assert corpo["maiorSessaoSegundos"] == corpo["maiorSessaoAtivaSegundos"] == corpo["tempoOperacionalEstimadoSegundos"]


def test_varias_sessoes_calculado_a_mao(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """u1/u2, d1/d2, demandas A/B. Encerradas: 600 + 1800 + 3000 = 5400. Ativa (u2/d2/B)
    iniciada há ~1000s. Distintos: demandas {A,B}=2, usuários {u1,u2}=2, departamentos {d1,d2}=2."""
    u1, u2 = _usuario_id(db_session, empresa), _usuario_id(db_session, empresa)
    d1, d2 = _departamento_id(db_session, empresa), _departamento_id(db_session, empresa)
    demanda_a, demanda_b = str(uuid.uuid4()), str(uuid.uuid4())
    _sessao(db_session, empresa, duracao=600, usuario_id=u1, departamento_id=d1, demanda_id=demanda_a)
    _sessao(db_session, empresa, duracao=1800, usuario_id=u1, departamento_id=d1, demanda_id=demanda_b)
    _sessao(db_session, empresa, duracao=3000, usuario_id=u2, departamento_id=d2, demanda_id=demanda_a)
    _sessao(
        db_session, empresa, status="ativa", usuario_id=u2, departamento_id=d2, demanda_id=demanda_b,
        inicio_em=datetime.now(timezone.utc) - timedelta(seconds=1000),
    )

    corpo = _indicadores(app, token_admin)
    assert corpo["sessoesAtivas"] == 1
    assert corpo["sessoesEncerradas"] == 3
    assert corpo["demandasDistintas"] == 2
    assert corpo["usuariosDistintos"] == 2
    assert corpo["departamentosDistintos"] == 2
    total = corpo["tempoOperacionalEstimadoSegundos"]
    assert 6370 <= total <= 6410  # 5400 + ~1000 (tolerância do NOW() da transação de teste)
    assert corpo["maiorSessaoSegundos"] == 3000  # a ativa (~1000) não supera a maior encerrada
    assert 970 <= corpo["maiorSessaoAtivaSegundos"] <= 1010
    assert corpo["tempoMedioSessaoSegundos"] == (2 * total + 4) // 8  # round(total / 4), meio sobe


def test_media_arredonda_meio_para_cima(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """(1 + 2) / 2 = 1.5 → 2, como `Math.round`."""
    _sessao(db_session, empresa, duracao=1)
    _sessao(db_session, empresa, duracao=2)
    assert _indicadores(app, token_admin)["tempoMedioSessaoSegundos"] == 2


def test_sessao_sem_usuario_nem_departamento_nao_entra_nos_distintos(
    app, db_session: Session, empresa: Empresa, token_admin: str
) -> None:
    _sessao(db_session, empresa, duracao=60)
    corpo = _indicadores(app, token_admin)
    assert corpo["usuariosDistintos"] == 0
    assert corpo["departamentosDistintos"] == 0
    assert corpo["demandasDistintas"] == 1


def test_cancelada_nunca_conta(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    cancelada = _sessao(db_session, empresa, status="ativa", inicio_em=DENTRO)
    cancelada.status = "cancelada"
    cancelada.duracao_segundos = 7200
    db_session.flush()
    assert _indicadores(app, token_admin) == ZERO


# --------------------------------------------------------------------------------------
# Período (mesma regra congelada de D3B)
# --------------------------------------------------------------------------------------

def test_periodo_encerrada_antes_nao_conta_boundary_conta(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, duracao=100, inicio_em=PERIODO - timedelta(seconds=1))
    _sessao(db_session, empresa, duracao=200, inicio_em=PERIODO)  # boundary: `>=`
    _sessao(db_session, empresa, duracao=400, inicio_em=PERIODO + timedelta(minutes=5))

    corpo = _indicadores(app, token_admin)
    assert corpo["sessoesEncerradas"] == 2
    assert corpo["tempoOperacionalEstimadoSegundos"] == 600


def test_periodo_encerrada_cruzando_inicio_nao_conta(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, duracao=3600, inicio_em=PERIODO - timedelta(minutes=30))
    assert _indicadores(app, token_admin) == ZERO


def test_periodo_ativa_antiga_conta_integralmente(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    agora = datetime.now(timezone.utc)
    _sessao(db_session, empresa, status="ativa", inicio_em=agora - timedelta(hours=3))

    resposta = get(TestClient(app), _url(periodo=agora - timedelta(hours=1)), token=token_admin)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["sessoesAtivas"] == 1
    assert 3 * 3600 - 30 <= corpo["tempoOperacionalEstimadoSegundos"] <= 3 * 3600 + 10


# --------------------------------------------------------------------------------------
# Filtros
# --------------------------------------------------------------------------------------

def test_filtro_usuario_unico_e_multiplos(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    u1, u2, u3 = (_usuario_id(db_session, empresa) for _ in range(3))
    _sessao(db_session, empresa, duracao=100, usuario_id=u1)
    _sessao(db_session, empresa, duracao=200, usuario_id=u2)
    _sessao(db_session, empresa, duracao=400, usuario_id=u3)
    _sessao(db_session, empresa, duracao=800)  # sem usuário: nunca casa com filtro de usuário ativo

    assert _indicadores(app, token_admin, usuarioIds=u1)["tempoOperacionalEstimadoSegundos"] == 100
    multi = _indicadores(app, token_admin, usuarioIds=f"{u1},{u3}")
    assert multi["sessoesEncerradas"] == 2
    assert multi["tempoOperacionalEstimadoSegundos"] == 500
    assert multi["usuariosDistintos"] == 2


def test_filtro_departamento_unico_e_multiplos(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    d1, d2, d3 = (_departamento_id(db_session, empresa) for _ in range(3))
    _sessao(db_session, empresa, duracao=100, departamento_id=d1)
    _sessao(db_session, empresa, duracao=200, departamento_id=d2)
    _sessao(db_session, empresa, duracao=400, departamento_id=d3)
    _sessao(db_session, empresa, duracao=800)

    assert _indicadores(app, token_admin, departamentoIds=d2)["tempoOperacionalEstimadoSegundos"] == 200
    multi = _indicadores(app, token_admin, departamentoIds=f"{d1},{d2}")
    assert multi["sessoesEncerradas"] == 2
    assert multi["departamentosDistintos"] == 2
    assert multi["tempoOperacionalEstimadoSegundos"] == 300


def test_status_ativa_exclui_encerradas(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, duracao=900)
    _sessao(db_session, empresa, status="ativa", inicio_em=datetime.now(timezone.utc) - timedelta(seconds=100))

    corpo = _indicadores(app, token_admin, status="ativa")
    assert corpo["sessoesAtivas"] == 1
    assert corpo["sessoesEncerradas"] == 0
    assert corpo["maiorSessaoSegundos"] < 900


def test_status_encerrada_mantem_as_ativas_semantica_atual(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """SEMÂNTICA ATUAL PRESERVADA, não "corrigida": no cliente as ativas eram buscadas sempre,
    então escolher status=encerrada nunca escondeu uma sessão ativa."""
    _sessao(db_session, empresa, duracao=900)
    _sessao(db_session, empresa, status="ativa", inicio_em=datetime.now(timezone.utc) - timedelta(seconds=100))

    corpo = _indicadores(app, token_admin, status="encerrada")
    assert corpo["sessoesAtivas"] == 1
    assert corpo["sessoesEncerradas"] == 1


def test_status_todos_traz_ambas(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, duracao=900)
    _sessao(db_session, empresa, status="ativa", inicio_em=datetime.now(timezone.utc) - timedelta(seconds=100))

    corpo = _indicadores(app, token_admin, status="todos")
    assert (corpo["sessoesAtivas"], corpo["sessoesEncerradas"]) == (1, 1)


# --------------------------------------------------------------------------------------
# demandaQuery — mesma busca do cliente: "<id> #<número> — <nome>", sem acento/caixa
# --------------------------------------------------------------------------------------

@pytest.fixture()
def demanda_acentuada(client_admin: TestClient) -> dict:
    return _criar_demanda(client_admin, "Campanha Inverno Ação")


def _com_sessao_na_demanda(db: Session, empresa: Empresa, demanda: dict, duracao: int = 100) -> None:
    _sessao(db, empresa, duracao=duracao, demanda_id=demanda["id"])
    _sessao(db, empresa, duracao=7)  # sessão de OUTRA demanda — nunca deve casar


@pytest.mark.parametrize(
    "consulta",
    [
        "inverno",                 # trecho do nome
        "INVERNO",                 # caixa
        "acao",                    # sem acento casa nome com acento
        "AÇÃO",                    # com acento e caixa casa o nome normalizado
        "campanha inverno",        # vários termos contíguos
        "—",                       # o separador também faz parte do texto casado
    ],
)
def test_demanda_query_por_nome(
    consulta: str, app, db_session: Session, empresa: Empresa, token_admin: str, demanda_acentuada: dict
) -> None:
    _com_sessao_na_demanda(db_session, empresa, demanda_acentuada)
    corpo = _indicadores(app, token_admin, demandaQuery=consulta)
    # `—` aparece em todas as demandas que EXISTEM; a sessão de demanda inexistente tem o id como nome
    esperado = 1
    assert corpo["sessoesEncerradas"] == esperado
    assert corpo["tempoOperacionalEstimadoSegundos"] == 100


def test_demanda_query_por_numero_operacional(app, db_session: Session, empresa: Empresa, token_admin: str, demanda_acentuada: dict) -> None:
    _com_sessao_na_demanda(db_session, empresa, demanda_acentuada)
    numero = demanda_acentuada["numeroOperacional"]
    assert _indicadores(app, token_admin, demandaQuery=f"#{numero}")["tempoOperacionalEstimadoSegundos"] == 100
    # atravessa o separador: "#<n> — campanha"
    assert _indicadores(app, token_admin, demandaQuery=f"#{numero} — campanha")["tempoOperacionalEstimadoSegundos"] == 100


def test_demanda_query_por_id_da_demanda_e_demanda_inexistente(
    app, db_session: Session, empresa: Empresa, token_admin: str
) -> None:
    """Sem Demanda correspondente o nome cai no próprio id (como `resolveTrafegoDemandaNome`):
    ainda casa pelo id, e não casa por nome nenhum."""
    demanda_id = str(uuid.uuid4())
    _sessao(db_session, empresa, duracao=50, demanda_id=demanda_id)
    _sessao(db_session, empresa, duracao=9)

    assert _indicadores(app, token_admin, demandaQuery=demanda_id[:13])["tempoOperacionalEstimadoSegundos"] == 50
    assert _indicadores(app, token_admin, demandaQuery="campanha") == ZERO


def test_demanda_query_sem_resultado_zera(app, db_session: Session, empresa: Empresa, token_admin: str, demanda_acentuada: dict) -> None:
    _com_sessao_na_demanda(db_session, empresa, demanda_acentuada)
    assert _indicadores(app, token_admin, demandaQuery="inexistente-zzz") == ZERO


def test_demanda_query_so_espacos_nao_filtra(app, db_session: Session, empresa: Empresa, token_admin: str, demanda_acentuada: dict) -> None:
    _com_sessao_na_demanda(db_session, empresa, demanda_acentuada)
    assert _indicadores(app, token_admin, demandaQuery="   ")["sessoesEncerradas"] == 2


def test_demanda_query_nao_e_aparada_para_casar(app, db_session: Session, empresa: Empresa, token_admin: str, demanda_acentuada: dict) -> None:
    """O cliente só usa `trim()` para decidir SE há filtro; o texto casado é o digitado, com
    espaços. "acao " (espaço no fim) não casa o nome que termina em "ação" — preservado."""
    _com_sessao_na_demanda(db_session, empresa, demanda_acentuada)
    assert _indicadores(app, token_admin, demandaQuery="acao")["sessoesEncerradas"] == 1
    assert _indicadores(app, token_admin, demandaQuery="acao ") == ZERO
    assert _indicadores(app, token_admin, demandaQuery=" inverno")["sessoesEncerradas"] == 1


def test_demanda_query_nao_cruza_tenant(app, db_session: Session, outra_empresa: Empresa, empresa: Empresa, token_admin: str, demanda_acentuada: dict) -> None:
    """Sessão da outra empresa com o id de uma Demanda desta empresa: a junção exige a mesma
    empresa, então o NOME dela não é usado (e a sessão nem entra no universo)."""
    _sessao(db_session, outra_empresa, duracao=70, demanda_id=demanda_acentuada["id"])
    assert _indicadores(app, token_admin, demandaQuery="inverno") == ZERO


def test_filtros_combinados(app, db_session: Session, empresa: Empresa, token_admin: str, demanda_acentuada: dict) -> None:
    u1, u2 = _usuario_id(db_session, empresa), _usuario_id(db_session, empresa)
    d1 = _departamento_id(db_session, empresa)
    _sessao(db_session, empresa, duracao=100, usuario_id=u1, departamento_id=d1, demanda_id=demanda_acentuada["id"])
    _sessao(db_session, empresa, duracao=200, usuario_id=u2, departamento_id=d1, demanda_id=demanda_acentuada["id"])
    _sessao(db_session, empresa, duracao=400, usuario_id=u1, departamento_id=d1)  # outra demanda
    _sessao(db_session, empresa, duracao=800, usuario_id=u1, departamento_id=d1, demanda_id=demanda_acentuada["id"],
            inicio_em=PERIODO - timedelta(days=1))  # fora do período

    corpo = _indicadores(app, token_admin, usuarioIds=u1, departamentoIds=d1, demandaQuery="inverno", status="encerrada")
    assert corpo["sessoesEncerradas"] == 1
    assert corpo["tempoOperacionalEstimadoSegundos"] == 100


# --------------------------------------------------------------------------------------
# Dataset > 100 — o que o cap de `limit=100` truncava
# --------------------------------------------------------------------------------------

def test_mais_de_100_encerradas_agregado_integral(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """130 encerradas de 1s..130s: soma = 130·131/2 = 8515, máx = 130, média = round(8515/130 =
    65.5) = 66, 130 demandas distintas. Truncar em 100 daria 5050/100/51 — outro número."""
    usuarios = [_usuario_id(db_session, empresa) for _ in range(3)]
    for i in range(1, 131):
        _sessao(db_session, empresa, duracao=i, usuario_id=usuarios[i % 3])

    corpo = _indicadores(app, token_admin)
    assert corpo["sessoesEncerradas"] == 130
    assert corpo["demandasDistintas"] == 130
    assert corpo["usuariosDistintos"] == 3
    assert corpo["tempoOperacionalEstimadoSegundos"] == 8515
    assert corpo["maiorSessaoSegundos"] == 130
    assert corpo["tempoMedioSessaoSegundos"] == 66


def test_mais_de_100_ativas_contadas(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    inicio = datetime.now(timezone.utc) - timedelta(seconds=60)
    for _ in range(105):
        _sessao(db_session, empresa, status="ativa", inicio_em=inicio)

    corpo = _indicadores(app, token_admin)
    assert corpo["sessoesAtivas"] == 105
    assert 105 * 30 <= corpo["tempoOperacionalEstimadoSegundos"] <= 105 * 70


def test_mais_de_100_com_filtro_de_usuario(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    alvo, outro = _usuario_id(db_session, empresa), _usuario_id(db_session, empresa)
    for _ in range(120):
        _sessao(db_session, empresa, duracao=10, usuario_id=alvo)
    for _ in range(30):
        _sessao(db_session, empresa, duracao=999, usuario_id=outro)

    corpo = _indicadores(app, token_admin, usuarioIds=alvo)
    assert corpo["sessoesEncerradas"] == 120
    assert corpo["tempoOperacionalEstimadoSegundos"] == 1200


# --------------------------------------------------------------------------------------
# Performance — uma consulta, sem materializar sessões
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("com_demanda_query", [False, True])
def test_uma_unica_consulta_a_sessoes(
    com_demanda_query: bool, app, db_session: Session, empresa: Empresa, token_admin: str
) -> None:
    for _ in range(6):
        _sessao(db_session, empresa, duracao=60, usuario_id=_usuario_id(db_session, empresa))

    chamadas: list[str] = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "sessoes_trabalho" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = get(
            TestClient(app),
            _url(demandaQuery="x" if com_demanda_query else None),
            token=token_admin,
        )
    finally:
        event.remove(engine, "before_cursor_execute", _contar)

    assert resposta.status_code == 200, resposta.text
    assert len(chamadas) == 1, f"esperada 1 consulta agregada, houve {len(chamadas)}"
    assert "COUNT(" in chamadas[0] and "LIMIT" not in chamadas[0].upper()


# --------------------------------------------------------------------------------------
# Validação
# --------------------------------------------------------------------------------------

def test_periodo_naive_e_422(app, token_admin: str) -> None:
    resposta = get(TestClient(app), "/sessoes-trabalho/trafego/indicadores?periodoInicio=2026-05-01T12:00:00", token=token_admin)
    assert resposta.status_code == 422, resposta.text


def test_periodo_ausente_e_422(app, token_admin: str) -> None:
    assert get(TestClient(app), "/sessoes-trabalho/trafego/indicadores", token=token_admin).status_code == 422


def test_status_invalido_e_422(app, token_admin: str) -> None:
    assert get(TestClient(app), _url(status="cancelada"), token=token_admin).status_code == 422


def test_usuario_ids_invalido_e_422(app, token_admin: str) -> None:
    assert get(TestClient(app), _url(usuarioIds="nao-e-uuid"), token=token_admin).status_code == 422
    assert get(TestClient(app), _url(departamentoIds=f"{uuid.uuid4()},xyz"), token=token_admin).status_code == 422


def test_csv_vazio_nao_filtra(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    _sessao(db_session, empresa, duracao=10)
    assert _indicadores(app, token_admin, usuarioIds=" , ,")["sessoesEncerradas"] == 1


# --------------------------------------------------------------------------------------
# Normalização de acentos (translate no SQL ≡ NFD do cliente)
# --------------------------------------------------------------------------------------

def test_mapa_de_acentos_bate_com_a_normalizacao_do_cliente() -> None:
    assert len(_ACENTOS_ORIGEM) == len(_ACENTOS_DESTINO) > 100
    for origem, destino in zip(_ACENTOS_ORIGEM, _ACENTOS_DESTINO):
        assert _remove_acentos(origem) == destino, f"{origem!r} → {destino!r}"
    assert _remove_acentos("AÇÃO São João — Ünïcode") == "acao sao joao — unicode"


# --------------------------------------------------------------------------------------
# PARIDADE com o cálculo que o cliente fazia (filterSessoes + buildResumo)
# --------------------------------------------------------------------------------------

def _normalizar_cliente(valor: str) -> str:
    """`normalize()` de lib/trafego.ts."""
    decomposto = unicodedata.normalize("NFD", valor.lower())
    return "".join(c for c in decomposto if not 0x300 <= ord(c) <= 0x36F)


def _referencia_cliente(sessoes: list[dict], filtros: dict, agora: datetime) -> dict:
    """Port literal de `filterSessoes` + `buildResumo` (frontend/src/lib/trafego.ts) aplicados
    ao universo que `TrafegoView.carregar` buscava (ativas sempre; encerradas só se
    status != "ativa" e inicio >= período)."""
    universo = [
        s for s in sessoes
        if s["status"] == "ativa"
        or (s["status"] == "encerrada" and filtros["status"] != "ativa" and s["inicio"] >= filtros["periodo"])
    ]

    def passa(s: dict) -> bool:
        usuario_ok = not filtros["usuarios"] or (s["usuario"] is not None and s["usuario"] in filtros["usuarios"])
        depto_ok = not filtros["departamentos"] or (s["departamento"] is not None and s["departamento"] in filtros["departamentos"])
        consulta = filtros["demanda_query"]
        demanda_ok = True
        if consulta.strip():
            nome = f"#{s['numero']} — {s['nome']}" if s["numero"] is not None else s["demanda"]
            demanda_ok = _normalizar_cliente(consulta) in _normalizar_cliente(f"{s['demanda']} {nome}")
        return usuario_ok and depto_ok and demanda_ok

    filtradas = [s for s in universo if passa(s)]

    def duracao(s: dict) -> int:
        if s["duracao"] is not None:
            return s["duracao"]
        return max(0, math.floor((agora - s["inicio"]).total_seconds()))

    duracoes = [duracao(s) for s in filtradas]
    total = sum(duracoes)
    return {
        "sessoesAtivas": sum(1 for s in filtradas if s["status"] == "ativa"),
        "sessoesEncerradas": sum(1 for s in filtradas if s["status"] == "encerrada"),
        "demandasDistintas": len({s["demanda"] for s in filtradas}),
        "usuariosDistintos": len({s["usuario"] for s in filtradas if s["usuario"] is not None}),
        "departamentosDistintos": len({s["departamento"] for s in filtradas if s["departamento"] is not None}),
        "tempoOperacionalEstimadoSegundos": total,
        "tempoMedioSessaoSegundos": math.floor(total / len(duracoes) + 0.5) if duracoes else 0,
        "maiorSessaoSegundos": max(duracoes) if duracoes else 0,
    }


def test_paridade_com_o_calculo_do_cliente(
    app, db_session: Session, empresa: Empresa, token_admin: str, client_admin: TestClient
) -> None:
    usuarios = [_usuario_id(db_session, empresa) for _ in range(3)]
    departamentos = [_departamento_id(db_session, empresa) for _ in range(2)]
    demandas = [_criar_demanda(client_admin, nome) for nome in ("Banner Verão", "Relatório Ação Social", "Vídeo Institucional")]
    agora = datetime.now(timezone.utc)

    registros: list[dict] = []

    def criar(status: str, duracao: int | None, inicio: datetime, usuario, departamento, demanda_idx: int | None) -> None:
        demanda_id = demandas[demanda_idx]["id"] if demanda_idx is not None else str(uuid.uuid4())
        _sessao(
            db_session, empresa, status=status, duracao=duracao or 0, inicio_em=inicio,
            usuario_id=usuario, departamento_id=departamento, demanda_id=demanda_id,
        )
        registros.append({
            "status": status, "duracao": duracao if status == "encerrada" else None, "inicio": inicio,
            "usuario": usuario, "departamento": departamento, "demanda": demanda_id,
            "numero": demandas[demanda_idx]["numeroOperacional"] if demanda_idx is not None else None,
            "nome": demandas[demanda_idx]["nome"] if demanda_idx is not None else None,
        })

    # encerradas (várias, dentro/fora do período, com e sem usuário/departamento/demanda)
    criar("encerrada", 600, PERIODO + timedelta(hours=1), usuarios[0], departamentos[0], 0)
    criar("encerrada", 1800, PERIODO + timedelta(hours=2), usuarios[0], departamentos[1], 1)
    criar("encerrada", 3000, PERIODO + timedelta(hours=3), usuarios[1], departamentos[1], 1)
    criar("encerrada", 45, PERIODO + timedelta(hours=4), usuarios[2], None, 2)
    criar("encerrada", 7200, PERIODO + timedelta(hours=5), None, departamentos[0], None)
    criar("encerrada", 999, PERIODO - timedelta(hours=1), usuarios[0], departamentos[0], 0)  # fora do período
    criar("encerrada", 123, PERIODO, None, None, 2)  # boundary
    # ativas (iniciadas em momentos distintos, inclusive antes do período)
    criar("ativa", None, agora - timedelta(seconds=500), usuarios[1], departamentos[0], 0)
    criar("ativa", None, agora - timedelta(days=2), usuarios[2], departamentos[1], 2)
    criar("ativa", None, agora - timedelta(seconds=90), None, None, 1)

    casos = [
        {"status": "todos", "usuarios": [], "departamentos": [], "demanda_query": ""},
        {"status": "ativa", "usuarios": [], "departamentos": [], "demanda_query": ""},
        {"status": "encerrada", "usuarios": [], "departamentos": [], "demanda_query": ""},
        {"status": "todos", "usuarios": [usuarios[0]], "departamentos": [], "demanda_query": ""},
        {"status": "todos", "usuarios": [usuarios[0], usuarios[1]], "departamentos": [], "demanda_query": ""},
        {"status": "todos", "usuarios": [], "departamentos": [departamentos[1]], "demanda_query": ""},
        {"status": "todos", "usuarios": [], "departamentos": departamentos, "demanda_query": ""},
        {"status": "todos", "usuarios": [], "departamentos": [], "demanda_query": "acao"},
        {"status": "todos", "usuarios": [], "departamentos": [], "demanda_query": "VIDEO"},
        {"status": "todos", "usuarios": [], "departamentos": [], "demanda_query": f"#{demandas[0]['numeroOperacional']}"},
        {"status": "encerrada", "usuarios": [usuarios[0]], "departamentos": [departamentos[1]], "demanda_query": "relatorio"},
        {"status": "todos", "usuarios": [usuarios[2]], "departamentos": [], "demanda_query": "institucional"},
        {"status": "todos", "usuarios": [], "departamentos": [], "demanda_query": "nada-casa"},
        {"status": "todos", "usuarios": [], "departamentos": [], "demanda_query": "acao "},  # espaço final, não aparado
    ]
    for caso in casos:
        caso["periodo"] = PERIODO
        parametros = {
            "status": caso["status"],
            "usuarioIds": ",".join(caso["usuarios"]) or None,
            "departamentoIds": ",".join(caso["departamentos"]) or None,
            "demandaQuery": caso["demanda_query"] or None,
        }
        resposta = get(TestClient(app), _url(**parametros), token=token_admin)
        assert resposta.status_code == 200, resposta.text
        servidor = resposta.json()
        referencia = _referencia_cliente(registros, caso, datetime.now(timezone.utc))
        n_ativas = referencia["sessoesAtivas"]

        for campo in ("sessoesAtivas", "sessoesEncerradas", "demandasDistintas", "usuariosDistintos", "departamentosDistintos"):
            assert servidor[campo] == referencia[campo], f"{campo} divergiu em {caso}"
        # Duração das ativas anda com o relógio (e o NOW() da transação de teste fica atrás do
        # relógio do Python): tolerância por sessão ativa. Contagens e distintos são EXATOS.
        folga = 30 * max(n_ativas, 1)
        assert abs(servidor["tempoOperacionalEstimadoSegundos"] - referencia["tempoOperacionalEstimadoSegundos"]) <= folga, caso
        assert abs(servidor["maiorSessaoSegundos"] - referencia["maiorSessaoSegundos"]) <= 30, caso
        assert abs(servidor["tempoMedioSessaoSegundos"] - referencia["tempoMedioSessaoSegundos"]) <= 30, caso
