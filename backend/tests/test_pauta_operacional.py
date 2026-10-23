"""P1_PAUTA_COLABORADOR — `GET /pauta/operacional`: a Pauta por ETAPA (responsabilidade efetiva + janela planejada). Dados sintéticos (ORM direto); o "agora" do serviço é injetado.

Prova, pela API real: autorização da Pauta global, itens neutros por etapa, a regra central de responsabilidade (fallback dinâmico, explícito bloqueia o fallback, departamento sem usuário, ninguém),
multi-responsável (um item só, nos dois colaboradores via filtro), baldes de planejamento (planejado / incompleto / não planejado), prazo NUNCA como geometria, período, status terminais, filtros pela
responsabilidade EFETIVA, equivalência SQL × regra pura, tetos por balde e custo constante de consultas.
"""

from __future__ import annotations

import itertools
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, select
from sqlalchemy.orm import Session

from app.core.executor_etapa import resolver_responsabilidade_etapa
from app.models.demanda import Demanda
from app.models.demanda_departamento import DemandaDepartamento
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from tests.test_carga_semanal_api import AGORA, SEG, etapa_carga, pessoa
from tests.test_d1_2a_cliente_projeto import _projeto
from tests.test_demanda import _cliente
from tests.test_sessao_trabalho import _departamento
from tests.test_trafego_v2_metricas import _demanda, _etapa, _resp_demanda

_SEQ = itertools.count(1)
D = lambda dia: SEG + timedelta(days=dia - 19)  # noqa: E731  (dia de outubro/2026: 22 → quinta)


@pytest.fixture(autouse=True)
def relogio(monkeypatch):
    monkeypatch.setattr("app.services.pauta_operacional_service.agora_utc", lambda: AGORA)


def pauta(cliente: TestClient, **params):
    return cliente.get("/pauta/operacional", params={chave: valor for chave, valor in params.items() if valor is not None})


def item_da_etapa(corpo: dict, etapa_id: str) -> dict | None:
    return next((i for i in corpo["itens"] if i["etapaId"] == etapa_id), None)


def ids_das_etapas(corpo: dict) -> set[str]:
    return {i["etapaId"] for i in corpo["itens"]}


def dep_geral(db: Session, demanda: Demanda, departamento) -> None:
    db.add(DemandaDepartamento(demanda_id=demanda.id, departamento_id=departamento.id, created_at=datetime.now(timezone.utc)))
    db.flush()


def nova(db: Session, empresa, *, ini=D(22), fim=D(25), users=(), deps=(), geral=(), geral_deps=(), **demanda):
    d, e = etapa_carga(db, empresa, ini=ini, fim=fim, users=users, deps=deps, **demanda)
    for u in geral:
        _resp_demanda(db, d, u)
    for dep in geral_deps:
        dep_geral(db, d, dep)
    return d, e


# ── autorização / tenant ───────────────────────────────────────────────────────────────────────────────────────────


def test_admin_e_gestor_acessam_operador_403_e_sem_token_401(client_admin, client_gestor, client_operador, client) -> None:
    assert pauta(client_admin).status_code == 200
    assert pauta(client_gestor).status_code == 200
    assert pauta(client_operador).status_code == 403
    assert pauta(client).status_code == 401


def test_so_o_proprio_tenant_e_dados_de_outra_empresa_nunca_aparecem(client_admin, db_session, empresa, outra_empresa) -> None:
    alheio = pessoa(db_session, outra_empresa, nome="Pessoa de outra empresa")
    _, e_alheia = nova(db_session, outra_empresa, users=[alheio])
    corpo = pauta(client_admin, empresaId=str(outra_empresa.id)).json()  # parâmetro desconhecido é ignorado
    assert e_alheia.id not in ids_das_etapas(corpo) and alheio.id not in [p["id"] for p in corpo["pessoas"]]
    assert pauta(client_admin, usuarioIds="nao-e-uuid").status_code == 422
    assert pauta(client_admin, prioridades="urgente").status_code == 422


# ── responsabilidade efetiva ───────────────────────────────────────────────────────────────────────────────────────


