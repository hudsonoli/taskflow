"""Tráfego V2 — `GET /trafego/operacional/fluxo`: FLUXO POR ETAPA (somente leitura). Dados sintéticos (ORM direto); o "agora" do serviço é injetado.

Prova: a identidade semântica da etapa é a MESMA de Gargalos (mesma `chave`), o servidor agrupa as Demandas atuais por definição, `metricas.wip == itensTotal`, os limites cortam só cards/colunas (nunca os
totais), nada do tempo pessoal entra, RBAC/tenant, somente leitura, e o número de consultas não cresce com o volume. Os testes de métrica comparam com o endpoint Gargalos (oráculo independente), nunca com a
mesma função dos dois lados.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.demanda_status_intervalo import DemandaStatusIntervalo
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.evento import Evento
from app.models.sessao_trabalho import SessaoTrabalho
from tests.test_d1_2a_cliente_projeto import _projeto
from tests.test_demanda import _cliente
from tests.test_sessao_trabalho import _departamento, _usuario
from tests.test_trafego_v2_metricas import (  # noqa: F401  (relogio é fixture autouse do módulo de métricas: precisa estar no namespace)
    AGORA,
    _cenario_fila,
    _chaves,
    _contar_queries,
    _demanda,
    _dep_etapa,
    _etapa,
    _get,
    _intervalo,
    _popular_volume,
    _resp_etapa,
    _t,
    client_sem_token,
    relogio,
)


def fluxo(cliente, **params):
    return _get(cliente, "fluxo", **params)


def aberta(db: Session, empresa, *, status: str = "em_execucao", etapa: str = "Criação", deps=(), tipo: str = "execucao", inicio: datetime | None = None, prazo: datetime | None = None, **demanda):
    """Demanda ABERTA com UMA etapa atual e o intervalo aberto nessa etapa (como o motor mantém)."""
    d = _demanda(db, empresa, status=status, prazo=prazo, **demanda)
    e = _etapa(db, d, 1, etapa, tipo=tipo)
    for dep in deps:
        _dep_etapa(db, e, dep)
    _intervalo(db, d, status, inicio or (AGORA - timedelta(hours=2)), etapa=e)
    return d, e


def por_nome(corpo: dict, nome: str) -> list[dict]:
    return [d for d in corpo["definicoes"] if d["definicaoEtapa"]["nome"] == nome]


def sha(chave_normalizada: str, tipo: str, ids: list[str]) -> str:
    """Oráculo INDEPENDENTE do formato da chave (nome normalizado, tipo, ids ordenados). Fixa o contrato: se a identidade mudar, o teste quebra."""
    return hashlib.sha1(f"{chave_normalizada}\x1f{tipo}\x1f{','.join(sorted(ids))}".encode("utf-8")).hexdigest()  # noqa: S324


# ── vazio e contrato ─────────────────────────────────────────────────────────────────────────────────────────────


def test_empresa_sem_trabalho_aberto(client_admin, db_session, empresa) -> None:
    corpo = fluxo(client_admin).json()
    assert corpo["definicoes"] == [] and corpo["definicoesTotal"] == 0 and corpo["definicoesRetornadas"] == 0 and corpo["truncado"] is False
    assert corpo["atual"] == {"wip": 0, "planejadas": 0, "emExecucao": 0, "pausadas": 0, "bloqueadas": 0, "aguardandoCliente": 0}
    assert corpo["semEtapa"] == {"workflowConcluido": 0, "semWorkflow": 0}
    assert corpo["limiteDefinicoes"] == 100 and corpo["limiteItensPorDefinicao"] == 20 and corpo["filtros"] == {"departamentoId": None}
    assert corpo["coberturaParcial"] is True and corpo["medicaoDesde"] is None  # nada medido ainda


def test_uma_definicao_com_todos_os_status_do_wip_na_mesma_coluna(client_admin, db_session, empresa) -> None:
    status = ["em_execucao", "pausada", "bloqueada", "aguardando_cliente", "planejada"]
    demandas = {s: aberta(db_session, empresa, status=s, etapa="Criação")[0] for s in status}
    for excluido in ("rascunho", "concluida", "cancelada", "arquivada"):  # fora do WIP
        d = _demanda(db_session, empresa, status=excluido)
        e = _etapa(db_session, d, 1, "Criação")
        if excluido == "rascunho":
            _intervalo(db_session, d, "rascunho", AGORA - timedelta(hours=3), etapa=e)  # rascunho tem intervalo aberto, mas fora do WIP
        else:  # terminais não têm intervalo aberto: o último foi fechado
            _intervalo(db_session, d, "em_execucao", AGORA - timedelta(hours=5), AGORA - timedelta(hours=3), etapa=e)
    corpo = fluxo(client_admin).json()
    [definicao] = corpo["definicoes"]
    m = definicao["metricas"]
    assert (m["wip"], m["emExecucao"], m["pausadas"], m["bloqueadas"], m["aguardandoCliente"], m["planejadas"]) == (5, 1, 1, 1, 1, 1)
    assert {i["status"] for i in definicao["itens"]} == set(status)  # cada Demanda aparece com o seu status; a coluna é a ETAPA
    assert {i["demandaId"] for i in definicao["itens"]} == {d.id for d in demandas.values()}
    assert corpo["atual"]["wip"] == 5  # rascunho/concluída/cancelada/arquivada não são WIP
    assert definicao["itensTotal"] == m["wip"] == 5  # WIP == total de cards elegíveis
    assert definicao["itensRetornados"] == 5 and definicao["truncado"] is False


def test_invariantes_chave_do_item_demanda_unica_e_wip_igual_ao_total(client_admin, db_session, empresa) -> None:
    deps = [_departamento(db_session, empresa) for _ in range(2)]
    for i in range(12):
        aberta(db_session, empresa, status=["em_execucao", "pausada", "bloqueada"][i % 3], etapa=["Criação", "Revisão", "Arte"][i % 3], deps=[deps[i % 2]])
    corpo = fluxo(client_admin).json()
    todos = []
    for definicao in corpo["definicoes"]:
        assert definicao["itensTotal"] == definicao["metricas"]["wip"] == len(definicao["itens"])
        for item in definicao["itens"]:
            assert item["definicaoChave"] == definicao["definicaoEtapa"]["chave"]  # gerada pelo servidor, idêntica à da coluna
            assert item["etapaAtual"]["departamentos"] == definicao["definicaoEtapa"]["departamentos"]
            todos.append(item["demandaId"])
    assert len(todos) == len(set(todos)) == 12  # DEMAND_UNIQUE_IN_FLOW
    assert sum(d["metricas"]["wip"] for d in corpo["definicoes"]) + sum(corpo["semEtapa"].values()) == corpo["atual"]["wip"]


# ── identidade semântica ─────────────────────────────────────────────────────────────────────────────────────────


def test_mesmo_nome_com_departamentos_diferentes_sao_duas_colunas(client_admin, db_session, empresa) -> None:
    design, social = _departamento(db_session, empresa), _departamento(db_session, empresa)
    d1, _ = aberta(db_session, empresa, etapa="Criação", deps=[design])
    d2, _ = aberta(db_session, empresa, etapa="Criação", deps=[social], status="pausada")
    d3, _ = aberta(db_session, empresa, etapa="Criação", deps=[design], status="bloqueada")
    corpo = fluxo(client_admin).json()
    criacao = por_nome(corpo, "Criação")
    assert len(criacao) == 2 and criacao[0]["definicaoEtapa"]["chave"] != criacao[1]["definicaoEtapa"]["chave"]
    por_dep = {tuple(d["id"] for d in c["definicaoEtapa"]["departamentos"]): c for c in criacao}
    assert {i["demandaId"] for i in por_dep[(design.id,)]["itens"]} == {d1.id, d3.id}
    assert {i["demandaId"] for i in por_dep[(social.id,)]["itens"]} == {d2.id}
    assert por_dep[(design.id,)]["metricas"]["wip"] == 2 and por_dep[(social.id,)]["metricas"]["wip"] == 1


def test_mesmo_nome_e_departamentos_com_caixa_e_espacos_diferentes_e_uma_definicao_so(client_admin, db_session, empresa) -> None:
    dep = _departamento(db_session, empresa)
    aberta(db_session, empresa, etapa="Criação", deps=[dep])
    aberta(db_session, empresa, etapa="  criação ", deps=[dep])
    [definicao] = fluxo(client_admin).json()["definicoes"]
    assert definicao["metricas"]["wip"] == 2


def test_tipo_diferente_e_definicao_diferente(client_admin, db_session, empresa) -> None:
    aberta(db_session, empresa, etapa="Revisão", tipo="execucao")
    aberta(db_session, empresa, etapa="Revisão", tipo="aprovacao")
    assert len(fluxo(client_admin).json()["definicoes"]) == 2


def test_chave_e_a_mesma_de_gargalos_e_tem_o_formato_estavel(client_admin, db_session, empresa) -> None:
    dep_a, dep_b = _departamento(db_session, empresa), _departamento(db_session, empresa)
    aberta(db_session, empresa, etapa="Criação", deps=[dep_b, dep_a], tipo="execucao")  # ordem de gravação dos departamentos não importa
    [definicao] = fluxo(client_admin).json()["definicoes"]
    esperado = sha("criação", "execucao", [dep_a.id, dep_b.id])
    assert definicao["definicaoEtapa"]["chave"] == esperado  # formato fixo: nome normalizado + tipo + ids ordenados
    [da_fila] = _get(client_admin, "gargalos").json()["fila"]
    assert da_fila["definicaoEtapa"]["chave"] == esperado  # GARGALOS_KEYS_REGRESSION: Gargalos segue produzindo a mesma chave
    assert definicao["definicaoEtapa"] == da_fila["definicaoEtapa"]  # nome, tipo e departamentos idênticos


# ── paridade com Gargalos (oráculo independente) ─────────────────────────────────────────────────────────────────


def test_metricas_e_totais_batem_com_gargalos_no_cenario_de_fila(client_admin, db_session, empresa) -> None:
    _cenario_fila(db_session, empresa)  # devolução, planejada truncada pela medição, workflow concluído, sem workflow, rascunho fora
    gargalos = _get(client_admin, "gargalos").json()
    corpo = fluxo(client_admin).json()
    fila = {f["definicaoEtapa"]["chave"]: f for f in gargalos["fila"]}
    etapas = {e["definicaoEtapa"]["chave"]: e for e in gargalos["etapas"]}
    assert {d["definicaoEtapa"]["chave"] for d in corpo["definicoes"]} == set(fila) | set(etapas)
    for definicao in corpo["definicoes"]:
        chave, m = definicao["definicaoEtapa"]["chave"], definicao["metricas"]
        if chave in fila:
            f = fila[chave]
            assert (m["wip"], m["planejadas"], m["emExecucao"], m["pausadas"], m["bloqueadas"], m["aguardandoCliente"]) == (f["wip"], f["planejadas"], f["emExecucao"], f["pausadas"], f["bloqueadas"], f["aguardandoCliente"])
            assert m["maisAntigaSegundos"] == f["maisAntigaSegundos"] and m["maisAntigaTruncadaPelaMedicao"] == f["maisAntigaTruncadaPelaMedicao"]
            assert definicao["itensTotal"] == f["wip"]
        else:
            assert m["wip"] == 0 and definicao["itens"] == []
        if chave in etapas:
            assert m["tempoExecucaoMedioSegundos"] == etapas[chave]["tempoExecucaoMedioSegundos"] and m["nExecucao"] == etapas[chave]["nExecucao"]
    assert corpo["atual"] == gargalos["atual"] and corpo["semEtapa"] == gargalos["filaSemEtapa"]
    assert corpo["medicaoDesde"] == gargalos["medicaoDesde"] and corpo["coberturaParcial"] == gargalos["coberturaParcial"]
    assert corpo["periodo"]["inicio"] == gargalos["periodo"]["inicio"] and corpo["periodo"]["fim"] == gargalos["periodo"]["fim"]


def test_metricas_batem_com_gargalos_em_volume(client_admin, db_session, empresa, outra_empresa) -> None:
    _popular_volume(db_session, empresa, demandas=80, semente=11)
    _popular_volume(db_session, outra_empresa, demandas=30, semente=5)
    gargalos = _get(client_admin, "gargalos", limite=200).json()
    corpo = fluxo(client_admin, limiteDefinicoes=200).json()
    etapas = {e["definicaoEtapa"]["chave"]: e for e in gargalos["etapas"]}
    achadas = {d["definicaoEtapa"]["chave"]: d for d in corpo["definicoes"]}
    assert set(etapas) <= set(achadas)
    for chave, e in etapas.items():
        assert achadas[chave]["metricas"]["tempoExecucaoMedioSegundos"] == e["tempoExecucaoMedioSegundos"], chave
        assert achadas[chave]["metricas"]["nExecucao"] == e["nExecucao"], chave
    assert corpo["atual"] == gargalos["atual"] and corpo["semEtapa"] == gargalos["filaSemEtapa"]


def test_filtro_de_departamento_aplica_a_metricas_itens_e_totais_como_em_gargalos(client_admin, db_session, empresa) -> None:
    design, social = _departamento(db_session, empresa), _departamento(db_session, empresa)
    aberta(db_session, empresa, etapa="Criação", deps=[design])
    aberta(db_session, empresa, etapa="Criação", deps=[design], status="pausada")
    aberta(db_session, empresa, etapa="Redação", deps=[social])
    aberta(db_session, empresa, etapa="Sem depto")
    corpo = fluxo(client_admin, departamentoId=design.id).json()
    gargalos = _get(client_admin, "gargalos", departamentoId=design.id).json()
    [definicao] = corpo["definicoes"]
    assert definicao["definicaoEtapa"]["nome"] == "Criação" and definicao["itensTotal"] == definicao["metricas"]["wip"] == 2
    assert corpo["atual"] == gargalos["atual"] and corpo["atual"]["wip"] == 2  # o total do cabeçalho também é filtrado — nunca global sobre cards filtrados
    assert corpo["filtros"] == {"departamentoId": design.id}
    assert fluxo(client_admin, departamentoId=str(uuid.uuid4())).json()["definicoes"] == []
    assert fluxo(client_admin, departamentoId="nao-e-uuid").status_code == 422


# ── sem amostra, sem WIP, sem etapa ──────────────────────────────────────────────────────────────────────────────


def test_sem_amostra_e_nulo_nunca_zero(client_admin, db_session, empresa) -> None:
    aberta(db_session, empresa, status="planejada", etapa="Briefing")  # só planejada: nenhum tempo em execução medido
    [definicao] = fluxo(client_admin).json()["definicoes"]
    assert definicao["metricas"]["tempoExecucaoMedioSegundos"] is None and definicao["metricas"]["nExecucao"] == 0 and definicao["metricas"]["wip"] == 1


def test_media_em_execucao_com_amostra(client_admin, db_session, empresa) -> None:
    aberta(db_session, empresa, status="em_execucao", etapa="Arte", inicio=AGORA - timedelta(hours=2))  # aberto: conta até agora
    d = _demanda(db_session, empresa, status="em_execucao")
    e = _etapa(db_session, d, 1, "Arte")
    _intervalo(db_session, d, "em_execucao", AGORA - timedelta(hours=6), AGORA - timedelta(hours=2), etapa=e)  # 4 h
    _intervalo(db_session, d, "em_execucao", AGORA - timedelta(hours=2), etapa=e)  # + 2 h aberto → 6 h numa ocorrência
    [definicao] = fluxo(client_admin).json()["definicoes"]
    # ocorrências: A = 2 h, B = 6 h → média operacional 4 h; nExecucao = 2 (média por ocorrência, não por pessoa)
    assert definicao["metricas"]["nExecucao"] == 2 and definicao["metricas"]["tempoExecucaoMedioSegundos"] == 4 * 3600


def test_definicao_so_com_historico_aparece_com_wip_zero(client_admin, db_session, empresa) -> None:
    d = _demanda(db_session, empresa, status="concluida")
    e = _etapa(db_session, d, 1, "Finalização", concluida=True)
    _intervalo(db_session, d, "em_execucao", AGORA - timedelta(days=3), AGORA - timedelta(days=3) + timedelta(hours=3), etapa=e)
    [definicao] = fluxo(client_admin).json()["definicoes"]
    assert definicao["metricas"]["wip"] == 0 and definicao["itens"] == [] and definicao["itensTotal"] == 0 and definicao["truncado"] is False
    assert definicao["metricas"]["tempoExecucaoMedioSegundos"] == 3 * 3600 and definicao["metricas"]["maisAntigaSegundos"] is None


def test_demandas_sem_etapa_atual_nao_somem_viram_contagem(client_admin, db_session, empresa) -> None:
    f6 = _demanda(db_session, empresa)  # workflow concluído, Demanda aberta (pendência conhecida)
    _etapa(db_session, f6, 1, "Única", concluida=True)
    _intervalo(db_session, f6, "em_execucao", AGORA - timedelta(hours=5))
    f7 = _demanda(db_session, empresa, status="pausada")  # nunca teve workflow
    _intervalo(db_session, f7, "pausada", AGORA - timedelta(hours=5))
    aberta(db_session, empresa, etapa="Criação")
    corpo = fluxo(client_admin).json()
    assert corpo["semEtapa"] == {"workflowConcluido": 1, "semWorkflow": 1}
    assert corpo["atual"]["wip"] == 3 and [d["metricas"]["wip"] for d in corpo["definicoes"]] == [1]  # não formam coluna, mas estão no total


def test_etapa_atual_e_a_do_intervalo_aberto_e_bate_com_o_agora(client_admin, db_session, empresa) -> None:
    d = _demanda(db_session, empresa, status="em_execucao")
    e1 = _etapa(db_session, d, 1, "Criação", concluida=True)
    e2 = _etapa(db_session, d, 2, "Revisão")
    _intervalo(db_session, d, "em_execucao", AGORA - timedelta(hours=9), AGORA - timedelta(hours=4), etapa=e1)
    _intervalo(db_session, d, "em_execucao", AGORA - timedelta(hours=4), etapa=e2)
    corpo = fluxo(client_admin).json()
    [definicao] = por_nome(corpo, "Revisão")
    assert definicao["itens"][0]["etapaAtual"]["id"] == e2.id
    assert por_nome(corpo, "Criação")[0]["metricas"]["wip"] == 0  # a etapa concluída só tem histórico; o item não está nela
    assert _get(client_admin, "agora").json()["emExecucao"][0]["etapaAtual"]["id"] == e2.id  # a mesma etapa atual que o Agora deriva do workflow


# ── cards ────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_campos_do_item_responsavel_cliente_projeto_e_nulos(client_admin, db_session, empresa) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=cliente.id)
    pessoa = _usuario(db_session, empresa)
    pessoa.nome = "Marina Souza"
    d, e = aberta(db_session, empresa, etapa="Arte", prazo=AGORA - timedelta(hours=1), cliente_id=cliente.id, projeto_id=projeto.id)
    _resp_etapa(db_session, e, pessoa)
    sem, _ = aberta(db_session, empresa, etapa="Arte", status="pausada")  # sem cliente, projeto nem responsável
    corpo = fluxo(client_admin).json()
    [definicao] = corpo["definicoes"]
    itens = {i["demandaId"]: i for i in definicao["itens"]}
    com = itens[d.id]
    assert com["cliente"] == {"id": cliente.id, "nome": cliente.nome} and com["projeto"]["id"] == projeto.id
    assert com["responsaveis"] == [{"usuarioId": pessoa.id, "nome": "Marina Souza"}] and com["atrasada"] is True and com["idadeEstadoSegundos"] == 2 * 3600
    assert com["identificador"] and com["codigoReferencia"] and com["titulo"] and com["numeroOperacional"] and com["etapaAtual"]["nome"] == "Arte"
    vazio = itens[sem.id]
    assert vazio["cliente"] is None and vazio["projeto"] is None and vazio["responsaveis"] == [] and vazio["atrasada"] is False
    for proibido in ("sessao", "horastrabalhadas", "produtividade", "ranking", "salario", "valor", "financeiro", "token"):
        assert not [c for c in _chaves(corpo) if proibido in c.lower()], proibido


def test_ordem_dos_cards_atrasadas_primeiro_depois_a_mais_antiga_no_estado(client_admin, db_session, empresa) -> None:
    nova, _ = aberta(db_session, empresa, etapa="Arte", inicio=AGORA - timedelta(hours=1))
    antiga, _ = aberta(db_session, empresa, etapa="Arte", inicio=AGORA - timedelta(hours=30))
    atrasada, _ = aberta(db_session, empresa, etapa="Arte", inicio=AGORA - timedelta(hours=5), prazo=AGORA - timedelta(minutes=1))
    [definicao] = fluxo(client_admin).json()["definicoes"]
    assert [i["demandaId"] for i in definicao["itens"]] == [atrasada.id, antiga.id, nova.id]


# ── limites e truncamento ────────────────────────────────────────────────────────────────────────────────────────


def test_itens_truncados_nunca_alteram_o_wip(client_admin, db_session, empresa) -> None:
    for i in range(27):
        aberta(db_session, empresa, etapa="Arte", status=["em_execucao", "pausada", "bloqueada"][i % 3], inicio=AGORA - timedelta(minutes=10 + i))
    [definicao] = fluxo(client_admin).json()["definicoes"]  # limite padrão 20
    assert definicao["metricas"]["wip"] == 27 and definicao["itensTotal"] == 27 and definicao["itensRetornados"] == 20 and definicao["truncado"] is True and len(definicao["itens"]) == 20
    assert definicao["metricas"]["emExecucao"] + definicao["metricas"]["pausadas"] + definicao["metricas"]["bloqueadas"] == 27  # contagens por status são do total, não dos 20
    pequeno = fluxo(client_admin, limiteItensPorDefinicao=5).json()
    assert pequeno["definicoes"][0]["itensRetornados"] == 5 and pequeno["definicoes"][0]["itensTotal"] == 27 and pequeno["limiteItensPorDefinicao"] == 5
    inteiro = fluxo(client_admin, limiteItensPorDefinicao=100).json()["definicoes"][0]
    assert inteiro["itensRetornados"] == 27 and inteiro["truncado"] is False


def test_definicoes_truncadas_mantem_os_totais_globais(client_admin, db_session, empresa) -> None:
    for i in range(60):
        aberta(db_session, empresa, etapa=f"Etapa {i:02d}")
    corpo = fluxo(client_admin, limiteDefinicoes=50).json()
    assert corpo["definicoesTotal"] == 60 and corpo["definicoesRetornadas"] == 50 and len(corpo["definicoes"]) == 50 and corpo["truncado"] is True
    assert corpo["atual"]["wip"] == 60  # o total NÃO é calculado só sobre as 50 devolvidas
    assert fluxo(client_admin).json()["truncado"] is False  # limite padrão 100


def test_limites_invalidos_sao_recusados(client_admin) -> None:
    for params in ({"limiteDefinicoes": 0}, {"limiteDefinicoes": 201}, {"limiteItensPorDefinicao": 0}, {"limiteItensPorDefinicao": 101}, {"periodoDias": 0}, {"periodoDias": 91}):
        assert fluxo(client_admin, **params).status_code == 422, params


def test_ordem_das_colunas_e_neutra_e_deterministica(client_admin, db_session, empresa) -> None:
    dep_b, dep_a = _departamento(db_session, empresa), _departamento(db_session, empresa)
    dep_a.nome, dep_b.nome = "Atendimento", "Mídia"
    db_session.flush()
    aberta(db_session, empresa, etapa="Zeta", deps=[dep_a])
    aberta(db_session, empresa, etapa="Alfa", deps=[dep_b])
    aberta(db_session, empresa, etapa="Beta", deps=[dep_a])
    aberta(db_session, empresa, etapa="Gama")  # sem departamento: por último
    ordem = [d["definicaoEtapa"]["nome"] for d in fluxo(client_admin).json()["definicoes"]]
    assert ordem == ["Beta", "Zeta", "Alfa", "Gama"]  # departamento(s) → nome; sem departamento por último
    assert ordem == [d["definicaoEtapa"]["nome"] for d in fluxo(client_admin).json()["definicoes"]]


# ── RBAC, tenant, somente leitura, sem tempo pessoal ─────────────────────────────────────────────────────────────


def test_rbac(client_admin, client_gestor, client_operador, client_sem_token, db_session, empresa) -> None:
    aberta(db_session, empresa)
    assert fluxo(client_admin).status_code == 200 and fluxo(client_gestor).status_code == 200
    assert fluxo(client_operador).status_code == 403
    assert fluxo(client_sem_token).status_code in (401, 403)


def test_tenant_nunca_vaza_e_empresa_nao_e_parametro(client_admin, db_session, empresa, outra_empresa) -> None:
    alheia, _ = aberta(db_session, outra_empresa, etapa="Segredo")
    minha, _ = aberta(db_session, empresa, etapa="Minha")
    corpo = fluxo(client_admin, empresaId=outra_empresa.id).json()
    assert [d["definicaoEtapa"]["nome"] for d in corpo["definicoes"]] == ["Minha"] and corpo["atual"]["wip"] == 1
    assert alheia.id not in str(corpo) and minha.id in str(corpo)
    dep_alheio = _departamento(db_session, outra_empresa)
    assert fluxo(client_admin, departamentoId=dep_alheio.id).json()["definicoes"] == []  # departamento de outra empresa: nada (mesmo comportamento de Gargalos)


def _snapshot(db: Session) -> tuple:
    return tuple(
        db.scalar(select(func.count()).select_from(modelo)) for modelo in (Demanda, DemandaWorkflowEtapa, DemandaStatusIntervalo, Evento, SessaoTrabalho)
    )


def test_somente_leitura_e_sem_tempo_pessoal(client_admin, db_session, empresa) -> None:
    d, e = aberta(db_session, empresa, etapa="Arte")
    agora_db = datetime.now(timezone.utc)
    db_session.add(SessaoTrabalho(id=str(uuid.uuid4()), empresa_id=empresa.id, demanda_id=d.id, workflow_etapa_id=e.id, usuario_id=_usuario(db_session, empresa).id, evento_inicio_id=str(uuid.uuid4()), evento_fim_id=str(uuid.uuid4()), status="encerrada", inicio_em=agora_db - timedelta(hours=9), fim_em=agora_db, duracao_segundos=9 * 3600, motivo_encerramento="pausa", created_at=agora_db, updated_at=agora_db))
    db_session.flush()
    sem_sessao = fluxo(client_admin).json()
    antes = _snapshot(db_session)
    declaracoes: list[str] = []

    def captura(conn, cursor, statement, parameters, context, executemany):
        declaracoes.append(statement)

    motor = db_session.get_bind()
    event.listen(motor, "before_cursor_execute", captura)
    try:
        com_sessao = fluxo(client_admin).json()
    finally:
        event.remove(motor, "before_cursor_execute", captura)
    assert declaracoes and not [s for s in declaracoes if "sessoes_trabalho" in s]  # PERSONAL_SESSIONS_READ=NÃO
    assert [s for s in declaracoes if "demanda_status_intervalos" in s]  # OPERATIONAL_INTERVALS_USED=SIM (a fonte das métricas)
    assert not [s for s in declaracoes if s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]
    assert _snapshot(db_session) == antes  # nenhuma Demanda, etapa, intervalo, evento ou sessão criado/alterado
    assert {k: v for k, v in com_sessao.items() if k != "agoraServidor"} == {k: v for k, v in sem_sessao.items() if k != "agoraServidor"}


def test_gargalos_e_agora_nao_mudaram(client_admin, db_session, empresa) -> None:
    _cenario_fila(db_session, empresa)
    gargalos = _get(client_admin, "gargalos").json()
    assert set(gargalos) == {"agoraServidor", "periodo", "filtros", "medicaoDesde", "coberturaParcial", "etapas", "etapasTotal", "semEtapa", "atual", "fila", "filaTotal", "filaSemEtapa", "limite"}
    assert set(gargalos["fila"][0]) == {"definicaoEtapa", "wip", "planejadas", "emExecucao", "pausadas", "bloqueadas", "aguardandoCliente", "maisAntigaDesde", "maisAntigaSegundos", "maisAntigaTruncadaPelaMedicao", "idadeEstadoMaisAntigoSegundos"}
    assert set(gargalos["fila"][0]["definicaoEtapa"]) == {"chave", "nome", "tipo", "departamentos"}  # sem definicaoChave/itens: contrato intacto
    agora = _get(client_admin, "agora").json()
    assert "definicaoChave" not in str(agora) and set(agora["emExecucao"][0]["etapaAtual"]) == {"id", "nome", "tipo", "departamentos"}


# ── consultas e volume ───────────────────────────────────────────────────────────────────────────────────────────


def _volume(db: Session, empresa, *, definicoes: int, demandas: int) -> None:
    deps = [_departamento(db, empresa) for _ in range(4)]
    for i in range(demandas):
        aberta(db, empresa, status=["em_execucao", "pausada", "bloqueada", "aguardando_cliente", "planejada"][i % 5], etapa=f"Etapa {i % definicoes:03d}", deps=[deps[i % 4]], inicio=AGORA - timedelta(minutes=i + 1))


def test_numero_de_queries_nao_cresce_com_o_volume(client_admin, db_session, empresa) -> None:
    _volume(db_session, empresa, definicoes=3, demandas=9)
    fluxo(client_admin)  # aquecimento (autenticação/permissões/regra)
    pequeno = _contar_queries(db_session, lambda: fluxo(client_admin))
    _volume(db_session, empresa, definicoes=120, demandas=520)
    fluxo(client_admin)
    grande = _contar_queries(db_session, lambda: fluxo(client_admin, limiteDefinicoes=200))
    assert pequeno == grande, (pequeno, grande)  # sem N+1: nenhuma consulta cresce por card, definição ou departamento
    print(f"FLOW_QUERY_COUNT_SMALL={pequeno} FLOW_QUERY_COUNT_LARGE={grande}")


def test_diagnostico_de_desempenho_com_100_definicoes_e_500_demandas(client_admin, db_session, empresa) -> None:
    _volume(db_session, empresa, definicoes=100, demandas=620)  # 100 etapas × 4 departamentos ciclando juntos = 100 definições
    fluxo(client_admin)
    inicio = time.perf_counter()
    corpo = fluxo(client_admin, limiteDefinicoes=200).json()
    decorrido = (time.perf_counter() - inicio) * 1000
    assert corpo["atual"]["wip"] == 620 and sum(d["metricas"]["wip"] for d in corpo["definicoes"]) == 620 and corpo["definicoesTotal"] >= 100
    assert all(d["itensTotal"] == d["metricas"]["wip"] for d in corpo["definicoes"])
    print(f"FLOW_LARGE_DATASET_MS={decorrido:.0f} definicoes={corpo['definicoesTotal']} demandas=620 (diagnóstico; sem cache e sem índice novo)")


# ── OpenAPI ──────────────────────────────────────────────────────────────────────────────────────────────────────


def test_openapi_tipado_com_parametros_documentados(app) -> None:
    esquema = app.openapi()
    operacao = esquema["paths"]["/trafego/operacional/fluxo"]["get"]
    parametros = {p["name"]: p for p in operacao["parameters"]}
    assert set(parametros) == {"periodoDias", "departamentoId", "limiteDefinicoes", "limiteItensPorDefinicao"}
    assert parametros["limiteItensPorDefinicao"]["schema"]["maximum"] == 100 and parametros["limiteDefinicoes"]["schema"]["maximum"] == 200 and parametros["periodoDias"]["schema"]["maximum"] == 90
    assert all(p.get("description") for n, p in parametros.items() if n != "limiteDefinicoes" and n != "limiteItensPorDefinicao")
    resposta = operacao["responses"]["200"]["content"]["application/json"]["schema"]
    assert resposta["$ref"].endswith("/TrafegoOperacionalFluxoRead")  # schema Pydantic, nunca dicionário solto
    componentes = esquema["components"]["schemas"]
    assert {"FluxoDefinicaoRead", "FluxoItemRead", "FluxoMetricasRead"} <= set(componentes)
    assert "definicaoChave" in componentes["FluxoItemRead"]["properties"] and "itensTotal" in componentes["FluxoDefinicaoRead"]["properties"]
