"""P1_STAGE_ASSIGNEES (ajuste final) — a responsabilidade EFETIVA da etapa é uma regra única do DOMÍNIO (`app.core.executor_etapa`), consumida por Carga, iniciar trabalho,
autoridade de avançar (concluir/aprovar/rejeitar), Meu Dia, notificações da próxima etapa e encerramento de sessões.

Regra congelada: (A) etapa com ao menos 1 vínculo explícito (usuário OU departamento) usa SÓ os vínculos dela; (B) sem vínculo, herda DINAMICAMENTE os responsáveis gerais da Demanda
(nunca copiados); (C) senão ninguém. O fallback NÃO concede gestão: editar a Demanda, esforço, planejamento e troca de responsáveis seguem exigindo vínculo explícito/permissão.

As fixtures abaixo exercitam a MESMA situação por todos os consumidores ao mesmo tempo, para que nenhum deles volte a divergir.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.test_carga_semanal_api import AGORA as CARGA_AGORA, SEG, carga, por_id, regra, relogio  # noqa: F401  (fixtures `regra`, `relogio`)
from tests.test_d1_criacao_demandas import _client_para
from tests.test_demanda import _departamento, dentro_do_expediente  # noqa: F401  (fixture)
from tests.test_fase_8a_workflow_progressao import _demanda_com_workflow, _etapa, _por_ordem, _url
from tests.test_fase_8c_workflow_notificacoes import TIPO, _da_etapa
from tests.test_meu_dia_fila_pessoal import _fila
from tests.test_sessao_trabalho_integridade import _abrir_ok, _patch, _sessao, operadores  # noqa: F401  (fixture `operadores`)
from tests.test_stage_assignees import _efetiva, _etapa_de, _put, _vinculos_da_etapa


@pytest.fixture(autouse=True)
def _expediente_aberto(dentro_do_expediente) -> None:  # noqa: F811
    """Iniciar trabalho respeita o expediente — a janela é fixada para o teste."""


def _planejar(db: Session, etapa_id: str, *, minutos: int = 240) -> None:
    """Estimativa + janela de UM dia (a segunda do “agora” da Carga) na etapa — a Carga só conta o que tem esforço."""
    etapa = db.get(DemandaWorkflowEtapa, etapa_id)
    etapa.esforco_estimado_minutos = minutos
    etapa.planejado_inicio = etapa.planejado_fim = SEG
    db.execute(text("UPDATE demandas SET status='planejada' WHERE id=:d AND status='rascunho'"), {"d": etapa.demanda_id})  # a Carga só conta Demandas fora do rascunho
    db.flush()


def _pode_iniciar(app, usuario: Usuario, demanda_id: str) -> bool:
    resposta = _client_para(app, usuario).get(f"/demandas/{demanda_id}")
    return resposta.status_code == 200 and resposta.json()["podeIniciarTrabalho"]  # fora do escopo = não pode


def _sessoes_do(db: Session, demanda_id: str, usuario: Usuario) -> int:
    db.expire_all()
    return db.execute(text("SELECT count(*) FROM sessoes_trabalho WHERE demanda_id=:d AND usuario_id=:u"), {"d": demanda_id, "u": usuario.id}).scalar()


def _planejado(corpo: dict, usuario: Usuario) -> int:
    return por_id(corpo["pessoas"], "usuarioId", usuario.id)["planejadoMin"]


def _pessoas_com_carga(corpo: dict) -> set[str]:
    return {p["usuarioId"] for p in corpo["pessoas"] if p["planejadoMin"]}


# --------------------------------------------------------------------------------------
# Fixture A — etapa SEM vínculo explícito + responsável geral = Milenna: todos os consumidores herdam
# --------------------------------------------------------------------------------------


def test_etapa_vazia_com_responsavel_geral_e_a_mesma_resposta_em_todos_os_consumidores(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario], regra  # noqa: F811
) -> None:
    milenna, raquel = operadores[0], operadores[1]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte"), _etapa("Aprovação", "aprovacao")], usuarioResponsavelIds=[milenna.id])
    e1, e2 = _etapa_de(demanda, 1), _etapa_de(demanda, 2)
    _planejar(db_session, e1["id"])
    c_milenna, c_raquel = _client_para(app, milenna), _client_para(app, raquel)

    # leitura: origem = tarefa, e NENHUM vínculo explícito foi criado
    assert _efetiva(demanda, 1) == {"origem": "tarefa", "usuarioIds": [milenna.id], "departamentoIds": []}
    assert _vinculos_da_etapa(db_session, e1["id"]) == (0, 0)
    # iniciar trabalho
    assert _pode_iniciar(app, milenna, demanda["id"]) is True and _pode_iniciar(app, raquel, demanda["id"]) is False
    # Meu Dia
    assert demanda["id"] in [i["id"] for i in _fila(c_milenna)] and demanda["id"] not in [i["id"] for i in _fila(c_raquel)]
    # Carga: a tarefa dá a carga à Milenna (origem tarefa), não ao “pool sem departamento”
    corpo = carga(client_admin).json()
    assert _planejado(corpo, milenna) == 240 and corpo["poolSemDepartamento"]["etapasCount"] == 0
    detalhe = carga(client_admin, usuarioId=milenna.id, detalhe="usuario").json()["detalhe"]["etapas"]
    assert [i["origem"] for i in detalhe if i["etapaId"] == e1["id"]] == ["responsavel"]  # a etapa planejada vai para a Milenna (origem tarefa → responsável)
    # autoridade de avançar: a Milenna pode; quem não é responsável de nada, não
    assert c_raquel.post(_url(demanda["id"], e1["id"], "concluir")).status_code in (403, 404)  # fora do escopo
    assert c_milenna.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    # notificação da PRÓXIMA etapa (vazia, herda a Milenna) considera a responsável efetiva — e a leitura continua sem vínculo próprio
    eventos = db_session.execute(text("SELECT payload FROM eventos WHERE entidade_id=:d AND tipo=:t"), {"d": demanda["id"], "t": TIPO}).all()
    assert eventos and milenna.id in str(eventos[-1][0])
    assert _vinculos_da_etapa(db_session, e1["id"]) == (0, 0) and _vinculos_da_etapa(db_session, e2["id"]) == (0, 0)


def test_notificacao_da_proxima_etapa_chega_ao_responsavel_geral_herdado(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    milenna = operadores[0]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte")], usuarioResponsavelIds=[milenna.id])
    assert client_admin.post(_url(demanda["id"], _etapa_de(demanda, 1)["id"], "concluir")).status_code == 200
    assert len(_da_etapa(_client_para(app, milenna), demanda["id"])) == 1


def test_fallback_nao_concede_esforco_nem_planejamento_da_etapa(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    milenna = operadores[0]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte")], usuarioResponsavelIds=[milenna.id])
    e1 = _etapa_de(demanda, 1)
    c = _client_para(app, milenna)
    base = f"/demandas/{demanda['id']}/workflow/etapas/{e1['id']}"
    assert c.get(f"/demandas/{demanda['id']}").status_code == 200
    assert c.patch(f"{base}/esforco", json={"esforcoEstimadoMinutos": 60}).status_code == 403  # esforço/planejamento seguem exigindo vínculo explícito
    assert c.patch(f"{base}/planejamento", json={"planejadoInicio": str(SEG), "planejadoFim": str(SEG)}).status_code == 403
    etapa = next(e for e in _por_ordem(c.get(f"/demandas/{demanda['id']}").json()) if e["id"] == e1["id"])
    assert etapa["podeEditarEsforco"] is False and etapa["podeEditarPlanejamento"] is False and etapa["podeAvancar"] is True


def test_fallback_e_dinamico_para_carga_e_para_iniciar_trabalho(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario], regra) -> None:  # noqa: F811
    milenna, joao = operadores[0], operadores[1]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte")], usuarioResponsavelIds=[milenna.id])
    e1 = _etapa_de(demanda, 1)
    _planejar(db_session, e1["id"])
    assert _planejado(carga(client_admin).json(), milenna) == 240
    _patch(client_admin, demanda["id"], usuarioResponsavelIds=[joao.id])  # troca o geral SEM tocar na etapa
    corpo = carga(client_admin).json()
    assert _planejado(corpo, joao) == 240 and milenna.id not in _pessoas_com_carga(corpo)
    assert _pode_iniciar(app, joao, demanda["id"]) is True and _pode_iniciar(app, milenna, demanda["id"]) is False
    assert _vinculos_da_etapa(db_session, e1["id"]) == (0, 0)  # nada persistido


# --------------------------------------------------------------------------------------
# Fixture B — etapa EXPLÍCITA (Raquel) + geral = Milenna: o explícito bloqueia o fallback em TODOS os consumidores
# --------------------------------------------------------------------------------------


def test_etapa_explicita_bloqueia_o_fallback_em_todos_os_consumidores(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario], regra  # noqa: F811
) -> None:
    milenna, raquel = operadores[0], operadores[1]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação", usuarios=[raquel.id]), _etapa("Arte")], usuarioResponsavelIds=[milenna.id])
    e1 = _etapa_de(demanda, 1)
    _planejar(db_session, e1["id"])
    c_milenna, c_raquel = _client_para(app, milenna), _client_para(app, raquel)

    assert _efetiva(demanda, 1) == {"origem": "etapa", "usuarioIds": [raquel.id], "departamentoIds": []}
    corpo = carga(client_admin).json()
    assert _planejado(corpo, raquel) == 240 and milenna.id not in _pessoas_com_carga(corpo)
    assert _pode_iniciar(app, raquel, demanda["id"]) is True and _pode_iniciar(app, milenna, demanda["id"]) is False
    c_milenna.post(f"/demandas/{demanda['id']}/iniciar-trabalho")  # pode mover o status pelo RBAC, mas NÃO é executora: não ganha sessão pessoal
    assert _sessoes_do(db_session, demanda["id"], milenna) == 0
    assert c_milenna.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 403  # a etapa é da Raquel
    etapa_para_milenna = next(e for e in _por_ordem(c_milenna.get(f"/demandas/{demanda['id']}").json()) if e["id"] == e1["id"])
    assert etapa_para_milenna["podeAvancar"] is False
    assert c_raquel.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200


def test_etapa_so_com_departamento_nao_cai_no_fallback_da_tarefa(
    app, db_session: Session, empresa: Empresa, client_admin: TestClient, operadores: list[Usuario], regra  # noqa: F811
) -> None:
    milenna = operadores[0]
    criacao = _departamento(db_session, empresa, nome="Criação")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação", departamentos=[criacao.id]), _etapa("Arte")], usuarioResponsavelIds=[milenna.id])
    e1 = _etapa_de(demanda, 1)
    _planejar(db_session, e1["id"])
    c_milenna = _client_para(app, milenna)

    assert _efetiva(demanda, 1) == {"origem": "etapa", "usuarioIds": [], "departamentoIds": [criacao.id]}
    corpo = carga(client_admin).json()
    assert milenna.id not in _pessoas_com_carga(corpo)  # Carga: pool do departamento, nunca a Milenna
    assert por_id(corpo["departamentos"], "departamentoId", criacao.id)["planejadoPoolMin"] == 240
    assert _pode_iniciar(app, milenna, demanda["id"]) is False
    assert c_milenna.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 403


def test_sem_nenhuma_responsabilidade_a_carga_vai_ao_pool_e_so_gestao_avanca(
    app, db_session: Session, client_admin: TestClient, client_gestor: TestClient, operadores: list[Usuario], regra  # noqa: F811
) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte")])
    e1 = _etapa_de(demanda, 1)
    _planejar(db_session, e1["id"])
    assert _efetiva(demanda, 1)["origem"] == "nenhuma"
    corpo = carga(client_admin).json()
    assert corpo["poolSemDepartamento"]["etapasCount"] == 2 and not _pessoas_com_carga(corpo)  # as duas etapas abertas, sem ninguém
    assert _client_para(app, operadores[0]).post(_url(demanda["id"], e1["id"], "concluir")).status_code in (403, 404)
    assert client_gestor.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200


# --------------------------------------------------------------------------------------
# Iniciar trabalho
# --------------------------------------------------------------------------------------


def test_iniciar_trabalho_com_etapa_vazia_usa_o_responsavel_geral(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    milenna, joao = operadores[0], operadores[1]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte")], usuarioResponsavelIds=[milenna.id])
    assert _client_para(app, joao).post(f"/demandas/{demanda['id']}/iniciar-trabalho").status_code in (403, 404)
    resposta = _client_para(app, milenna).post(f"/demandas/{demanda['id']}/iniciar-trabalho")
    assert resposta.status_code == 200, resposta.text
    assert _sessoes_do(db_session, demanda["id"], milenna) == 1  # executora efetiva: ganha a sessão pessoal


# --------------------------------------------------------------------------------------
# Sessões de trabalho acompanham a responsabilidade EFETIVA FINAL
# --------------------------------------------------------------------------------------


def test_explicito_raquel_limpo_com_geral_milenna_encerra_a_sessao_da_raquel(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    milenna, raquel = operadores[0], operadores[1]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação", usuarios=[raquel.id]), _etapa("Arte")], usuarioResponsavelIds=[milenna.id])
    e1 = _etapa_de(demanda, 1)
    _patch(client_admin, demanda["id"], status="em_execucao")
    sessao_raquel = _abrir_ok(client_admin, demanda["id"], raquel.id)
    assert _put(client_admin, demanda["id"], e1["id"], [], []).status_code == 200  # herda: efetivo final = Milenna
    assert _sessao(db_session, sessao_raquel["id"]).status == "encerrada"
    assert _sessao(db_session, sessao_raquel["id"]).motivo_encerramento == "troca_responsavel"
    ativas = db_session.execute(text("SELECT count(*) FROM sessoes_trabalho WHERE demanda_id=:d AND status='ativa'"), {"d": demanda["id"]}).scalar()
    assert ativas == 0  # a Milenna NÃO ganhou sessão


def test_trocar_o_responsavel_geral_encerra_a_sessao_herdada_do_antigo(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    milenna, joao = operadores[0], operadores[1]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte")], usuarioResponsavelIds=[milenna.id])
    _patch(client_admin, demanda["id"], status="em_execucao")
    sessao = _abrir_ok(client_admin, demanda["id"], milenna.id)
    _patch(client_admin, demanda["id"], usuarioResponsavelIds=[joao.id])
    antiga = _sessao(db_session, sessao["id"])
    assert antiga.status == "encerrada" and antiga.motivo_encerramento == "troca_responsavel"


def test_trocar_o_geral_nao_encerra_a_sessao_de_quem_tem_a_etapa_explicita(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    raquel, joao = operadores[0], operadores[1]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação", usuarios=[raquel.id]), _etapa("Arte")], usuarioResponsavelIds=[raquel.id])
    _patch(client_admin, demanda["id"], status="em_execucao")
    sessao = _abrir_ok(client_admin, demanda["id"], raquel.id)
    _patch(client_admin, demanda["id"], usuarioResponsavelIds=[raquel.id, joao.id])
    assert _sessao(db_session, sessao["id"]).status == "ativa"  # explícito da etapa: o geral não interfere


# --------------------------------------------------------------------------------------
# Custo: o fallback não introduz consulta por Demanda/etapa
# --------------------------------------------------------------------------------------


def _contar_consultas(db: Session, chamada) -> int:
    comandos: list[str] = []

    def capturar(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement)

    engine = db.get_bind()
    chamada()  # aquece
    event.listen(engine, "before_cursor_execute", capturar)
    try:
        chamada()
    finally:
        event.remove(engine, "before_cursor_execute", capturar)
    return len(comandos)


def test_carga_lista_e_meu_dia_tem_custo_constante_com_mais_demandas(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario], regra  # noqa: F811
) -> None:
    milenna = operadores[0]
    c_milenna = _client_para(app, milenna)

    def nova() -> None:
        demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte")], usuarioResponsavelIds=[milenna.id])
        _planejar(db_session, _etapa_de(demanda, 1)["id"])

    nova()
    chamadas = {
        "carga": lambda: carga(client_admin),
        "lista": lambda: client_admin.get("/demandas", params={"limit": 200}),
        "meu_dia": lambda: _fila(c_milenna),
    }
    antes = {nome: _contar_consultas(db_session, chamada) for nome, chamada in chamadas.items()}
    for _ in range(5):
        nova()
    depois = {nome: _contar_consultas(db_session, chamada) for nome, chamada in chamadas.items()}
    assert depois == antes, (antes, depois)


# --------------------------------------------------------------------------------------
# Meu Dia / Meu Departamento — escopo de DEMANDA (DemandaResponsavel / DemandaDepartamento): o fallback já está dentro dele
# --------------------------------------------------------------------------------------


def test_meu_departamento_enxerga_a_demanda_do_departamento_geral_com_etapa_vazia_ou_explicita(
    app, db_session: Session, empresa: Empresa, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    from tests.test_fase_7c_visoes_lideranca import _ids, _lista

    maria = operadores[0]
    criacao = _departamento(db_session, empresa, nome="Criação")
    digital = _departamento(db_session, empresa, nome="Digital")
    criacao.responsavel_usuario_id = maria.id  # Head formal de Criação
    db_session.commit()
    vazia = _demanda_com_workflow(client_admin, [_etapa("Redação")], departamentoResponsavelIds=[criacao.id])
    explicita_outro = _demanda_com_workflow(client_admin, [_etapa("Arte", departamentos=[digital.id])], departamentoResponsavelIds=[criacao.id])
    assert _efetiva(vazia, 1) == {"origem": "tarefa", "usuarioIds": [], "departamentoIds": [criacao.id]}
    assert _efetiva(explicita_outro, 1)["origem"] == "etapa"
    ids = _ids(_lista(_client_para(app, maria), "meu-departamento"))
    assert vazia["id"] in ids  # a etapa vazia herda o departamento geral: segue na visão do Head
    assert explicita_outro["id"] in ids  # o escopo é o da DEMANDA (departamento geral); a etapa explícita de outro setor não o esconde
    assert _vinculos_da_etapa(db_session, _etapa_de(vazia, 1)["id"]) == (0, 0)