def test_fallback_etapa_vazia_aparece_para_o_responsavel_geral(client_admin, db_session, empresa) -> None:
    milenna = pessoa(db_session, empresa, nome="Milenna")
    _, e = nova(db_session, empresa, geral=[milenna])
    corpo = pauta(client_admin).json()
    item = item_da_etapa(corpo, e.id)
    assert item["responsabilidadeEfetiva"] == {"origem": "tarefa", "usuarioIds": [milenna.id], "departamentoIds": []}
    assert item["planejamento"] == {"inicio": "2026-10-22", "fim": "2026-10-25", "estado": "planejado", "invalido": False}
    assert [(p["id"], p["nome"]) for p in corpo["pessoas"]] == [(milenna.id, "Milenna")]
    assert ids_das_etapas(pauta(client_admin, usuarioIds=milenna.id).json()) == {e.id}


def test_etapa_explicita_vence_e_o_responsavel_geral_nao_aparece_por_fallback(client_admin, db_session, empresa) -> None:
    milenna, raquel = pessoa(db_session, empresa, nome="Milenna"), pessoa(db_session, empresa, nome="Raquel")
    _, e = nova(db_session, empresa, users=[raquel], geral=[milenna])
    item = item_da_etapa(pauta(client_admin).json(), e.id)
    assert item["responsabilidadeEfetiva"] == {"origem": "etapa", "usuarioIds": [raquel.id], "departamentoIds": []}
    assert ids_das_etapas(pauta(client_admin, usuarioIds=raquel.id).json()) == {e.id}
    assert pauta(client_admin, usuarioIds=milenna.id).json()["itens"] == []  # o geral bruto da Demanda NÃO vale quando a etapa é explícita


def test_multiresponsavel_e_um_item_so_com_os_dois_e_aparece_no_filtro_de_cada_um(client_admin, db_session, empresa) -> None:
    raquel, joao = pessoa(db_session, empresa, nome="Raquel"), pessoa(db_session, empresa, nome="João")
    _, e = nova(db_session, empresa, users=[raquel, joao])
    corpo = pauta(client_admin).json()
    assert len(corpo["itens"]) == 1  # a Pauta não duplica nem rateia: quem agrupa é a interface
    assert sorted(corpo["itens"][0]["responsabilidadeEfetiva"]["usuarioIds"]) == sorted([raquel.id, joao.id])
    assert ids_das_etapas(pauta(client_admin, usuarioIds=raquel.id).json()) == {e.id}
    assert ids_das_etapas(pauta(client_admin, usuarioIds=joao.id).json()) == {e.id}
    assert corpo["itens"][0]["planejamento"]["inicio"] == "2026-10-22" and corpo["itens"][0]["planejamento"]["fim"] == "2026-10-25"  # a janela NÃO é dividida


def test_departamento_sem_usuario_nao_escolhe_ninguem_e_nao_herda_o_geral(client_admin, db_session, empresa) -> None:
    milenna = pessoa(db_session, empresa, nome="Milenna")
    criacao = _departamento(db_session, empresa)
    _, e = nova(db_session, empresa, deps=[criacao], geral=[milenna])
    item = item_da_etapa(pauta(client_admin).json(), e.id)
    assert item["responsabilidadeEfetiva"] == {"origem": "etapa", "usuarioIds": [], "departamentoIds": [criacao.id]}
    assert pauta(client_admin, usuarioIds=milenna.id).json()["itens"] == []
    assert ids_das_etapas(pauta(client_admin, departamentoIds=criacao.id).json()) == {e.id}


def test_sem_nenhuma_responsabilidade_continua_visivel(client_admin, db_session, empresa) -> None:
    _, e = nova(db_session, empresa)
    assert item_da_etapa(pauta(client_admin).json(), e.id)["responsabilidadeEfetiva"] == {"origem": "nenhuma", "usuarioIds": [], "departamentoIds": []}


