"""Responsáveis EXPLÍCITOS por etapa da Demanda (usuários e departamentos) + responsabilidade EFETIVA (etapa → tarefa → ninguém).

`PUT /demandas/{id}/workflow/etapas/{etapaId}/responsaveis` substitui os vínculos explícitos da etapa (atual ou futura; concluída é somente leitura). `[]`+`[]` volta a herdar a tarefa.
O fallback é DINÂMICO (nunca copiado para a etapa). Na criação, `workflowEtapasResponsaveis` (por `modeloEtapaId`) é opcional e atômico.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.services.demanda_service import DemandaService
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _client_para, _head_por_responsavel
from tests.test_demanda import _departamento, dentro_do_expediente  # noqa: F401  (fixture)
from tests.test_fase_8a_workflow_progressao import _demanda_com_workflow, _etapa, _por_ordem, _url
from tests.test_sessao_trabalho_integridade import _abrir_ok, _patch, _sessao, operadores  # noqa: F401  (fixture `operadores`)


@pytest.fixture(autouse=True)
def _expediente_aberto(dentro_do_expediente) -> None:  # noqa: F811
    """Iniciar trabalho / entrar em execução respeita o expediente — a janela é fixada para o teste."""


def _put(client: TestClient, demanda_id: str, etapa_id: str, usuarios: list[str] | None = None, departamentos: list[str] | None = None):
    return client.put(
        f"/demandas/{demanda_id}/workflow/etapas/{etapa_id}/responsaveis",
        json={"usuarioResponsavelIds": usuarios or [], "departamentoResponsavelIds": departamentos or []},
    )


def _tres_etapas(client: TestClient, **extra) -> dict:
    return _demanda_com_workflow(client, [_etapa("Redação"), _etapa("Direção de Arte"), _etapa("Aprovação interna", "aprovacao")], **extra)


def _etapa_de(corpo: dict, ordem: int) -> dict:
    return _por_ordem(corpo)[ordem - 1]


def _eventos(db: Session, demanda_id: str) -> list[Evento]:
    db.expire_all()
    return list(db.scalars(select(Evento).where(Evento.entidade_id == demanda_id, Evento.tipo == "demanda.workflow_responsaveis_alterados")).all())


def _vinculos_da_etapa(db: Session, etapa_id: str) -> tuple[int, int]:
    db.expire_all()
    u = db.scalar(text("SELECT count(*) FROM demanda_workflow_etapa_responsaveis WHERE demanda_workflow_etapa_id=:e"), {"e": etapa_id})
    d = db.scalar(text("SELECT count(*) FROM demanda_workflow_etapa_departamentos_responsaveis WHERE demanda_workflow_etapa_id=:e"), {"e": etapa_id})
    return u, d


def _efetiva(corpo: dict, ordem: int) -> dict:
    return _etapa_de(corpo, ordem)["responsabilidadeEfetiva"]


# --------------------------------------------------------------------------------------
# Edição e leitura
# --------------------------------------------------------------------------------------


def test_etapa_com_responsavel_explicito_troca_soma_e_vira_origem_etapa(client_admin: TestClient, operadores: list[Usuario]) -> None:
    raquel, joao = operadores[0], operadores[1]
    demanda = _tres_etapas(client_admin)
    da = _etapa_de(demanda, 2)

    r = _put(client_admin, demanda["id"], da["id"], [raquel.id])
    assert r.status_code == 200, r.text
    etapa = _etapa_de(r.json(), 2)
    assert etapa["usuarioResponsavelIds"] == [raquel.id] and _efetiva(r.json(), 2) == {"origem": "etapa", "usuarioIds": [raquel.id], "departamentoIds": []}

    r = _put(client_admin, demanda["id"], da["id"], [joao.id])  # troca
    assert _etapa_de(r.json(), 2)["usuarioResponsavelIds"] == [joao.id]
    r = _put(client_admin, demanda["id"], da["id"], [raquel.id, joao.id])  # multi-responsável preservado
    assert sorted(_etapa_de(r.json(), 2)["usuarioResponsavelIds"]) == sorted([raquel.id, joao.id])
    assert sorted(_efetiva(r.json(), 2)["usuarioIds"]) == sorted([raquel.id, joao.id])
    # as outras etapas e o status/ordem/planejamento não mudam
    assert _etapa_de(r.json(), 1)["usuarioResponsavelIds"] == [] and _etapa_de(r.json(), 3)["usuarioResponsavelIds"] == []
    assert [e["status"] for e in _por_ordem(r.json())] == ["pendente"] * 3


def test_departamento_explicito_e_usuario_mais_departamento(db_session: Session, empresa: Empresa, client_admin: TestClient, operadores: list[Usuario]) -> None:
    criacao = _departamento(db_session, empresa, nome="Criação")
    demanda = _tres_etapas(client_admin)
    etapa = _etapa_de(demanda, 2)
    r = _put(client_admin, demanda["id"], etapa["id"], [], [criacao.id])
    assert _efetiva(r.json(), 2) == {"origem": "etapa", "usuarioIds": [], "departamentoIds": [criacao.id]}
    r = _put(client_admin, demanda["id"], etapa["id"], [operadores[0].id], [criacao.id])
    efetiva = _efetiva(r.json(), 2)
    assert efetiva["origem"] == "etapa" and efetiva["usuarioIds"] == [operadores[0].id] and efetiva["departamentoIds"] == [criacao.id]


def test_limpar_volta_a_herdar_a_tarefa_ou_ninguem(client_admin: TestClient, operadores: list[Usuario]) -> None:
    milenna, raquel = operadores[0], operadores[1]
    com_tarefa = _tres_etapas(client_admin, usuarioResponsavelIds=[milenna.id])
    etapa = _etapa_de(com_tarefa, 1)
    _put(client_admin, com_tarefa["id"], etapa["id"], [raquel.id])
    r = _put(client_admin, com_tarefa["id"], etapa["id"], [], [])
    assert _efetiva(r.json(), 1) == {"origem": "tarefa", "usuarioIds": [milenna.id], "departamentoIds": []}  # herdado, nunca "sem responsável forçado"

    sem_tarefa = _tres_etapas(client_admin)
    assert _efetiva(sem_tarefa, 1) == {"origem": "nenhuma", "usuarioIds": [], "departamentoIds": []}


def test_fallback_e_dinamico_e_nunca_copiado_para_a_etapa(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    milenna, joao = operadores[0], operadores[1]
    demanda = _tres_etapas(client_admin, usuarioResponsavelIds=[milenna.id])
    etapa = _etapa_de(demanda, 2)
    assert _efetiva(demanda, 2)["usuarioIds"] == [milenna.id]

    r = _patch(client_admin, demanda["id"], usuarioResponsavelIds=[joao.id])  # troca o geral SEM tocar na etapa
    assert _efetiva(r, 2) == {"origem": "tarefa", "usuarioIds": [joao.id], "departamentoIds": []}
    assert _vinculos_da_etapa(db_session, etapa["id"]) == (0, 0)  # nada persistido na etapa


def test_explicito_nao_muda_quando_a_tarefa_troca_e_departamento_explicito_nao_cai_no_fallback(
    db_session: Session, empresa: Empresa, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    milenna, raquel, joao = operadores[0], operadores[1], operadores[2]
    criacao = _departamento(db_session, empresa, nome="Criação")
    demanda = _tres_etapas(client_admin, usuarioResponsavelIds=[milenna.id])
    e1, e2 = _etapa_de(demanda, 1), _etapa_de(demanda, 2)
    _put(client_admin, demanda["id"], e1["id"], [raquel.id])
    _put(client_admin, demanda["id"], e2["id"], [], [criacao.id])
    r = _patch(client_admin, demanda["id"], usuarioResponsavelIds=[joao.id])
    assert _efetiva(r, 1) == {"origem": "etapa", "usuarioIds": [raquel.id], "departamentoIds": []}
    efetiva = _efetiva(r, 2)
    assert efetiva["origem"] == "etapa" and efetiva["usuarioIds"] == [] and efetiva["departamentoIds"] == [criacao.id]  # só departamento = responsabilidade explícita
    assert milenna.id not in efetiva["usuarioIds"] and joao.id not in efetiva["usuarioIds"]


def test_no_op_nao_gera_evento_e_mudanca_gera_um_com_antes_e_depois(db_session: Session, client_admin: TestClient, usuario_admin: Usuario, operadores: list[Usuario]) -> None:
    demanda = _tres_etapas(client_admin)
    etapa = _etapa_de(demanda, 2)
    assert _put(client_admin, demanda["id"], etapa["id"], [], []).status_code == 200
    assert _eventos(db_session, demanda["id"]) == []  # no-op
    _put(client_admin, demanda["id"], etapa["id"], [operadores[0].id])
    _put(client_admin, demanda["id"], etapa["id"], [operadores[0].id])  # repetido: no-op
    (evento,) = _eventos(db_session, demanda["id"])
    assert evento.payload["etapaId"] == etapa["id"] and evento.payload["atorUsuarioId"] == usuario_admin.id
    assert evento.payload["usuariosAntes"] == [] and evento.payload["usuariosDepois"] == [operadores[0].id]


def test_etapa_concluida_e_somente_leitura_e_etapa_futura_pode_ser_editada(client_admin: TestClient, operadores: list[Usuario]) -> None:
    demanda = _tres_etapas(client_admin)
    e1, e3 = _etapa_de(demanda, 1), _etapa_de(demanda, 3)
    assert _put(client_admin, demanda["id"], e3["id"], [operadores[0].id]).status_code == 200  # futura
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    r = _put(client_admin, demanda["id"], e1["id"], [operadores[1].id])
    assert r.status_code == 409 and "somente para consulta" in r.json()["detail"]
    assert client_admin.get(f"/demandas/{demanda['id']}").json()["workflowEtapas"][0]["usuarioResponsavelIds"] == []


def test_validacao_cross_tenant_arquivada_e_etapa_de_outra_demanda(
    app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    estranho = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="estranho")
    dep_estranho = _departamento(db_session, outra_empresa, nome="Outro tenant")
    demanda = _tres_etapas(client_admin)
    etapa = _etapa_de(demanda, 2)
    assert _put(client_admin, demanda["id"], etapa["id"], [estranho.id]).status_code == 422
    assert _put(client_admin, demanda["id"], etapa["id"], [], [dep_estranho.id]).status_code == 422
    outra = _tres_etapas(client_admin)
    assert _put(client_admin, demanda["id"], _etapa_de(outra, 1)["id"], [operadores[0].id]).status_code == 404  # etapa de outra demanda
    cliente_de_fora = _client_para(app, estranho)
    assert _put(cliente_de_fora, demanda["id"], etapa["id"], [estranho.id]).status_code == 404  # outra empresa não enxerga a demanda
    assert client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code == 200
    assert _put(client_admin, demanda["id"], etapa["id"], [operadores[0].id]).status_code == 409


# --------------------------------------------------------------------------------------
# Autoridade (a mesma de alterar os responsáveis da Demanda)
# --------------------------------------------------------------------------------------


def test_head_so_atribui_departamento_que_lidera_e_operador_comum_so_o_proprio_contexto(
    app, db_session: Session, empresa: Empresa, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    head = operadores[0]
    dep_head = _head_por_responsavel(db_session, empresa, head)
    outro_dep = _departamento(db_session, empresa, nome="De outro Head")
    demanda = _tres_etapas(client_admin, usuarioResponsavelIds=[head.id])
    etapa = _etapa_de(demanda, 2)
    cliente = _client_para(app, head)
    assert _put(cliente, demanda["id"], etapa["id"], [], [outro_dep.id]).status_code == 422  # fora do que ele lidera
    assert _put(cliente, demanda["id"], etapa["id"], [], [dep_head.id]).status_code == 200

    comum = operadores[1]
    _patch(client_admin, demanda["id"], usuarioResponsavelIds=[head.id, comum.id])
    cliente_comum = _client_para(app, comum)
    r = _put(cliente_comum, demanda["id"], etapa["id"], [operadores[2].id])  # atribuir alguém fora do próprio contexto
    assert r.status_code == 422
    assert _put(cliente_comum, demanda["id"], etapa["id"], [comum.id]).status_code == 200  # a si mesmo pode


def test_quem_nao_enxerga_a_demanda_recebe_404(app, client_admin: TestClient, operadores: list[Usuario]) -> None:
    demanda = _tres_etapas(client_admin)
    assert _put(_client_para(app, operadores[0]), demanda["id"], _etapa_de(demanda, 1)["id"], [operadores[0].id]).status_code == 404


# --------------------------------------------------------------------------------------
# Efeitos: sessão, iniciar trabalho
# --------------------------------------------------------------------------------------


def test_remover_o_responsavel_da_etapa_encerra_a_sessao_dele_uma_so_vez(db_session: Session, app, client_admin: TestClient, operadores: list[Usuario]) -> None:
    a, b = operadores[0], operadores[1]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte")], usuarioResponsavelIds=[a.id, b.id])
    etapa = _etapa_de(demanda, 1)
    _put(client_admin, demanda["id"], etapa["id"], [a.id, b.id])
    _patch(client_admin, demanda["id"], status="em_execucao")
    sessao_a = _abrir_ok(client_admin, demanda["id"], a.id)
    sessao_b = _abrir_ok(client_admin, demanda["id"], b.id)

    assert _put(client_admin, demanda["id"], etapa["id"], [b.id]).status_code == 200
    antiga = _sessao(db_session, sessao_a["id"])
    assert antiga.status == "encerrada" and antiga.motivo_encerramento == "troca_responsavel"
    assert _sessao(db_session, sessao_b["id"]).status == "ativa"  # quem continua responsável não é tocado
    db_session.expire_all()
    fins = db_session.scalars(select(Evento).where(Evento.entidade_id == demanda["id"], Evento.tipo == "sessao_trabalho_encerrada")).all()
    assert len(fins) == 1  # um só evento de encerramento


def test_voltar_a_herdar_mantem_a_sessao_de_quem_ainda_e_responsavel_pela_tarefa(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    a = operadores[0]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação")], usuarioResponsavelIds=[a.id])
    etapa = _etapa_de(demanda, 1)
    _put(client_admin, demanda["id"], etapa["id"], [a.id])
    _patch(client_admin, demanda["id"], status="em_execucao")
    sessao = _abrir_ok(client_admin, demanda["id"], a.id)
    _put(client_admin, demanda["id"], etapa["id"], [], [])  # herda: A continua responsável (geral)
    assert _sessao(db_session, sessao["id"]).status == "ativa"


def test_iniciar_trabalho_e_a_lista_refletem_a_nova_responsabilidade(app, client_admin: TestClient, operadores: list[Usuario]) -> None:
    raquel, joao = operadores[0], operadores[1]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Redação"), _etapa("Arte")], usuarioResponsavelIds=[raquel.id, joao.id])
    etapa = _etapa_de(demanda, 1)
    _put(client_admin, demanda["id"], etapa["id"], [raquel.id])
    pode = lambda u: next(d for d in _client_para(app, u).get("/demandas", params={"limit": 200}).json() if d["id"] == demanda["id"])["podeIniciarTrabalho"]  # noqa: E731
    assert pode(raquel) is True and pode(joao) is False  # a etapa explícita vence o geral
    _put(client_admin, demanda["id"], etapa["id"], [], [])
    assert pode(joao) is True  # voltou a herdar


# --------------------------------------------------------------------------------------
# Criação
# --------------------------------------------------------------------------------------


def _modelo(client: TestClient, etapas: list[dict]) -> dict:
    resposta = client.post("/workflow-modelos", json={"nome": f"Modelo {uuid.uuid4().hex[:8]}", "etapas": etapas})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _ids_do_modelo(modelo: dict) -> list[str]:
    return [e["id"] for e in sorted(modelo["etapas"], key=lambda e: e["ordem"])]


def test_criacao_com_responsaveis_por_etapa_associa_cada_etapa_certa(client_admin: TestClient, operadores: list[Usuario]) -> None:
    raquel, joao, ana = operadores[0], operadores[1], operadores[2]
    modelo = _modelo(client_admin, [_etapa("Redação"), _etapa("Direção de Arte"), _etapa("Aprovação interna", "aprovacao", usuarios=[ana.id])])
    e1, e2, e3 = _ids_do_modelo(modelo)
    r = client_admin.post(
        "/demandas",
        json={
            "nome": "Com responsáveis por etapa",
            "workflowModeloId": modelo["id"],
            "workflowEtapasResponsaveis": [
                {"modeloEtapaId": e1, "usuarioResponsavelIds": [raquel.id]},
                {"modeloEtapaId": e2, "usuarioResponsavelIds": [joao.id]},
            ],
        },
    )
    assert r.status_code == 201, r.text
    etapas = _por_ordem(r.json())
    assert [x["usuarioResponsavelIds"] for x in etapas] == [[raquel.id], [joao.id], [ana.id]]  # a 3ª (não enviada) segue o MODELO
    assert [x["responsabilidadeEfetiva"]["origem"] for x in etapas] == ["etapa", "etapa", "etapa"]


def test_criacao_sem_o_campo_novo_e_identica_a_legada(client_admin: TestClient, operadores: list[Usuario]) -> None:
    ana = operadores[0]
    modelo = _modelo(client_admin, [_etapa("A", usuarios=[ana.id]), _etapa("B")])
    r = client_admin.post("/demandas", json={"nome": "Legada", "workflowModeloId": modelo["id"]})
    assert r.status_code == 201
    assert [x["usuarioResponsavelIds"] for x in _por_ordem(r.json())] == [[ana.id], []]


def test_criacao_override_vazio_remove_o_que_o_modelo_trazia_e_herda_a_tarefa(client_admin: TestClient, operadores: list[Usuario]) -> None:
    ana, milenna = operadores[0], operadores[1]
    modelo = _modelo(client_admin, [_etapa("A", usuarios=[ana.id])])
    (e1,) = _ids_do_modelo(modelo)
    r = client_admin.post(
        "/demandas",
        json={"nome": "Herda", "workflowModeloId": modelo["id"], "usuarioResponsavelIds": [milenna.id], "workflowEtapasResponsaveis": [{"modeloEtapaId": e1}]},
    )
    assert r.status_code == 201, r.text
    assert _efetiva(r.json(), 1) == {"origem": "tarefa", "usuarioIds": [milenna.id], "departamentoIds": []}


def test_criacao_valida_contrato_e_nao_deixa_demanda_parcial(db_session: Session, client_admin: TestClient, empresa: Empresa, outra_empresa: Empresa, operadores: list[Usuario]) -> None:
    modelo = _modelo(client_admin, [_etapa("A"), _etapa("B")])
    outro_modelo = _modelo(client_admin, [_etapa("X")])
    e1, _ = _ids_do_modelo(modelo)
    (x1,) = _ids_do_modelo(outro_modelo)
    estranho = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="estranho3")
    antes = db_session.scalar(text("SELECT count(*) FROM demandas"))
    base = {"nome": "Inválida", "workflowModeloId": modelo["id"]}
    assert client_admin.post("/demandas", json={"nome": "x", "workflowEtapasResponsaveis": [{"modeloEtapaId": e1}]}).status_code == 422  # sem modelo
    assert client_admin.post("/demandas", json={**base, "workflowEtapasResponsaveis": [{"modeloEtapaId": x1}]}).status_code == 422  # etapa de OUTRO modelo
    assert client_admin.post("/demandas", json={**base, "workflowEtapasResponsaveis": [{"modeloEtapaId": e1}, {"modeloEtapaId": e1}]}).status_code == 422  # repetida
    assert client_admin.post("/demandas", json={**base, "workflowEtapasResponsaveis": [{"modeloEtapaId": e1, "usuarioResponsavelIds": [estranho.id]}]}).status_code == 422
    assert db_session.scalar(text("SELECT count(*) FROM demandas")) == antes  # nenhuma Demanda criada


def test_falha_no_meio_da_criacao_desfaz_demanda_etapas_e_eventos(db_session: Session, client_admin: TestClient, operadores: list[Usuario], monkeypatch: pytest.MonkeyPatch) -> None:
    modelo = _modelo(client_admin, [_etapa("A"), _etapa("B")])
    e1, _ = _ids_do_modelo(modelo)
    db_session.commit()
    antes = (db_session.scalar(text("SELECT count(*) FROM demandas")), db_session.scalar(text("SELECT count(*) FROM demanda_workflow_etapas")),
             db_session.scalar(text("SELECT count(*) FROM eventos WHERE tipo = 'demanda.criada'")))

    def quebra(*_a, **_k):
        raise RuntimeError("falha ao gravar responsáveis das etapas")

    monkeypatch.setattr("app.repositories.demanda_repository.DemandaRepository.criar_etapa_responsaveis", quebra)
    cliente = TestClient(client_admin.app, raise_server_exceptions=False, headers=dict(client_admin.headers))
    r = cliente.post("/demandas", json={"nome": "Quebra", "workflowModeloId": modelo["id"], "workflowEtapasResponsaveis": [{"modeloEtapaId": e1, "usuarioResponsavelIds": [operadores[0].id]}]})
    assert r.status_code == 500
    monkeypatch.undo()
    depois = (db_session.scalar(text("SELECT count(*) FROM demandas")), db_session.scalar(text("SELECT count(*) FROM demanda_workflow_etapas")),
              db_session.scalar(text("SELECT count(*) FROM eventos WHERE tipo = 'demanda.criada'")))
    assert depois == antes  # nem Demanda, nem etapas, nem evento órfão


def test_leitura_traz_a_origem_em_lista_e_detalhe_sem_consulta_por_etapa(db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    from sqlalchemy import event

    for _ in range(2):
        _tres_etapas(client_admin, usuarioResponsavelIds=[operadores[0].id])

    def contar() -> int:
        comandos: list[str] = []

        def capturar(conn, cursor, statement, parameters, context, executemany):
            comandos.append(statement)

        engine = db_session.get_bind()
        client_admin.get("/demandas", params={"limit": 200})
        event.listen(engine, "before_cursor_execute", capturar)
        try:
            lista = client_admin.get("/demandas", params={"limit": 200}).json()
        finally:
            event.remove(engine, "before_cursor_execute", capturar)
        assert all(e["responsabilidadeEfetiva"]["origem"] == "tarefa" for d in lista for e in d["workflowEtapas"])
        return len(comandos)

    pouco = contar()
    for _ in range(5):
        _tres_etapas(client_admin, usuarioResponsavelIds=[operadores[0].id])
    assert contar() == pouco  # custo constante: a origem sai dos dados já carregados em lote


def test_servico_publico_resolve_pela_mesma_regra_pura() -> None:
    from app.core.executor_etapa import resolver_responsabilidade_etapa

    assert resolver_responsabilidade_etapa(etapa_usuario_ids=[], etapa_departamento_ids=["d"], demanda_usuario_ids=["u"], demanda_departamento_ids=[]) == ("etapa", [], ["d"])
    assert resolver_responsabilidade_etapa(etapa_usuario_ids=[], etapa_departamento_ids=[], demanda_usuario_ids=["u"], demanda_departamento_ids=["x"]) == ("tarefa", ["u"], ["x"])
    assert resolver_responsabilidade_etapa(etapa_usuario_ids=[], etapa_departamento_ids=[], demanda_usuario_ids=[], demanda_departamento_ids=[]) == ("nenhuma", [], [])
    assert DemandaService is not None
