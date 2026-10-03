"""D4A — `GET /relatorios/projetos/analise` e `GET /relatorios/projetos/pecas`: "Análise de projeto"
e "Análise de peças" calculadas no servidor, sem o cap de 200 Demandas globais que o frontend
tinha (`AppDataContext.demandas` = `GET /demandas?limit=200`, as mais recentes da EMPRESA).

Os valores são EXATOS (datas fixas, sem relógio). Além dos casos calculados à mão há um teste de
PARIDADE que porta `analisarProjeto`/`analisarPecasPorProjeto` (frontend/src/lib/relatorios.ts)
para Python e compara com o servidor, e um dataset de 250+ Demandas cujo resultado seria
truncado se alguma consulta voltasse a ter o cap.
"""

from __future__ import annotations

import itertools
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.core.escopo import EscopoDemanda
from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.empresa import Empresa
from app.models.projeto import Projeto
from app.models.usuario import Usuario
from app.repositories.relatorio_repository import RelatorioRepository
from tests.helpers.api import get
from tests.test_trafego_carga import _usuario

FUSO = ZoneInfo("America/Sao_Paulo")
BASE = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
_NUMERO = itertools.count(100_000)


def _projeto(client: TestClient, nome: str | None = None) -> dict:
    resposta = client.post("/projetos", json={"nome": nome or f"Projeto {uuid.uuid4().hex[:8]}"})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _demanda(
    db: Session,
    empresa: Empresa,
    projeto_id: str | None,
    *,
    nome: str | None = None,
    status: str = "em_execucao",
    prioridade: str = "media",
    criada: datetime | None = None,
    atualizada: datetime | None = None,
    data_inicio: date | None = None,
    enviado: datetime | None = None,
    retorno: datetime | None = None,
    responsaveis: list[Usuario] | None = None,
    numero: int | None = None,
) -> Demanda:
    n = numero if numero is not None else next(_NUMERO)
    criada = criada or BASE
    demanda = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_referencia=f"T26{n:06d}",
        ano_referencia=26,
        sequencial_referencia=n,
        numero_operacional=n,
        nome=nome or f"Demanda {n}",
        status=status,
        prioridade=prioridade,
        projeto_id=projeto_id,
        data_inicio=data_inicio,
        enviado_cliente_em=enviado,
        retorno_recebido_em=retorno,
        created_at=criada,
        updated_at=atualizada or criada,
    )
    db.add(demanda)
    db.flush()
    for usuario in responsaveis or []:
        db.add(DemandaResponsavel(demanda_id=demanda.id, usuario_id=usuario.id, created_at=criada))
    db.flush()
    return demanda


def _url_analise(projeto_id: str) -> str:
    return f"/relatorios/projetos/analise?projetoId={projeto_id}"


def _url_pecas(projeto_id: str, **params: int) -> str:
    extra = "".join(f"&{chave}={valor}" for chave, valor in params.items())
    return f"/relatorios/projetos/pecas?projetoId={projeto_id}{extra}"


def _analise(client: TestClient, projeto_id: str) -> dict:
    resposta = client.get(_url_analise(projeto_id))
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _pecas(client: TestClient, projeto_id: str, **params: int) -> dict:
    resposta = client.get(_url_pecas(projeto_id, **params))
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# --------------------------------------------------------------------------------------
# RBAC / tenant / validação
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("url", [_url_analise, _url_pecas])
def test_admin_e_gestor_acessam(client_admin: TestClient, client_gestor: TestClient, url) -> None:
    projeto = _projeto(client_admin)
    assert client_admin.get(url(projeto["id"])).status_code == 200
    assert client_gestor.get(url(projeto["id"])).status_code == 200


@pytest.mark.parametrize("url", [_url_analise, _url_pecas])
def test_operador_e_403(client_admin: TestClient, client_operador: TestClient, url) -> None:
    projeto = _projeto(client_admin)
    assert client_operador.get(url(projeto["id"])).status_code == 403