def test_responsabilidade_dinamica_trocar_o_geral_move_o_item_sem_persistir_na_etapa(client_admin, db_session, empresa) -> None:
    milenna, joao = pessoa(db_session, empresa, nome="Milenna"), pessoa(db_session, empresa, nome="João")
    d, e = nova(db_session, empresa, geral=[milenna])
    assert ids_das_etapas(pauta(client_admin, usuarioIds=milenna.id).json()) == {e.id}
    db_session.execute(delete(DemandaResponsavel).where(DemandaResponsavel.demanda_id == d.id))
    _resp_demanda(db_session, d, joao)
    assert pauta(client_admin, usuarioIds=milenna.id).json()["itens"] == []
    assert ids_das_etapas(pauta(client_admin, usuarioIds=joao.id).json()) == {e.id}
    assert item_da_etapa(pauta(client_admin).json(), e.id)["responsabilidadeEfetiva"]["origem"] == "tarefa"


def test_filtro_de_departamento_usa_a_responsabilidade_efetiva_nao_o_cadastro_do_usuario(client_admin, db_session, empresa) -> None:
    criacao, arte = _departamento(db_session, empresa), _departamento(db_session, empresa)
    raquel = pessoa(db_session, empresa, dep=criacao, nome="Raquel")  # cadastrada em Criação…
    _, e = nova(db_session, empresa, users=[raquel], geral_deps=[arte])  # …mas a etapa é dela (sem departamento) e a tarefa é da Arte
    assert pauta(client_admin, departamentoIds=criacao.id).json()["itens"] == []
    assert pauta(client_admin, departamentoIds=arte.id).json()["itens"] == []  # etapa explícita só com usuário: o departamento geral não vale
    _, f = nova(db_session, empresa, geral_deps=[arte])  # etapa vazia herda o departamento geral
    assert ids_das_etapas(pauta(client_admin, departamentoIds=arte.id).json()) == {f.id}


# ── planejamento: baldes, prazo, período ───────────────────────────────────────────────────────────────────────────


def test_baldes_planejada_incompleta_e_nao_planejada(client_admin, db_session, empresa) -> None:
    _, plan = nova(db_session, empresa)
    _, inc = nova(db_session, empresa, ini=D(22), fim=None)
    _, nao = nova(db_session, empresa, ini=None, fim=None)
    corpo = pauta(client_admin).json()
    assert item_da_etapa(corpo, plan.id)["planejamento"]["estado"] == "planejado"
    assert item_da_etapa(corpo, inc.id)["planejamento"] == {"inicio": "2026-10-22", "fim": None, "estado": "incompleto", "invalido": False}
    assert item_da_etapa(corpo, nao.id)["planejamento"] == {"inicio": None, "fim": None, "estado": "nao_planejado", "invalido": False}
    assert [corpo["totais"][b]["total"] for b in ("planejadas", "incompletas", "naoPlanejadas")] == [1, 1, 1]


def test_prazo_diferente_nunca_vira_geometria(client_admin, db_session, empresa) -> None:
    prazo = datetime(2026, 10, 30, 21, 0, tzinfo=timezone.utc)
    _, e = nova(db_session, empresa, prazo=prazo)
    item = item_da_etapa(pauta(client_admin).json(), e.id)
    assert (item["planejamento"]["inicio"], item["planejamento"]["fim"]) == ("2026-10-22", "2026-10-25")  # nunca 22→30
    assert item["prazoEtapaAtual"].startswith("2026-10-30") and item["etapaAtual"] is True  # só informação secundária, só na etapa atual
    # sem planejamento, o prazo NÃO inventa janela
    _, sem = nova(db_session, empresa, ini=None, fim=None, prazo=prazo)
    assert item_da_etapa(pauta(client_admin).json(), sem.id)["planejamento"]["estado"] == "nao_planejado"


