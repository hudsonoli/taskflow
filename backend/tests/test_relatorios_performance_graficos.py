"""D4B — "Performance de colaborador" e os três gráficos de Relatórios, calculados no servidor:

- `GET /relatorios/colaboradores` e `/colaboradores/performance?colaboradorId=`
- `GET /relatorios/graficos/abertas-por-projeto?clienteId=`
- `GET /relatorios/graficos/volume-por-colaborador`
- `GET /relatorios/graficos/volume-semanal`

Antes, tudo isso era calculado no navegador sobre `AppDataContext.demandas`
(`GET /demandas?limit=200`: as 200 Demandas mais recentes da EMPRESA). Aqui os valores são
EXATOS (datas fixas, relógio injetado), há testes de PARIDADE com a lógica antiga portada
(`analisarPerformanceColaborador`, `demandasAbertasPorProjeto`, `volumePorProjetoEColaborador`,
`volumeSemanal` de frontend/src/lib/relatorios.ts), de múltiplos responsáveis (a Demanda conta
para CADA um — double-count INTENCIONAL, é o que o frontend sempre fez), de >200 Demandas e de
número de queries constante.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.helpers.api import get
from tests.test_relatorios_projeto import BASE, FUSO, _demanda
from tests.test_trafego_carga import _usuario

STATUS_TODOS = (
    "rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente", "concluida", "cancelada", "arquivada",
)
STATUS_ABERTOS = STATUS_TODOS[:6]


def _cliente(client: TestClient, nome: str | None = None) -> dict:
    corpo = {"nome": nome or f"Cliente {uuid.uuid4().hex[:8]}", "tipoDocumento": "cnpj", "corIdentificacao": "blue"}
    resposta = client.post("/clientes", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _projeto_de(client: TestClient, cliente_id: str | None, nome: str | None = None) -> dict:
    corpo = {"nome": nome or f"Projeto {uuid.uuid4().hex[:8]}"}
    if cliente_id:
        corpo["clienteId"] = cliente_id
    resposta = client.post("/projetos", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _etapa(db: Session, demanda: Demanda, ordem: int, nome: str, responsaveis: list[Usuario]) -> DemandaWorkflowEtapa:
    etapa = DemandaWorkflowEtapa(
        id=str(uuid.uuid4()),
        demanda_id=demanda.id,
        ordem=ordem,
        nome=nome,
        tipo="execucao",
        quantidade_antes_deadline=1,
        unidade_prazo="horas",
        status="pendente",
        created_at=BASE,
        updated_at=BASE,
    )
    db.add(etapa)
    db.flush()
    for usuario in responsaveis:
        db.add(DemandaWorkflowEtapaResponsavel(demanda_workflow_etapa_id=etapa.id, usuario_id=usuario.id, created_at=BASE))
    db.flush()
    return etapa


def _demanda_com_prazo(
    db: Session, empresa: Empresa, usuario: Usuario | None, status: str, fim_previsto: date | None,
    atualizada: datetime, *, numero: int | None = None, projeto_id: str | None = None,
) -> Demanda:
    demanda = _demanda(db, empresa, projeto_id, status=status, atualizada=atualizada, numero=numero,
                       responsaveis=[usuario] if usuario else [])
    demanda.data_fim_prevista = fim_previsto
    db.flush()
    return demanda


def _performance(client: TestClient, colaborador_id: str) -> dict:
    resposta = client.get(f"/relatorios/colaboradores/performance?colaboradorId={colaborador_id}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _abertas(client: TestClient, cliente_id: str) -> list[dict]:
    resposta = client.get(f"/relatorios/graficos/abertas-por-projeto?clienteId={cliente_id}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _volume(client: TestClient) -> list[dict]:
    resposta = client.get("/relatorios/graficos/volume-por-colaborador")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _semanal(client: TestClient) -> list[dict]:
    resposta = client.get("/relatorios/graficos/volume-semanal")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _fixar_agora(monkeypatch: pytest.MonkeyPatch, agora: datetime) -> None:
    monkeypatch.setattr("app.services.relatorio_service.agora_local", lambda: agora.astimezone(FUSO))


# --------------------------------------------------------------------------------------
# RBAC / tenant / validação
# --------------------------------------------------------------------------------------

_SEM_PARAMETRO = [
    "/relatorios/colaboradores",
    "/relatorios/graficos/volume-por-colaborador",
    "/relatorios/graficos/volume-semanal",
]


@pytest.mark.parametrize("url", _SEM_PARAMETRO)
def test_rbac_sem_parametro(app, client_admin: TestClient, client_gestor: TestClient, client_operador: TestClient, url: str) -> None:
    assert client_admin.get(url).status_code == 200
    assert client_gestor.get(url).status_code == 200
    assert client_operador.get(url).status_code == 403
    assert get(TestClient(app), url).status_code == 401


def test_rbac_com_parametro(
    app, client_admin: TestClient, client_gestor: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    cliente = _cliente(client_admin)
    urls = [
        f"/relatorios/colaboradores/performance?colaboradorId={usuario_operador.id}",
        f"/relatorios/graficos/abertas-por-projeto?clienteId={cliente['id']}",
    ]
    for url in urls:
        assert client_admin.get(url).status_code == 200
        assert client_gestor.get(url).status_code == 200
        assert client_operador.get(url).status_code == 403
        assert get(TestClient(app), url).status_code == 401


def test_ids_invalidos_sao_422(client_admin: TestClient) -> None:
    assert client_admin.get("/relatorios/colaboradores/performance?colaboradorId=x").status_code == 422
    assert client_admin.get("/relatorios/graficos/abertas-por-projeto?clienteId=x").status_code == 422
    assert client_admin.get("/relatorios/colaboradores/performance").status_code == 422


def test_colaborador_inexistente_de_outra_empresa_ou_de_sistema_e_404(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    sistema = _usuario(db_session, empresa, "Sistema")
    sistema.is_system_account = True
    alheio = _usuario(db_session, outra_empresa, "Alheio")
    db_session.flush()
    for colaborador_id in (str(uuid.uuid4()), alheio.id, sistema.id):
        assert client_admin.get(f"/relatorios/colaboradores/performance?colaboradorId={colaborador_id}").status_code == 404


def test_cliente_inexistente_ou_de_outra_empresa_e_404_nunca_403(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    agora = datetime.now(timezone.utc)
    alheio = Cliente(
        id=str(uuid.uuid4()), empresa_id=outra_empresa.id, codigo_interno="cli-alheio", codigo_referencia="C26009999",
        ano_referencia=26, sequencial_referencia=9999, nome="Alheio", nome_normalizado="alheio", tipo_documento="cnpj",
        status="ativo", cor_identificacao="blue", created_at=agora, updated_at=agora,
    )
    db_session.add(alheio)
    db_session.flush()
    for cliente_id in (str(uuid.uuid4()), alheio.id):
        assert client_admin.get(f"/relatorios/graficos/abertas-por-projeto?clienteId={cliente_id}").status_code == 404


# --------------------------------------------------------------------------------------
# Opções do seletor de colaboradores
# --------------------------------------------------------------------------------------


def test_colaboradores_todos_os_status_sem_sistema_ordem_nome_e_so_da_empresa(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    ativo = _usuario(db_session, empresa, "Bruno")
    inativo = _usuario(db_session, empresa, "Ana", status="inativo")
    arquivado = _usuario(db_session, empresa, "Carla", status="arquivado")
    sistema = _usuario(db_session, empresa, "Sistema")
    sistema.is_system_account = True
    alheio = _usuario(db_session, outra_empresa, "Alheio")
    db_session.flush()
    ids = [opcao["id"] for opcao in client_admin.get("/relatorios/colaboradores").json()]
    assert {ativo.id, inativo.id, arquivado.id} <= set(ids)
    assert sistema.id not in ids and alheio.id not in ids
    nomes = [opcao["nome"] for opcao in client_admin.get("/relatorios/colaboradores").json()]
    assert nomes == sorted(nomes)  # `nome ASC`


def test_colaborador_alem_da_antiga_janela_de_200_usuarios_aparece_e_tem_nome_correto(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """O diretório do frontend cortava em `limit=200` por nome. Com 205 usuários, o último por
    nome ficava de fora do seletor; aqui ele aparece e o nome vem do servidor."""
    for i in range(205):
        _usuario(db_session, empresa, f"AAA {i:03d}")
    ultimo = _usuario(db_session, empresa, "ZZZ Último Colaborador")
    opcoes = client_admin.get("/relatorios/colaboradores").json()
    assert len(opcoes) > 200
    assert opcoes[-1] == {"id": ultimo.id, "nome": "ZZZ Último Colaborador"}
    assert _performance(client_admin, ultimo.id)["colaboradorNome"] == "ZZZ Último Colaborador"


# --------------------------------------------------------------------------------------
# Performance de colaborador
# --------------------------------------------------------------------------------------


def test_performance_vazia(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    ana = _usuario(db_session, empresa, "Ana")
    assert _performance(client_admin, ana.id) == {
        "colaboradorId": ana.id,
        "colaboradorNome": "Ana",
        "demandasEntregues": 0,
        "entreguesNoPrazo": 0,
        "entreguesEmAtraso": 0,
        "participacaoPorEtapa": [],
    }


def test_performance_uma_demanda_no_prazo(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    ana = _usuario(db_session, empresa, "Ana")
    demanda = _demanda_com_prazo(db_session, empresa, ana, "concluida", date(2026, 3, 20), datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc))
    _etapa(db_session, demanda, 1, "Criação", [ana])
    corpo = _performance(client_admin, ana.id)
    assert corpo["demandasEntregues"] == 1
    assert corpo["entreguesNoPrazo"] == 1 and corpo["entreguesEmAtraso"] == 0
    assert corpo["participacaoPorEtapa"] == [{"id": "Criação", "label": "Criação", "value": 1}]


def test_prazo_vai_ate_o_fim_do_dia_no_fuso_da_aplicacao_e_sem_prazo_e_atraso(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Fronteira: prazo 09/03 → vale até 23:59:59.999999 de São Paulo (= 10/03 02:59:59.999999Z).
    Um instante depois (03:00Z = 00:00 de 10/03 local) já é atraso. Sem `data_fim_prevista`,
    atraso. Demanda não concluída não é entrega."""
    ana = _usuario(db_session, empresa, "Ana")
    _demanda_com_prazo(db_session, empresa, ana, "concluida", date(2026, 3, 9), datetime(2026, 3, 10, 2, 59, 59, 999999, tzinfo=timezone.utc))
    _demanda_com_prazo(db_session, empresa, ana, "concluida", date(2026, 3, 9), datetime(2026, 3, 10, 3, 0, 0, tzinfo=timezone.utc))
    _demanda_com_prazo(db_session, empresa, ana, "concluida", date(2026, 3, 9), datetime(2026, 3, 9, 3, 0, 0, tzinfo=timezone.utc))
    _demanda_com_prazo(db_session, empresa, ana, "concluida", None, datetime(2026, 3, 1, tzinfo=timezone.utc))
    _demanda_com_prazo(db_session, empresa, ana, "em_execucao", date(2026, 3, 9), datetime(2026, 3, 1, tzinfo=timezone.utc))
    _demanda_com_prazo(db_session, empresa, ana, "cancelada", date(2026, 3, 9), datetime(2026, 3, 1, tzinfo=timezone.utc))
    corpo = _performance(client_admin, ana.id)
    assert (corpo["demandasEntregues"], corpo["entreguesNoPrazo"], corpo["entreguesEmAtraso"]) == (4, 2, 2)