@pytest.mark.parametrize("url", [_url_analise, _url_pecas])
def test_sem_token_e_401(app, client_admin: TestClient, url) -> None:
    projeto = _projeto(client_admin)
    assert get(TestClient(app), url(projeto["id"])).status_code == 401


@pytest.mark.parametrize("url", [_url_analise, _url_pecas])
def test_projeto_inexistente_e_404(client_admin: TestClient, url) -> None:
    assert client_admin.get(url(str(uuid.uuid4()))).status_code == 404


@pytest.mark.parametrize("url", [_url_analise, _url_pecas])
def test_projeto_de_outra_empresa_e_404_nunca_403(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa, url
) -> None:
    agora = datetime.now(timezone.utc)
    alheio = Projeto(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_referencia="P26009999",
        ano_referencia=26,
        sequencial_referencia=9999,
        nome="Projeto de outra empresa",
        nome_normalizado="projeto de outra empresa",
        status="ativo",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(alheio)
    db_session.flush()
    assert client_admin.get(url(alheio.id)).status_code == 404


@pytest.mark.parametrize("url", [_url_analise, _url_pecas])
def test_projeto_id_invalido_e_422(client_admin: TestClient, url) -> None:
    assert client_admin.get(url("nao-e-uuid")).status_code == 422


@pytest.mark.parametrize("parametros", [{"limit": 0}, {"limit": 201}, {"offset": -1}])
def test_paginacao_invalida_e_422(client_admin: TestClient, parametros: dict) -> None:
    projeto = _projeto(client_admin)
    assert client_admin.get(_url_pecas(projeto["id"], **parametros)).status_code == 422


def test_demanda_de_outra_empresa_com_o_mesmo_projeto_nao_conta(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    """Defesa em profundidade: mesmo uma linha (impossível pela API) de outra empresa apontando
    para o Projeto não entra — o universo filtra por `empresa_id`."""
    projeto = _projeto(client_admin)
    _demanda(db_session, empresa, projeto["id"])
    _demanda(db_session, outra_empresa, projeto["id"], prioridade="alta")
    assert _analise(client_admin, projeto["id"])["totalDemandas"] == 1
    assert _pecas(client_admin, projeto["id"])["total"] == 1


# --------------------------------------------------------------------------------------
# Análise de projeto
# --------------------------------------------------------------------------------------


def test_analise_vazia(client_admin: TestClient) -> None:
    projeto = _projeto(client_admin, "Projeto Vazio")
    assert _analise(client_admin, projeto["id"]) == {
        "projetoId": projeto["id"],
        "projetoNome": "Projeto Vazio",
        "totalDemandas": 0,
        "prioridade": {"baixa": 0, "media": 0, "alta": 0},
        "tempoMedioAberturaAteInicioDias": None,
        "tempoMedioRetornoClienteDias": None,
        "colaboradores": [],
    }


def test_analise_com_um_registro(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(client_admin)
    ana = _usuario(db_session, empresa, "Ana")
    _demanda(
        db_session,
        empresa,
        projeto["id"],
        prioridade="alta",
        criada=datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc),
        data_inicio=date(2026, 3, 12),
        enviado=datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc),
        retorno=datetime(2026, 3, 11, 18, 0, tzinfo=timezone.utc),
        responsaveis=[ana],
    )
    corpo = _analise(client_admin, projeto["id"])
    assert corpo["totalDemandas"] == 1
    assert corpo["prioridade"] == {"baixa": 0, "media": 0, "alta": 1}
    # 12/03 00:00 (São Paulo, UTC-3) = 12/03 03:00Z; criada 10/03 15:00Z → 1 dia + 12h = 1.5d.
    assert corpo["tempoMedioAberturaAteInicioDias"] == pytest.approx(1.5)
    assert corpo["tempoMedioRetornoClienteDias"] == pytest.approx(0.25)
    assert corpo["colaboradores"] == [{"id": ana.id, "nome": "Ana", "demandas": 1}]


def test_analise_multiplos_com_medias_prioridades_e_colaboradores(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    projeto = _projeto(client_admin)
    ana, bruno, carla = (_usuario(db_session, empresa, nome) for nome in ("Ana", "Bruno", "Carla"))
    criada = datetime(2026, 3, 10, 3, 0, tzinfo=timezone.utc)  # 10/03 00:00 em São Paulo
    _demanda(db_session, empresa, projeto["id"], prioridade="baixa", criada=criada, data_inicio=date(2026, 3, 11),
             enviado=BASE, retorno=BASE + timedelta(days=2), responsaveis=[bruno])
    _demanda(db_session, empresa, projeto["id"], prioridade="media", criada=criada, data_inicio=date(2026, 3, 13),
             enviado=BASE, retorno=BASE + timedelta(days=4), responsaveis=[bruno, ana])
    _demanda(db_session, empresa, projeto["id"], prioridade="alta", criada=criada, responsaveis=[bruno])
    _demanda(db_session, empresa, projeto["id"], prioridade="alta", criada=criada, responsaveis=[])
    _demanda(db_session, empresa, projeto["id"], prioridade="alta", status="concluida", criada=criada, responsaveis=[carla])
    _demanda(db_session, empresa, projeto["id"], prioridade="baixa", status="cancelada", criada=criada)

    corpo = _analise(client_admin, projeto["id"])
    assert corpo["totalDemandas"] == 6  # concluída e cancelada contam: "Total no projeto"
    assert corpo["prioridade"] == {"baixa": 2, "media": 1, "alta": 3}
    # Só as duas com `data_inicio`: (1 + 3) / 2 = 2 dias.
    assert corpo["tempoMedioAberturaAteInicioDias"] == pytest.approx(2.0)
    assert corpo["tempoMedioRetornoClienteDias"] == pytest.approx(3.0)
    assert corpo["colaboradores"] == [
        {"id": ana.id, "nome": "Ana", "demandas": 1},
        {"id": bruno.id, "nome": "Bruno", "demandas": 3},
        {"id": carla.id, "nome": "Carla", "demandas": 1},
    ]


def test_analise_ignora_arquivada_outro_projeto_e_sem_projeto(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    alvo = _projeto(client_admin)
    outro = _projeto(client_admin)
    ana = _usuario(db_session, empresa, "Ana")
    _demanda(db_session, empresa, alvo["id"], responsaveis=[ana])
    _demanda(db_session, empresa, alvo["id"], status="arquivada", prioridade="alta", responsaveis=[ana])
    _demanda(db_session, empresa, outro["id"], responsaveis=[ana])
    _demanda(db_session, empresa, None, responsaveis=[ana])
    corpo = _analise(client_admin, alvo["id"])
    assert corpo["totalDemandas"] == 1
    assert corpo["prioridade"]["alta"] == 0
    assert corpo["colaboradores"] == [{"id": ana.id, "nome": "Ana", "demandas": 1}]


def test_media_de_abertura_ignora_sem_data_inicio_e_retorno_exige_os_dois_campos(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    projeto = _projeto(client_admin)
    criada = datetime(2026, 3, 10, 3, 0, tzinfo=timezone.utc)
    _demanda(db_session, empresa, projeto["id"], criada=criada, data_inicio=date(2026, 3, 12))
    _demanda(db_session, empresa, projeto["id"], criada=criada)  # sem data_inicio: fora da média
    _demanda(db_session, empresa, projeto["id"], criada=criada, enviado=BASE)  # sem retorno: fora
    _demanda(db_session, empresa, projeto["id"], criada=criada, retorno=BASE)  # sem envio: fora
    _demanda(db_session, empresa, projeto["id"], criada=criada, enviado=BASE, retorno=BASE + timedelta(days=1))
    corpo = _analise(client_admin, projeto["id"])
    assert corpo["tempoMedioAberturaAteInicioDias"] == pytest.approx(2.0)
    assert corpo["tempoMedioRetornoClienteDias"] == pytest.approx(1.0)


def test_abertura_usa_a_meia_noite_do_fuso_da_aplicacao(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Fronteira de data: `data_inicio` é dia de calendário, 00:00 em São Paulo (UTC-3), não em
    UTC. Criada exatamente nesse instante → 0d (com UTC seria -0.125d); 1s antes → +1s; depois
    → negativo (como sempre foi)."""
    projeto = _projeto(client_admin)
    meia_noite_sp = datetime(2026, 3, 10, 3, 0, tzinfo=timezone.utc)
    _demanda(db_session, empresa, projeto["id"], criada=meia_noite_sp, data_inicio=date(2026, 3, 10))
    assert _analise(client_admin, projeto["id"])["tempoMedioAberturaAteInicioDias"] == pytest.approx(0.0, abs=1e-12)

    outro = _projeto(client_admin)
    _demanda(db_session, empresa, outro["id"], criada=meia_noite_sp - timedelta(seconds=1), data_inicio=date(2026, 3, 10))
    assert _analise(client_admin, outro["id"])["tempoMedioAberturaAteInicioDias"] == pytest.approx(1 / 86400)

    terceiro = _projeto(client_admin)
    _demanda(db_session, empresa, terceiro["id"], criada=meia_noite_sp + timedelta(hours=12), data_inicio=date(2026, 3, 10))
    assert _analise(client_admin, terceiro["id"])["tempoMedioAberturaAteInicioDias"] == pytest.approx(-0.5)


def test_colaboradores_excluem_conta_de_sistema_e_usuario_de_outra_empresa(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    projeto = _projeto(client_admin)
    ana = _usuario(db_session, empresa, "Ana")
    sistema = _usuario(db_session, empresa, "Sistema")
    sistema.is_system_account = True
    alheio = _usuario(db_session, outra_empresa, "Alheio")
    db_session.flush()
    _demanda(db_session, empresa, projeto["id"], responsaveis=[ana, sistema, alheio])
    corpo = _analise(client_admin, projeto["id"])
    assert corpo["colaboradores"] == [{"id": ana.id, "nome": "Ana", "demandas": 1}]


def test_usuario_inativo_ou_arquivado_continua_nos_colaboradores(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """O diretório de usuários da tela incluía todos os status — referência histórica."""
    projeto = _projeto(client_admin)
    antigo = _usuario(db_session, empresa, "Antigo", status="arquivado")
    _demanda(db_session, empresa, projeto["id"], responsaveis=[antigo])
    assert [c["nome"] for c in _analise(client_admin, projeto["id"])["colaboradores"]] == ["Antigo"]


def test_analise_respeita_o_escopo_resolvido_e_escopo_vazio_devolve_zeros(
    db_session: Session, empresa: Empresa, client_admin: TestClient, usuario_operador: Usuario
) -> None:
    """O universo passa pelo predicado ÚNICO de escopo de Demanda (a rota só admite quem tem
    visão total, mas a regra não é fixada aqui): um escopo "meus" só vê o que o usuário
    responde; um escopo vazio não vê nada."""
    projeto = _projeto(client_admin)
    _demanda(db_session, empresa, projeto["id"], responsaveis=[usuario_operador])
    _demanda(db_session, empresa, projeto["id"], responsaveis=[])
    repo = RelatorioRepository()

    meus = EscopoDemanda(
        empresa_id=empresa.id, usuario_id=usuario_operador.id, visao_total=False, usuario_responsavel=True
    )
    vazio = EscopoDemanda(empresa_id=empresa.id, usuario_id=usuario_operador.id, visao_total=False)
    total = EscopoDemanda(empresa_id=empresa.id, usuario_id=usuario_operador.id, visao_total=True)

    assert repo.analise_projeto(db_session, escopo=meus, projeto_id=projeto["id"], fuso="UTC")["total"] == 1
    assert repo.analise_projeto(db_session, escopo=total, projeto_id=projeto["id"], fuso="UTC")["total"] == 2
    assert repo.analise_projeto(db_session, escopo=vazio, projeto_id=projeto["id"], fuso="UTC")["total"] == 0
    assert repo.pecas_projeto(db_session, escopo=meus, projeto_id=projeto["id"], limit=50, offset=0)[1] == 1
    assert repo.pecas_projeto(db_session, escopo=vazio, projeto_id=projeto["id"], limit=50, offset=0) == ([], 0)


# --------------------------------------------------------------------------------------
# Análise de peças
# --------------------------------------------------------------------------------------


def test_pecas_vazio(client_admin: TestClient) -> None:
    projeto = _projeto(client_admin)
    assert _pecas(client_admin, projeto["id"]) == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_pecas_um_registro_e_em_andamento(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(client_admin)
    ana = _usuario(db_session, empresa, "Ana")
    demanda = _demanda(db_session, empresa, projeto["id"], nome="Banner", numero=777, responsaveis=[ana])
    corpo = _pecas(client_admin, projeto["id"])
    assert corpo["total"] == 1
    assert corpo["items"] == [
        {
            "demandaId": demanda.id,
            "nome": "Banner",
            "numeroOperacional": 777,
            "redatorNome": "Ana",
            "tempoEmPautaDias": None,
            "emAndamento": True,
        }
    ]


def test_pecas_tempo_em_pauta_so_para_concluida_ou_cancelada(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    projeto = _projeto(client_admin)
    for status in ("rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"):
        _demanda(db_session, empresa, projeto["id"], status=status, atualizada=BASE + timedelta(days=9))
    concluida = _demanda(db_session, empresa, projeto["id"], status="concluida", atualizada=BASE + timedelta(days=3, hours=12))
    cancelada = _demanda(db_session, empresa, projeto["id"], status="cancelada", atualizada=BASE + timedelta(hours=6))
    por_id = {item["demandaId"]: item for item in _pecas(client_admin, projeto["id"])["items"]}

    assert len(por_id) == 8
    assert por_id[concluida.id]["emAndamento"] is False
    assert por_id[concluida.id]["tempoEmPautaDias"] == pytest.approx(3.5)
    assert por_id[cancelada.id]["emAndamento"] is False
    assert por_id[cancelada.id]["tempoEmPautaDias"] == pytest.approx(0.25)
    abertas = [item for demanda_id, item in por_id.items() if demanda_id not in (concluida.id, cancelada.id)]
    assert all(item["emAndamento"] and item["tempoEmPautaDias"] is None for item in abertas)


def test_pecas_ordem_numero_operacional_desc_e_arquivada_fora(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    projeto = _projeto(client_admin)
    for numero in (5, 9, 1, 7):
        _demanda(db_session, empresa, projeto["id"], numero=numero)
    _demanda(db_session, empresa, projeto["id"], numero=99, status="arquivada")
    corpo = _pecas(client_admin, projeto["id"])
    assert [item["numeroOperacional"] for item in corpo["items"]] == [9, 7, 5, 1]
    assert corpo["total"] == 4


def test_redator_e_o_primeiro_responsavel_por_id_e_sem_responsavel_e_nulo(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    projeto = _projeto(client_admin)
    a, b, c = (_usuario(db_session, empresa, nome) for nome in ("Ana", "Bruno", "Carla"))
    primeiro = min((a, b, c), key=lambda usuario: usuario.id)
    com = _demanda(db_session, empresa, projeto["id"], numero=2, responsaveis=[a, b, c])
    sem = _demanda(db_session, empresa, projeto["id"], numero=1)
    por_id = {item["demandaId"]: item for item in _pecas(client_admin, projeto["id"])["items"]}
    assert por_id[com.id]["redatorNome"] == primeiro.nome
    assert por_id[sem.id]["redatorNome"] is None


def test_redator_conta_de_sistema_ou_de_outra_empresa_e_nulo(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    """Fora do diretório de usuários da tela → "Sem responsável", como antes (nome nunca vaza)."""
    projeto = _projeto(client_admin)
    sistema = _usuario(db_session, empresa, "Sistema")
    sistema.is_system_account = True
    alheio = _usuario(db_session, outra_empresa, "Alheio")
    db_session.flush()
    d1 = _demanda(db_session, empresa, projeto["id"], numero=2, responsaveis=[sistema])
    d2 = _demanda(db_session, empresa, projeto["id"], numero=1, responsaveis=[alheio])
    por_id = {item["demandaId"]: item for item in _pecas(client_admin, projeto["id"])["items"]}
    assert por_id[d1.id]["redatorNome"] is None
    assert por_id[d2.id]["redatorNome"] is None


def test_pecas_paginacao_total_estavel_e_pagina_alem_do_fim(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    projeto = _projeto(client_admin)
    for numero in range(1, 8):
        _demanda(db_session, empresa, projeto["id"], numero=numero)
    primeira = _pecas(client_admin, projeto["id"], limit=3, offset=0)
    segunda = _pecas(client_admin, projeto["id"], limit=3, offset=3)
    terceira = _pecas(client_admin, projeto["id"], limit=3, offset=6)
    alem = _pecas(client_admin, projeto["id"], limit=3, offset=30)

    assert [i["numeroOperacional"] for i in primeira["items"]] == [7, 6, 5]
    assert [i["numeroOperacional"] for i in segunda["items"]] == [4, 3, 2]
    assert [i["numeroOperacional"] for i in terceira["items"]] == [1]
    assert primeira["total"] == segunda["total"] == terceira["total"] == alem["total"] == 7
    assert alem["items"] == [] and alem["offset"] == 30 and alem["limit"] == 3


# --------------------------------------------------------------------------------------
# Dataset > 200 — falharia se algum caminho voltasse a ter o cap
# --------------------------------------------------------------------------------------


def test_dataset_acima_de_200_nao_trunca_nada(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    """Projeto ALVO com 250 Demandas ANTIGAS + 60 Demandas MAIS RECENTES de outro projeto: o
    antigo `GET /demandas?limit=200` da empresa devolveria só as 200 mais novas — 60 do ruído e
    140 do alvo. Aqui o alvo tem de aparecer inteiro; e o projeto cujas Demandas ficam TODAS
    além dessa janela não pode sumir."""
    alvo = _projeto(client_admin, "Alvo")
    ruido = _projeto(client_admin, "Ruido")
    antigo = _projeto(client_admin, "Antigo")
    ana, bruno = _usuario(db_session, empresa, "Ana"), _usuario(db_session, empresa, "Bruno")

    numero = 1
    for i in range(10):  # as 10 mais antigas de todas: o projeto "Antigo"
        _demanda(db_session, empresa, antigo["id"], numero=numero, responsaveis=[bruno])
        numero += 1
    prioridades = ["baixa", "media", "alta"]
    for i in range(250):
        _demanda(
            db_session,
            empresa,
            alvo["id"],
            numero=numero,
            prioridade=prioridades[i % 3],
            status="concluida" if i % 5 == 0 else "em_execucao",
            responsaveis=[ana] if i % 2 == 0 else [ana, bruno],
        )
        numero += 1
    for i in range(60):
        _demanda(db_session, empresa, ruido["id"], numero=numero, responsaveis=[bruno])
        numero += 1

    analise = _analise(client_admin, alvo["id"])
    assert analise["totalDemandas"] == 250
    assert analise["prioridade"] == {"baixa": 84, "media": 83, "alta": 83}  # i%3 em 0..249
    assert analise["colaboradores"] == [
        {"id": ana.id, "nome": "Ana", "demandas": 250},
        {"id": bruno.id, "nome": "Bruno", "demandas": 125},
    ]

    pecas = _pecas(client_admin, alvo["id"], limit=200, offset=0)
    resto = _pecas(client_admin, alvo["id"], limit=200, offset=200)
    assert pecas["total"] == resto["total"] == 250
    assert len(pecas["items"]) == 200 and len(resto["items"]) == 50
    todos = [item["numeroOperacional"] for item in pecas["items"] + resto["items"]]
    assert todos == sorted(todos, reverse=True) and len(set(todos)) == 250
    assert sum(1 for item in pecas["items"] + resto["items"] if not item["emAndamento"]) == 50

    # Todas as Demandas do projeto "Antigo" estão além das 200 mais recentes da empresa.
    antigo_analise = _analise(client_admin, antigo["id"])
    assert antigo_analise["totalDemandas"] == 10
    assert antigo_analise["colaboradores"] == [{"id": bruno.id, "nome": "Bruno", "demandas": 10}]
    assert _pecas(client_admin, antigo["id"])["total"] == 10


# --------------------------------------------------------------------------------------
# Paridade com a lógica antiga do frontend (portada) — só em teste, nunca em produção
# --------------------------------------------------------------------------------------


def _analisar_projeto_antigo(demandas: list[Demanda], responsaveis: dict[str, list[str]], usuarios: list[Usuario]) -> dict:
    """Porte de `analisarProjeto` (lib/relatorios.ts), com a diretório de usuários ordenado por
    nome e `parseDataLocal` como 00:00 do dia no fuso local."""

    def dias(inicio: datetime, fim: datetime) -> float:
        return (fim - inicio).total_seconds() / 86400

    aberturas = [
        dias(d.created_at, datetime(d.data_inicio.year, d.data_inicio.month, d.data_inicio.day, tzinfo=FUSO))
        for d in demandas
        if d.data_inicio is not None
    ]
    retornos = [dias(d.enviado_cliente_em, d.retorno_recebido_em) for d in demandas if d.enviado_cliente_em and d.retorno_recebido_em]
    colaboradores = [
        {"id": u.id, "nome": u.nome, "demandas": sum(1 for d in demandas if u.id in responsaveis.get(d.id, []))}
        for u in sorted(usuarios, key=lambda usuario: usuario.nome)
    ]
    return {
        "totalDemandas": len(demandas),
        "prioridade": {p: sum(1 for d in demandas if d.prioridade == p) for p in ("baixa", "media", "alta")},
        "tempoMedioAberturaAteInicioDias": sum(aberturas) / len(aberturas) if aberturas else None,
        "tempoMedioRetornoClienteDias": sum(retornos) / len(retornos) if retornos else None,
        "colaboradores": [c for c in colaboradores if c["demandas"] > 0],
    }


def _analisar_pecas_antigo(demandas: list[Demanda], responsaveis: dict[str, list[str]], nomes: dict[str, str]) -> list[dict]:
    """Porte de `analisarPecasPorProjeto`, na ordem da listagem (`numero_operacional DESC`)."""
    pecas = []
    for d in sorted(demandas, key=lambda demanda: demanda.numero_operacional, reverse=True):
        primeiro = sorted(responsaveis.get(d.id, []))[:1]
        em_andamento = d.status not in ("concluida", "cancelada")
        pecas.append(
            {
                "demandaId": d.id,
                "nome": d.nome,
                "numeroOperacional": d.numero_operacional,
                "redatorNome": nomes.get(primeiro[0]) if primeiro else None,
                "tempoEmPautaDias": None if em_andamento else (d.updated_at - d.created_at).total_seconds() / 86400,
                "emAndamento": em_andamento,
            }
        )
    return pecas


def test_paridade_com_a_logica_antiga_do_frontend(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    projeto = _projeto(client_admin)
    usuarios = [_usuario(db_session, empresa, nome) for nome in ("Ana", "Bruno", "Carla", "Daniel")]
    ana, bruno, carla, daniel = usuarios
    cenarios = [
        dict(prioridade="alta", criada=datetime(2026, 3, 2, 14, 30, tzinfo=timezone.utc), data_inicio=date(2026, 3, 4), responsaveis=[ana, bruno]),
        dict(prioridade="media", criada=datetime(2026, 3, 3, 9, 0, tzinfo=timezone.utc), data_inicio=date(2026, 3, 3), responsaveis=[bruno]),
        dict(prioridade="baixa", status="concluida", criada=datetime(2026, 3, 4, 9, 0, tzinfo=timezone.utc),
             atualizada=datetime(2026, 3, 9, 21, 17, tzinfo=timezone.utc), responsaveis=[carla]),
        dict(prioridade="alta", status="cancelada", criada=datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc),
             atualizada=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc), responsaveis=[]),
        dict(prioridade="media", criada=datetime(2026, 3, 6, 9, 0, tzinfo=timezone.utc), data_inicio=date(2026, 3, 1),
             enviado=datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc), retorno=datetime(2026, 3, 8, 16, 45, tzinfo=timezone.utc),
             responsaveis=[daniel, ana]),
        dict(prioridade="media", status="aguardando_cliente", criada=datetime(2026, 3, 7, 1, 59, tzinfo=timezone.utc),
             enviado=datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc), retorno=datetime(2026, 3, 7, 11, 0, tzinfo=timezone.utc),
             responsaveis=[carla]),
        dict(prioridade="baixa", status="pausada", criada=datetime(2026, 3, 8, 9, 0, tzinfo=timezone.utc), responsaveis=[ana]),
    ]
    for cenario in cenarios:
        _demanda(db_session, empresa, projeto["id"], **cenario)

    demandas = list(db_session.scalars(select(Demanda).where(Demanda.projeto_id == projeto["id"])).all())
    responsaveis: dict[str, list[str]] = {d.id: [] for d in demandas}
    for demanda_id, usuario_id in db_session.execute(select(DemandaResponsavel.demanda_id, DemandaResponsavel.usuario_id)):
        if demanda_id in responsaveis:
            responsaveis[demanda_id].append(usuario_id)

    esperado = _analisar_projeto_antigo(demandas, responsaveis, usuarios)
    obtido = _analise(client_admin, projeto["id"])
    assert obtido["totalDemandas"] == esperado["totalDemandas"]
    assert obtido["prioridade"] == esperado["prioridade"]
    assert obtido["tempoMedioAberturaAteInicioDias"] == pytest.approx(esperado["tempoMedioAberturaAteInicioDias"], abs=1e-9)
    assert obtido["tempoMedioRetornoClienteDias"] == pytest.approx(esperado["tempoMedioRetornoClienteDias"], abs=1e-9)
    assert obtido["colaboradores"] == esperado["colaboradores"]

    esperadas = _analisar_pecas_antigo(demandas, responsaveis, {u.id: u.nome for u in usuarios})
    obtidas = _pecas(client_admin, projeto["id"])["items"]
    assert len(obtidas) == len(esperadas)
    for obtida, esperada in zip(obtidas, esperadas, strict=True):
        assert {k: v for k, v in obtida.items() if k != "tempoEmPautaDias"} == {k: v for k, v in esperada.items() if k != "tempoEmPautaDias"}
        if esperada["tempoEmPautaDias"] is None:
            assert obtida["tempoEmPautaDias"] is None
        else:
            assert obtida["tempoEmPautaDias"] == pytest.approx(esperada["tempoEmPautaDias"], abs=1e-9)


# --------------------------------------------------------------------------------------
# Sem N+1
# --------------------------------------------------------------------------------------


def _consultas_a_demandas(app, db_session: Session, token: str, url: str) -> int:
    chamadas: list[str] = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "FROM demandas" in statement or "demanda_responsaveis" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = get(TestClient(app), url, token=token)
    finally:
        event.remove(engine, "before_cursor_execute", _contar)
    assert resposta.status_code == 200, resposta.text
    return len(chamadas)


def test_numero_de_consultas_constante_com_poucas_ou_muitas_demandas(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa, token_admin: str
) -> None:
    projeto = _projeto(client_admin)
    usuarios = [_usuario(db_session, empresa) for _ in range(5)]
    _demanda(db_session, empresa, projeto["id"], responsaveis=usuarios[:1])
    analise_poucas = _consultas_a_demandas(app, db_session, token_admin, _url_analise(projeto["id"]))
    pecas_poucas = _consultas_a_demandas(app, db_session, token_admin, _url_pecas(projeto["id"], limit=200))
    for i in range(79):
        _demanda(db_session, empresa, projeto["id"], responsaveis=usuarios[: 1 + i % 5], status="concluida" if i % 2 else "pausada")
    analise_muitas = _consultas_a_demandas(app, db_session, token_admin, _url_analise(projeto["id"]))
    pecas_muitas = _consultas_a_demandas(app, db_session, token_admin, _url_pecas(projeto["id"], limit=200))

    assert analise_poucas == analise_muitas == 2  # agregados + colaboradores
    assert pecas_poucas == pecas_muitas == 2  # total + página (redator resolvido no mesmo SELECT)