def test_periodo_recorta_planejadas_e_informa_antes_e_depois(client_admin, db_session, empresa) -> None:
    _, dentro = nova(db_session, empresa, ini=D(22), fim=D(25))
    _, cruza_inicio = nova(db_session, empresa, ini=D(10), fim=D(20))  # termina dentro do período
    _, antes = nova(db_session, empresa, ini=D(5), fim=D(10))
    _, depois = nova(db_session, empresa, ini=date(2026, 12, 1), fim=date(2026, 12, 3))
    corpo = pauta(client_admin, inicio="2026-10-19", fim="2026-11-15").json()
    assert ids_das_etapas(corpo) == {dentro.id, cruza_inicio.id}
    assert (corpo["totais"]["planejadasAntes"], corpo["totais"]["planejadasDepois"]) == (1, 1)
    assert antes.id not in ids_das_etapas(corpo) and depois.id not in ids_das_etapas(corpo)
    assert (corpo["meta"]["inicio"], corpo["meta"]["fim"], corpo["meta"]["hoje"]) == ("2026-10-19", "2026-11-15", "2026-10-19")
    padrao = pauta(client_admin).json()["meta"]
    assert (padrao["inicio"], padrao["fim"]) == ("2026-10-19", "2026-11-15")  # segunda da semana atual + 28 dias


def test_incompleta_entra_ate_o_fim_do_periodo_e_nao_planejada_entra_sempre(client_admin, db_session, empresa) -> None:
    _, antiga = nova(db_session, empresa, ini=D(1), fim=None)  # início passado, sem fim: ainda pendência
    _, futura = nova(db_session, empresa, ini=date(2027, 1, 10), fim=None)
    _, nao = nova(db_session, empresa, ini=None, fim=None)
    corpo = pauta(client_admin, inicio="2026-10-19", fim="2026-11-15").json()
    assert ids_das_etapas(corpo) == {antiga.id, nao.id}
    assert futura.id not in ids_das_etapas(corpo)


def test_validacao_do_periodo(client_admin) -> None:
    assert pauta(client_admin, inicio="2026-11-15", fim="2026-10-19").status_code == 422
    assert pauta(client_admin, inicio="2026-01-01", fim="2026-12-31").status_code == 422
    assert pauta(client_admin, inicio="2026-10-19", fim="2027-01-18").status_code == 200  # 92 dias


# ── universo ───────────────────────────────────────────────────────────────────────────────────────────────────────


def test_status_terminais_e_etapa_concluida_ficam_fora_e_etapas_futuras_entram(client_admin, db_session, empresa) -> None:
    for status in ("concluida", "cancelada", "arquivada"):
        _, fora = nova(db_session, empresa, status=status)
        assert fora.id not in ids_das_etapas(pauta(client_admin).json()), status
    d, e1 = nova(db_session, empresa)
    e1.status, e1.concluida_em = "concluida", datetime.now(timezone.utc)
    e2 = _etapa(db_session, d, 2, "Etapa 2")
    e2.planejado_inicio, e2.planejado_fim = D(28), D(30)
    e3 = _etapa(db_session, d, 3, "Etapa 3")
    e3.planejado_inicio, e3.planejado_fim = D(31), D(32)
    db_session.flush()
    corpo = pauta(client_admin).json()
    assert e1.id not in ids_das_etapas(corpo)
    assert (item_da_etapa(corpo, e2.id)["etapaAtual"], item_da_etapa(corpo, e3.id)["etapaAtual"]) == (True, False)  # a atual e as futuras planejadas


@pytest.mark.parametrize("ini,fim,balde", [(D(22), D(25), "planejadas"), (D(22), None, "incompletas"), (None, None, "naoPlanejadas")])
def test_rascunho_nao_entra_em_nenhum_balde_nem_nas_contagens(client_admin, db_session, empresa, ini, fim, balde) -> None:
    milenna = pessoa(db_session, empresa, nome="Milenna")
    d, e = nova(db_session, empresa, ini=ini, fim=fim, status="rascunho", geral=[milenna])
    corpo = pauta(client_admin).json()
    assert e.id not in ids_das_etapas(corpo) and corpo["itens"] == []
    assert corpo["totais"][balde] == {"total": 0, "devolvidos": 0, "truncado": False}  # nem escondido nas contagens
    assert ids_das_etapas(pauta(client_admin, usuarioIds=milenna.id).json()) == set()  # nem por filtro
    assert ids_das_etapas(pauta(client_admin, busca=d.nome).json()) == set()  # nem por busca
    assert corpo["pessoas"] == []