def test_multiplos_responsaveis_a_demanda_conta_para_cada_um_sem_dividir(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Regra do frontend antigo (`usuarioResponsavelIds.includes`): double-count INTENCIONAL —
    uma Demanda com 2 responsáveis é 1 entrega para cada, não 1 no total nem 0,5 cada."""
    ana, bruno, carla = (_usuario(db_session, empresa, nome) for nome in ("Ana", "Bruno", "Carla"))
    compartilhada = _demanda_com_prazo(db_session, empresa, None, "concluida", date(2026, 3, 20), datetime(2026, 3, 10, tzinfo=timezone.utc))
    for usuario in (ana, bruno):
        db_session.add(DemandaResponsavel(demanda_id=compartilhada.id, usuario_id=usuario.id, created_at=BASE))
    db_session.flush()
    _etapa(db_session, compartilhada, 1, "Redação", [ana, bruno])

    for usuario in (ana, bruno):
        corpo = _performance(client_admin, usuario.id)
        assert (corpo["demandasEntregues"], corpo["entreguesNoPrazo"]) == (1, 1)
        assert corpo["participacaoPorEtapa"] == [{"id": "Redação", "label": "Redação", "value": 1}]
    assert _performance(client_admin, carla.id)["demandasEntregues"] == 0


def test_participacao_por_etapa_regras(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    """Só conta etapa em que ele é responsável DA ETAPA e dentro de Demanda em que ele também é
    responsável da DEMANDA; nomes iguais somam; ordem = primeira aparição (Demandas por
    `numero_operacional DESC`, etapas por `ordem`)."""
    ana, bruno = _usuario(db_session, empresa, "Ana"), _usuario(db_session, empresa, "Bruno")
    d1 = _demanda(db_session, empresa, None, numero=10, responsaveis=[ana])  # mais antiga
    d2 = _demanda(db_session, empresa, None, numero=20, responsaveis=[ana, bruno])
    d3 = _demanda(db_session, empresa, None, numero=30, responsaveis=[bruno])  # Ana NÃO é responsável
    d4 = _demanda(db_session, empresa, None, numero=15, responsaveis=[ana], status="arquivada")
    _etapa(db_session, d1, 1, "Revisão", [ana])
    _etapa(db_session, d1, 2, "Aprovação", [ana])
    _etapa(db_session, d2, 1, "Criação", [ana, bruno])
    _etapa(db_session, d2, 2, "Revisão", [ana])
    _etapa(db_session, d2, 3, "Revisão", [ana])  # mesmo nome na MESMA demanda: conta 2
    _etapa(db_session, d2, 4, "Publicação", [bruno])  # Ana não é responsável da etapa
    _etapa(db_session, d3, 1, "Fantasma", [ana])  # etapa dela, demanda de outro: fora
    _etapa(db_session, d4, 1, "Arquivada", [ana])  # demanda arquivada: fora
    corpo = _performance(client_admin, ana.id)
    # d2 (número 20) vem antes de d1 (10): Criação, Revisão (x3: d2 duas + d1 uma), Aprovação.
    assert [(f["label"], f["value"]) for f in corpo["participacaoPorEtapa"]] == [("Criação", 1), ("Revisão", 3), ("Aprovação", 1)]


def test_performance_ignora_arquivada_outra_empresa_e_demanda_de_outros(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    ana, bruno = _usuario(db_session, empresa, "Ana"), _usuario(db_session, empresa, "Bruno")
    alheio = _usuario(db_session, outra_empresa, "Alheio")
    _demanda_com_prazo(db_session, empresa, ana, "concluida", date(2026, 3, 20), datetime(2026, 3, 10, tzinfo=timezone.utc))
    _demanda_com_prazo(db_session, empresa, ana, "arquivada", date(2026, 3, 20), datetime(2026, 3, 10, tzinfo=timezone.utc))
    _demanda_com_prazo(db_session, empresa, bruno, "concluida", date(2026, 3, 20), datetime(2026, 3, 10, tzinfo=timezone.utc))
    # Linha (impossível pela API) da outra empresa com o responsável da empresa: defesa em profundidade.
    intrusa = _demanda(db_session, outra_empresa, None, status="concluida", responsaveis=[ana, alheio])
    assert intrusa.empresa_id != empresa.id
    assert _performance(client_admin, ana.id)["demandasEntregues"] == 1


def test_usuario_inativo_e_arquivado_tem_performance(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    for status in ("inativo", "bloqueado", "arquivado"):
        antigo = _usuario(db_session, empresa, f"Antigo {status}", status=status)
        _demanda_com_prazo(db_session, empresa, antigo, "concluida", None, BASE)
        assert _performance(client_admin, antigo.id)["demandasEntregues"] == 1


def test_performance_respeita_o_escopo_resolvido(
    client_admin: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    from app.core.escopo import EscopoDemanda
    from app.repositories.relatorio_repository import RelatorioRepository

    ana = _usuario(db_session, empresa, "Ana")
    _demanda(db_session, empresa, None, status="concluida", responsaveis=[ana, usuario_operador])
    _demanda(db_session, empresa, None, status="concluida", responsaveis=[ana])
    repo = RelatorioRepository()
    total = EscopoDemanda(empresa_id=empresa.id, usuario_id=usuario_operador.id, visao_total=True)
    meus = EscopoDemanda(empresa_id=empresa.id, usuario_id=usuario_operador.id, visao_total=False, usuario_responsavel=True)
    vazio = EscopoDemanda(empresa_id=empresa.id, usuario_id=usuario_operador.id, visao_total=False)
    assert repo.performance_colaborador(db_session, escopo=total, colaborador_id=ana.id, fuso="UTC")["entregues"] == 2
    assert repo.performance_colaborador(db_session, escopo=meus, colaborador_id=ana.id, fuso="UTC")["entregues"] == 1
    assert repo.performance_colaborador(db_session, escopo=vazio, colaborador_id=ana.id, fuso="UTC")["entregues"] == 0
    assert repo.abertas_por_projeto(db_session, escopo=vazio, cliente_id=str(uuid.uuid4())) == []
    assert repo.volume_semanal(db_session, escopo=vazio, primeira_semana=date(2026, 1, 5), fim_exclusivo=date(2026, 1, 12), fuso="UTC") == {}


def test_performance_acima_de_200_nao_trunca(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    """O colaborador ALVO tem 240 Demandas ANTIGAS (concluídas, sendo 60 em atraso) e 60 outras
    Demandas MAIS RECENTES de outra pessoa empurram as dele para fora da janela de 200 do
    `GET /demandas`: a lógica antiga contaria só as 200 mais novas (60 + 140)."""
    alvo, outro = _usuario(db_session, empresa, "Alvo"), _usuario(db_session, empresa, "Outro")
    numero = 1
    for i in range(240):
        demanda = _demanda_com_prazo(
            db_session, empresa, alvo, "concluida", date(2026, 3, 10),
            datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc) if i % 4 else datetime(2026, 3, 12, 12, 0, tzinfo=timezone.utc),
            numero=numero,
        )
        _etapa(db_session, demanda, 1, "Criação" if i % 2 else "Revisão", [alvo])
        numero += 1
    for _ in range(60):
        _demanda(db_session, empresa, None, numero=numero, responsaveis=[outro])
        numero += 1
    corpo = _performance(client_admin, alvo.id)
    assert (corpo["demandasEntregues"], corpo["entreguesNoPrazo"], corpo["entreguesEmAtraso"]) == (240, 180, 60)
    assert {f["label"]: f["value"] for f in corpo["participacaoPorEtapa"]} == {"Criação": 120, "Revisão": 120}


# --------------------------------------------------------------------------------------
# Gráfico — abertas por projeto
# --------------------------------------------------------------------------------------


def test_abertas_so_os_seis_status_abertos(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(client_admin)
    projeto = _projeto_de(client_admin, cliente["id"], "Campanha")
    for status in STATUS_TODOS:
        _demanda(db_session, empresa, projeto["id"], status=status)
    assert _abertas(client_admin, cliente["id"]) == [{"id": projeto["id"], "label": "Campanha", "value": 6}]


def test_abertas_regras_de_projeto_e_cliente(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente, outro_cliente = _cliente(client_admin), _cliente(client_admin)
    p_b = _projeto_de(client_admin, cliente["id"], "Beta")
    p_a = _projeto_de(client_admin, cliente["id"], "Alfa")
    p_vazio = _projeto_de(client_admin, cliente["id"], "Gama sem demanda")
    p_fechado = _projeto_de(client_admin, cliente["id"], "Delta só concluída")
    p_alheio = _projeto_de(client_admin, outro_cliente["id"], "Omega")
    p_interno = _projeto_de(client_admin, None, "Interno")
    for projeto, quantidade in ((p_b, 2), (p_a, 3), (p_alheio, 4), (p_interno, 5)):
        for _ in range(quantidade):
            _demanda(db_session, empresa, projeto["id"])
    _demanda(db_session, empresa, p_fechado["id"], status="concluida")
    _demanda(db_session, empresa, None)  # sem projeto: não entra em nenhuma fatia
    assert [(f["label"], f["value"]) for f in _abertas(client_admin, cliente["id"])] == [("Alfa", 3), ("Beta", 2)]
    assert p_vazio["id"] not in [f["id"] for f in _abertas(client_admin, cliente["id"])]


def test_abertas_cliente_sem_projetos_e_lista_vazia(client_admin: TestClient) -> None:
    assert _abertas(client_admin, _cliente(client_admin)["id"]) == []


def test_abertas_projeto_alem_da_antiga_janela_aparece(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(client_admin)
    antigo = _projeto_de(client_admin, cliente["id"], "Antigo")
    grande = _projeto_de(client_admin, cliente["id"], "Grande")
    ruido = _projeto_de(client_admin, None, "Ruido")
    numero = 1
    for _ in range(12):  # as mais antigas de todas: fora das 200 mais recentes da empresa
        _demanda(db_session, empresa, antigo["id"], numero=numero)
        numero += 1
    for _ in range(250):
        _demanda(db_session, empresa, grande["id"], numero=numero)
        numero += 1
    for _ in range(60):
        _demanda(db_session, empresa, ruido["id"], numero=numero)
        numero += 1
    assert [(f["label"], f["value"]) for f in _abertas(client_admin, cliente["id"])] == [("Antigo", 12), ("Grande", 250)]


# --------------------------------------------------------------------------------------
# Gráfico — volume por projeto e colaborador
# --------------------------------------------------------------------------------------


def test_volume_vazio_sem_projetos(client_admin: TestClient) -> None:
    assert _volume(client_admin) == []


def test_volume_todos_os_projetos_inclusive_sem_demanda_e_arquivado_em_ordem_de_nome(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    ana = _usuario(db_session, empresa, "Ana")
    p_b = _projeto_de(client_admin, None, "Beta")
    p_a = _projeto_de(client_admin, None, "Alfa")
    p_arquivado = _projeto_de(client_admin, None, "Zeta arquivado")
    assert client_admin.post(f"/projetos/{p_arquivado['id']}/arquivar", json={"motivoArquivamento": "teste"}).status_code in (200, 204)
    _demanda(db_session, empresa, p_b["id"], responsaveis=[ana])
    serie = _volume(client_admin)
    assert [s["categoria"] for s in serie] == ["Alfa", "Beta", "Zeta arquivado"]
    assert serie[0]["segmentos"] == [] and serie[2]["segmentos"] == []
    assert serie[1] == {"categoria": "Beta", "categoriaId": p_b["id"], "segmentos": [{"seriesId": ana.id, "label": "Ana", "value": 1}]}
    assert p_a["id"] == serie[0]["categoriaId"]


def test_volume_multiplos_responsaveis_conta_para_cada_um(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    """Mesma regra do relatório antigo: a Demanda entra no segmento de CADA responsável
    (double-count intencional — a soma das barras pode passar do total de Demandas)."""
    ana, bruno = _usuario(db_session, empresa, "Ana"), _usuario(db_session, empresa, "Bruno")
    projeto = _projeto_de(client_admin, None, "P")
    _demanda(db_session, empresa, projeto["id"], responsaveis=[ana, bruno])
    _demanda(db_session, empresa, projeto["id"], responsaveis=[bruno])
    segmentos = _volume(client_admin)[0]["segmentos"]
    assert [(s["label"], s["value"]) for s in segmentos] == [("Ana", 1), ("Bruno", 2)]


def test_volume_regras_de_universo(client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    ana = _usuario(db_session, empresa, "Ana")
    sistema = _usuario(db_session, empresa, "Sistema")
    sistema.is_system_account = True
    alheio = _usuario(db_session, outra_empresa, "Alheio")
    db_session.flush()
    projeto = _projeto_de(client_admin, None, "P")
    for status in STATUS_TODOS:  # qualquer status entra; arquivada não
        _demanda(db_session, empresa, projeto["id"], status=status, responsaveis=[ana])
    _demanda(db_session, empresa, projeto["id"], responsaveis=[sistema, alheio])
    _demanda(db_session, empresa, projeto["id"])  # sem responsável: nenhum segmento
    _demanda(db_session, empresa, None, responsaveis=[ana])  # sem projeto: fora
    assert [(s["label"], s["value"]) for s in _volume(client_admin)[0]["segmentos"]] == [("Ana", 8)]


def test_volume_usuario_inativo_continua_aparecendo(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    antigo = _usuario(db_session, empresa, "Antigo", status="arquivado")
    projeto = _projeto_de(client_admin, None, "P")
    _demanda(db_session, empresa, projeto["id"], responsaveis=[antigo])
    assert [s["label"] for s in _volume(client_admin)[0]["segmentos"]] == ["Antigo"]


def test_volume_acima_de_200_completo(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    ana, bruno = _usuario(db_session, empresa, "Ana"), _usuario(db_session, empresa, "Bruno")
    antigo = _projeto_de(client_admin, None, "Antigo")
    grande = _projeto_de(client_admin, None, "Grande")
    ruido = _projeto_de(client_admin, None, "Ruido")
    numero = 1
    for _ in range(10):
        _demanda(db_session, empresa, antigo["id"], numero=numero, responsaveis=[bruno])
        numero += 1
    for i in range(250):
        _demanda(db_session, empresa, grande["id"], numero=numero, responsaveis=[ana] if i % 2 else [ana, bruno])
        numero += 1
    for _ in range(60):
        _demanda(db_session, empresa, ruido["id"], numero=numero, responsaveis=[bruno])
        numero += 1
    por_projeto = {s["categoria"]: {x["label"]: x["value"] for x in s["segmentos"]} for s in _volume(client_admin)}
    assert por_projeto == {"Antigo": {"Bruno": 10}, "Grande": {"Ana": 250, "Bruno": 125}, "Ruido": {"Bruno": 60}}


# --------------------------------------------------------------------------------------
# Gráfico — volume semanal
# --------------------------------------------------------------------------------------

# Quarta 11/03/2026 10:00 em São Paulo; semana corrente = segunda 09/03; janela = 12 semanas,
# da segunda 22/12/2025 até a semana de 09/03/2026 (a corrente).
AGORA = datetime(2026, 3, 11, 10, 0, tzinfo=FUSO)


def _local(ano: int, mes: int, dia: int, hora: int = 0, minuto: int = 0, segundo: int = 0, micro: int = 0) -> datetime:
    return datetime(ano, mes, dia, hora, minuto, segundo, micro, tzinfo=FUSO).astimezone(timezone.utc)


def test_semanal_sempre_12_semanas_em_ordem_com_zeros(
    client_admin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixar_agora(monkeypatch, AGORA)
    pontos = _semanal(client_admin)
    assert len(pontos) == 12
    assert pontos[0]["inicioSemana"] == "2025-12-22" and pontos[-1]["inicioSemana"] == "2026-03-09"
    assert all(p["value"] == 0 for p in pontos)
    datas = [date.fromisoformat(p["inicioSemana"]) for p in pontos]
    assert all(d.weekday() == 0 for d in datas) and datas == sorted(datas)


def test_semanal_fronteiras_de_semana_no_fuso_da_aplicacao(
    client_admin: TestClient, db_session: Session, empresa: Empresa, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixar_agora(monkeypatch, AGORA)
    # Primeiro instante da janela conta (semana 0); 1µs antes, não.
    _demanda(db_session, empresa, None, criada=_local(2025, 12, 22))
    _demanda(db_session, empresa, None, criada=_local(2025, 12, 22) - timedelta(microseconds=1))
    # Domingo 23:00 local (= segunda 02:00Z) pertence à semana ANTERIOR; segunda 00:00 local, à seguinte.
    _demanda(db_session, empresa, None, criada=_local(2026, 1, 4, 23))
    _demanda(db_session, empresa, None, criada=_local(2026, 1, 5))
    # Fim da semana corrente conta; a segunda seguinte (futuro) não.
    _demanda(db_session, empresa, None, criada=_local(2026, 3, 15, 23, 59, 59, 999999))
    _demanda(db_session, empresa, None, criada=_local(2026, 3, 16))
    por_semana = {p["inicioSemana"]: p["value"] for p in _semanal(client_admin)}
    assert por_semana["2025-12-22"] == 1
    assert por_semana["2025-12-29"] == 1  # o domingo 04/01 23:00 local
    assert por_semana["2026-01-05"] == 1
    assert por_semana["2026-03-09"] == 1
    assert sum(por_semana.values()) == 4


def test_semanal_conta_qualquer_status_e_projeto_menos_arquivada(
    client_admin: TestClient, db_session: Session, empresa: Empresa, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixar_agora(monkeypatch, AGORA)
    projeto = _projeto_de(client_admin, None, "P")
    for status in STATUS_TODOS:
        _demanda(db_session, empresa, projeto["id"], status=status, criada=_local(2026, 3, 10, 9))
    _demanda(db_session, empresa, None, criada=_local(2026, 3, 10, 9))
    assert _semanal(client_admin)[-1]["value"] == 9  # 8 não arquivadas + 1 sem projeto


def test_semanal_tenant_e_acima_de_200_numa_semana(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixar_agora(monkeypatch, AGORA)
    for i in range(250):
        _demanda(db_session, empresa, None, criada=_local(2026, 2, 3, 8) + timedelta(minutes=i))
    _demanda(db_session, outra_empresa, None, criada=_local(2026, 2, 3, 9))
    por_semana = {p["inicioSemana"]: p["value"] for p in _semanal(client_admin)}
    assert por_semana["2026-02-02"] == 250 and sum(por_semana.values()) == 250


def _volume_semanal_antigo(criadas: list[datetime], agora: datetime, semanas: int = 12) -> list[tuple[str, int]]:
    """Porte de `volumeSemanal` (lib/relatorios.ts): semanas segunda→segunda no fuso local."""
    hoje = agora.astimezone(FUSO)
    inicio_corrente = (hoje - timedelta(days=hoje.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    pontos = []
    for indice in range(semanas - 1, -1, -1):
        inicio = inicio_corrente - timedelta(days=7 * indice)
        fim = inicio + timedelta(days=7)
        pontos.append((inicio.date().isoformat(), sum(1 for criada in criadas if inicio <= criada < fim)))
    return pontos


def test_paridade_semanal_com_a_logica_antiga(
    client_admin: TestClient, db_session: Session, empresa: Empresa, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixar_agora(monkeypatch, AGORA)
    criadas = [_local(2025, 12, 22), _local(2025, 12, 21, 23, 59), _local(2026, 1, 11, 22), _local(2026, 1, 12), _local(2026, 2, 28, 12),
               _local(2026, 3, 9), _local(2026, 3, 11, 9, 59), _local(2026, 3, 11, 10, 1), _local(2026, 3, 15, 23, 59), _local(2026, 4, 1)]
    criadas += [_local(2026, 2, 17, 8) + timedelta(hours=h) for h in range(30)]
    for criada in criadas:
        _demanda(db_session, empresa, None, criada=criada)
    esperado = _volume_semanal_antigo(criadas, AGORA)
    obtido = [(p["inicioSemana"], p["value"]) for p in _semanal(client_admin)]
    assert obtido == esperado


# --------------------------------------------------------------------------------------
# Paridade — Performance / Abertas / Volume com a lógica antiga portada
# --------------------------------------------------------------------------------------


def _ler(db: Session, empresa: Empresa):
    demandas = sorted(
        db.scalars(select(Demanda).where(Demanda.empresa_id == empresa.id, Demanda.status != "arquivada")).all(),
        key=lambda d: d.numero_operacional, reverse=True,
    )
    responsaveis: dict[str, list[str]] = {d.id: [] for d in demandas}
    for demanda_id, usuario_id in db.execute(select(DemandaResponsavel.demanda_id, DemandaResponsavel.usuario_id)):
        if demanda_id in responsaveis:
            responsaveis[demanda_id].append(usuario_id)
    etapas: dict[str, list[tuple[str, list[str]]]] = {d.id: [] for d in demandas}
    for etapa in db.scalars(select(DemandaWorkflowEtapa).order_by(DemandaWorkflowEtapa.demanda_id, DemandaWorkflowEtapa.ordem)).all():
        if etapa.demanda_id in etapas:
            donos = list(db.scalars(select(DemandaWorkflowEtapaResponsavel.usuario_id).where(
                DemandaWorkflowEtapaResponsavel.demanda_workflow_etapa_id == etapa.id)))
            etapas[etapa.demanda_id].append((etapa.nome, donos))
    return demandas, responsaveis, etapas


def _performance_antiga(demandas, responsaveis, etapas, colaborador_id: str) -> dict:
    """Porte de `analisarPerformanceColaborador` (lib/relatorios.ts)."""
    dele = [d for d in demandas if colaborador_id in responsaveis[d.id]]
    entregues = [d for d in dele if d.status == "concluida"]

    def no_prazo(d: Demanda) -> bool:
        if d.data_fim_prevista is None:
            return False
        fim = datetime(d.data_fim_prevista.year, d.data_fim_prevista.month, d.data_fim_prevista.day, 23, 59, 59, 999000, tzinfo=FUSO)
        return d.updated_at.replace(microsecond=d.updated_at.microsecond // 1000 * 1000) <= fim

    n_prazo = sum(1 for d in entregues if no_prazo(d))
    contagem: dict[str, int] = {}
    for d in dele:
        for nome, donos in etapas[d.id]:
            if colaborador_id in donos:
                contagem[nome] = contagem.get(nome, 0) + 1
    return {"entregues": len(entregues), "no_prazo": n_prazo, "atraso": len(entregues) - n_prazo, "etapas": list(contagem.items())}


def test_paridade_performance_com_a_logica_antiga(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    ana, bruno, carla = (_usuario(db_session, empresa, nome) for nome in ("Ana", "Bruno", "Carla"))
    projeto = _projeto_de(client_admin, None, "P")
    cenarios = [
        ("concluida", date(2026, 3, 9), datetime(2026, 3, 10, 2, 59, 59, 999999, tzinfo=timezone.utc), [ana, bruno], [("Criação", [ana]), ("Revisão", [ana, bruno])]),
        ("concluida", date(2026, 3, 9), datetime(2026, 3, 10, 3, 0, tzinfo=timezone.utc), [ana], [("Revisão", [ana])]),
        ("concluida", None, BASE, [ana, carla], [("Criação", [carla])]),
        ("em_execucao", date(2026, 3, 9), BASE, [ana], [("Aprovação", [ana]), ("Criação", [ana])]),
        ("cancelada", date(2026, 3, 9), BASE, [ana], []),
        ("concluida", date(2026, 4, 1), datetime(2026, 3, 20, tzinfo=timezone.utc), [bruno], [("Criação", [bruno])]),
        ("concluida", date(2026, 3, 1), datetime(2026, 3, 20, tzinfo=timezone.utc), [], [("Criação", [ana])]),
    ]
    for status, fim, atualizada, donos, passos in cenarios:
        demanda = _demanda_com_prazo(db_session, empresa, None, status, fim, atualizada, projeto_id=projeto["id"])
        for dono in donos:
            db_session.add(DemandaResponsavel(demanda_id=demanda.id, usuario_id=dono.id, created_at=BASE))
        db_session.flush()
        for ordem, (nome, responsaveis_etapa) in enumerate(passos, start=1):
            _etapa(db_session, demanda, ordem, nome, responsaveis_etapa)

    demandas, responsaveis, etapas = _ler(db_session, empresa)
    for usuario in (ana, bruno, carla):
        esperado = _performance_antiga(demandas, responsaveis, etapas, usuario.id)
        obtido = _performance(client_admin, usuario.id)
        assert obtido["demandasEntregues"] == esperado["entregues"], usuario.nome
        assert obtido["entreguesNoPrazo"] == esperado["no_prazo"], usuario.nome
        assert obtido["entreguesEmAtraso"] == esperado["atraso"], usuario.nome
        assert [(f["label"], f["value"]) for f in obtido["participacaoPorEtapa"]] == esperado["etapas"], usuario.nome


def test_paridade_abertas_e_volume_com_a_logica_antiga(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    usuarios = [_usuario(db_session, empresa, nome) for nome in ("Ana", "Bruno", "Carla")]
    cliente = _cliente(client_admin)
    projetos = [_projeto_de(client_admin, cliente["id"], nome) for nome in ("Beta", "Alfa")] + [_projeto_de(client_admin, None, "Interno")]
    numero = 1
    for projeto in projetos:
        for i, status in enumerate(STATUS_TODOS):
            _demanda(db_session, empresa, projeto["id"], status=status, numero=numero, responsaveis=usuarios[: (i % 3) + 1])
            numero += 1
    _demanda(db_session, empresa, None, numero=numero, responsaveis=usuarios)

    demandas, responsaveis, _ = _ler(db_session, empresa)
    abertas = {"rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"}
    nomes = {p["id"]: p["nome"] for p in projetos}

    # `demandasAbertasPorProjeto`: projetos do cliente por nome, valor>0.
    esperado_pizza = [
        (nomes[p["id"]], sum(1 for d in demandas if d.projeto_id == p["id"] and d.status in abertas))
        for p in sorted([p for p in projetos if p.get("clienteId") == cliente["id"]], key=lambda p: p["nome"])
    ]
    assert [(f["label"], f["value"]) for f in _abertas(client_admin, cliente["id"])] == [x for x in esperado_pizza if x[1] > 0]

    # `volumePorProjetoEColaborador`: todos os projetos por nome; usuários por nome com valor>0.
    esperado_volume = [
        (p["nome"], [(u.nome, n) for u in sorted(usuarios, key=lambda u: u.nome)
                     if (n := sum(1 for d in demandas if d.projeto_id == p["id"] and u.id in responsaveis[d.id])) > 0])
        for p in sorted(projetos, key=lambda p: p["nome"])
    ]
    obtido = [(s["categoria"], [(x["label"], x["value"]) for x in s["segmentos"]]) for s in _volume(client_admin)]
    assert obtido == esperado_volume


# --------------------------------------------------------------------------------------
# Sem N+1
# --------------------------------------------------------------------------------------


def _consultas(app, db_session: Session, token: str, url: str) -> int:
    """Statements do relatório: os que tocam Demanda/responsáveis/projetos ou listam usuários
    ordenados (a autenticação do request só lê `usuarios` por id e não entra)."""
    chamadas: list[str] = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if any(marca in statement for marca in ("demandas", "demanda_responsaveis", "FROM projetos", "ORDER BY usuarios.nome")):
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = get(TestClient(app), url, token=token)
    finally:
        event.remove(engine, "before_cursor_execute", _contar)
    assert resposta.status_code == 200, resposta.text
    return len(chamadas)


def test_numero_de_consultas_constante(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa, token_admin: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixar_agora(monkeypatch, AGORA)
    cliente = _cliente(client_admin)
    ana = _usuario(db_session, empresa, "Ana")
    projeto = _projeto_de(client_admin, cliente["id"], "P0")
    demanda = _demanda_com_prazo(db_session, empresa, ana, "concluida", date(2026, 3, 20), BASE, projeto_id=projeto["id"])
    _etapa(db_session, demanda, 1, "Criação", [ana])
    urls = [
        "/relatorios/colaboradores",
        f"/relatorios/colaboradores/performance?colaboradorId={ana.id}",
        f"/relatorios/graficos/abertas-por-projeto?clienteId={cliente['id']}",
        "/relatorios/graficos/volume-por-colaborador",
        "/relatorios/graficos/volume-semanal",
    ]
    poucas = [_consultas(app, db_session, token_admin, url) for url in urls]

    usuarios = [ana] + [_usuario(db_session, empresa) for _ in range(12)]
    for i in range(10):
        extra = _projeto_de(client_admin, cliente["id"], f"P{i + 1}")
        for j in range(6):
            d = _demanda_com_prazo(db_session, empresa, usuarios[(i + j) % 13], "concluida" if j % 2 else "pausada",
                                   date(2026, 3, 20), BASE + timedelta(days=j), projeto_id=extra["id"])
            if usuarios[(i + j) % 13].id != ana.id:
                db_session.add(DemandaResponsavel(demanda_id=d.id, usuario_id=ana.id, created_at=BASE))
                db_session.flush()
            _etapa(db_session, d, 1, f"Etapa {j % 3}", [usuarios[(i + j) % 13]])
            _etapa(db_session, d, 2, "Criação", [ana])
    muitas = [_consultas(app, db_session, token_admin, url) for url in urls]

    assert poucas == muitas
    assert muitas == [1, 2, 1, 2, 1]  # colaboradores; entregas+etapas; pizza; projetos+pares; semanas