def test_rascunho_fora_das_contagens_antes_e_depois_do_periodo(client_admin, db_session, empresa) -> None:
    nova(db_session, empresa, ini=D(1), fim=D(5), status="rascunho")  # antes do período
    nova(db_session, empresa, ini=date(2026, 12, 1), fim=date(2026, 12, 3), status="rascunho")  # depois
    totais = pauta(client_admin, inicio="2026-10-19", fim="2026-11-15").json()["totais"]
    assert (totais["planejadasAntes"], totais["planejadasDepois"]) == (0, 0)
    nova(db_session, empresa, ini=D(1), fim=D(5), status="planejada")
    assert pauta(client_admin, inicio="2026-10-19", fim="2026-11-15").json()["totais"]["planejadasAntes"] == 1


def test_demanda_que_sai_do_rascunho_passa_a_aparecer_nos_tres_baldes(client_admin, db_session, empresa) -> None:
    milenna = pessoa(db_session, empresa, nome="Milenna")
    casos = [nova(db_session, empresa, ini=ini, fim=fim, status="rascunho", geral=[milenna]) for ini, fim in ((D(22), D(25)), (D(22), None), (None, None))]
    assert pauta(client_admin).json()["itens"] == []
    for demanda, _ in casos:
        demanda.status = "planejada"
    db_session.flush()
    corpo = pauta(client_admin).json()
    assert ids_das_etapas(corpo) == {etapa.id for _, etapa in casos}
    assert [corpo["totais"][b]["total"] for b in ("planejadas", "incompletas", "naoPlanejadas")] == [1, 1, 1]
    assert all(i["responsabilidadeEfetiva"]["usuarioIds"] == [milenna.id] for i in corpo["itens"])  # a responsabilidade não mudou com o status


@pytest.mark.parametrize("status", ["planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"])
def test_estados_operacionais_entram_e_terminais_e_rascunho_saem(client_admin, db_session, empresa, status) -> None:
    _, dentro = nova(db_session, empresa, status=status)
    assert dentro.id in ids_das_etapas(pauta(client_admin).json())


@pytest.mark.parametrize("status", ["rascunho", "concluida", "cancelada", "arquivada"])
def test_estados_fora_da_pauta(client_admin, db_session, empresa, status) -> None:
    _, fora = nova(db_session, empresa, status=status)
    assert fora.id not in ids_das_etapas(pauta(client_admin).json())


def test_filtros_cliente_projeto_prioridade_e_busca(client_admin, db_session, empresa) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)
    d1, e1 = nova(db_session, empresa, cliente_id=cliente.id, projeto_id=projeto.id, nome="Campanha de verão")
    d1.prioridade = "alta"
    _, e2 = nova(db_session, empresa, nome="Outra coisa")
    db_session.flush()
    assert ids_das_etapas(pauta(client_admin, clienteIds=cliente.id).json()) == {e1.id}
    assert ids_das_etapas(pauta(client_admin, projetoIds=projeto.id).json()) == {e1.id}
    assert ids_das_etapas(pauta(client_admin, prioridades="alta").json()) == {e1.id}
    assert ids_das_etapas(pauta(client_admin, busca="verão").json()) == {e1.id}
    assert ids_das_etapas(pauta(client_admin, busca="Demanda").json()) >= {e1.id, e2.id}
    assert pauta(client_admin, busca="100%_nada").json()["itens"] == []  # curingas são escapados
    assert item_da_etapa(pauta(client_admin, clienteIds=cliente.id).json(), e1.id)["projetoId"] == projeto.id


# ── equivalência SQL × regra pura ──────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("etapa_users,etapa_deps,geral_users,geral_deps", list(itertools.product([0, 1], repeat=4)))
def test_filtros_sql_equivalem_a_regra_pura_de_responsabilidade(client_admin, db_session, empresa, etapa_users, etapa_deps, geral_users, geral_deps) -> None:
    u_etapa, u_geral = pessoa(db_session, empresa), pessoa(db_session, empresa)
    d_etapa, d_geral = _departamento(db_session, empresa), _departamento(db_session, empresa)
    _, e = nova(
        db_session, empresa,
        users=[u_etapa] if etapa_users else [], deps=[d_etapa] if etapa_deps else [],
        geral=[u_geral] if geral_users else [], geral_deps=[d_geral] if geral_deps else [],
    )
    origem, usuarios, departamentos = resolver_responsabilidade_etapa(
        etapa_usuario_ids=[u_etapa.id] if etapa_users else [], etapa_departamento_ids=[d_etapa.id] if etapa_deps else [],
        demanda_usuario_ids=[u_geral.id] if geral_users else [], demanda_departamento_ids=[d_geral.id] if geral_deps else [],
    )
    corpo = pauta(client_admin).json()
    assert item_da_etapa(corpo, e.id)["responsabilidadeEfetiva"] == {"origem": origem, "usuarioIds": usuarios, "departamentoIds": departamentos}
    for candidato in (u_etapa, u_geral):
        no_filtro = e.id in ids_das_etapas(pauta(client_admin, usuarioIds=candidato.id).json())
        assert no_filtro == (candidato.id in usuarios), (origem, candidato.id)
    for candidato in (d_etapa, d_geral):
        no_filtro = e.id in ids_das_etapas(pauta(client_admin, departamentoIds=candidato.id).json())
        assert no_filtro == (candidato.id in departamentos), (origem, candidato.id)


# ── tetos, custo e somente leitura ─────────────────────────────────────────────────────────────────────────────────


def test_teto_por_balde_informa_o_total_real(client_admin, db_session, empresa, monkeypatch) -> None:
    monkeypatch.setattr("app.services.pauta_operacional_service.LIMITE_POR_BALDE", 3)
    for _ in range(5):
        nova(db_session, empresa)
    nova(db_session, empresa, ini=None, fim=None)
    corpo = pauta(client_admin).json()
    assert corpo["totais"]["planejadas"] == {"total": 5, "devolvidos": 3, "truncado": True}
    assert corpo["totais"]["naoPlanejadas"] == {"total": 1, "devolvidos": 1, "truncado": False}
    assert len(corpo["itens"]) == 4


def test_custo_constante_de_consultas_com_mais_etapas(client_admin, db_session, empresa) -> None:
    usuarios = [pessoa(db_session, empresa, nome=f"Pessoa {i}") for i in range(4)]
    deps = [_departamento(db_session, empresa) for _ in range(2)]

    def popular(qtd: int) -> None:
        for i in range(qtd):
            nova(db_session, empresa, users=usuarios[: (i % 3) + 1] if i % 2 else (), geral=[usuarios[3]] if i % 2 == 0 else (), geral_deps=[deps[i % 2]] if i % 4 == 0 else ())
            nova(db_session, empresa, ini=None, fim=None)

    def consultas() -> int:
        comandos: list[str] = []

        def capturar(conn, cursor, statement, parameters, context, executemany):
            comandos.append(statement)

        engine = db_session.get_bind()
        pauta(client_admin)  # aquece
        event.listen(engine, "before_cursor_execute", capturar)
        try:
            assert pauta(client_admin).status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", capturar)
        return len(comandos)

    popular(2)
    pouco = consultas()
    popular(60)
    muito = consultas()
    assert muito == pouco, (pouco, muito)


def test_leitura_nao_escreve(client_admin, db_session, empresa) -> None:
    _, e = nova(db_session, empresa, geral=[pessoa(db_session, empresa)])
    antes = db_session.execute(select(DemandaWorkflowEtapa.updated_at).where(DemandaWorkflowEtapa.id == e.id)).scalar_one()
    pauta(client_admin)
    pauta(client_admin, usuarioIds=str(e.id))
    depois = db_session.execute(select(DemandaWorkflowEtapa.updated_at).where(DemandaWorkflowEtapa.id == e.id)).scalar_one()
    assert antes == depois
