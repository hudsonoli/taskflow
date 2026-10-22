"""Kanban → "iniciar trabalho": arrastar para Em execução inicia/troca a sessão pessoal de quem EXECUTA a etapa, numa transação só.

`POST /demandas/{id}/iniciar-trabalho` (comando explícito — nenhum PATCH de status abre sessão):
- executor da etapa atual: status → em_execucao + encerra a sessão dele em OUTRA demanda + abre a desta;
- quem não é executor (gestor organizando o trabalho de outros): só o status, sem sessão pessoal;
- nunca pausa a demanda anterior nem toca nas sessões de outros responsáveis; falha desfaz tudo.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.executor_etapa import eh_executor_da_demanda
from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.empresa import Empresa
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.services.demanda_service import DemandaService
from app.services.sessao_trabalho_service import SessaoTrabalhoService
from tests.test_d1_criacao_demandas import _client_para
from tests.test_demanda import dentro_do_expediente  # noqa: F401  (fixture)
from tests.test_fase_8a_workflow_progressao import _etapa
from tests.test_sessao_trabalho_integridade import _abrir_ok, _demanda, _demanda_com_workflow, _patch, _sessao, _sessoes, operadores  # noqa: F401  (fixture `operadores`)


@pytest.fixture(autouse=True)
def _expediente_aberto(dentro_do_expediente) -> None:  # noqa: F811
    """Entrar em execução respeita o expediente — a janela é fixada para o teste não depender da hora."""


def _iniciar(client: TestClient, demanda_id: str):
    return client.post(f"/demandas/{demanda_id}/iniciar-trabalho")


def _ativas(db: Session, usuario_id: str) -> list[SessaoTrabalho]:
    db.expire_all()
    return list(db.scalars(select(SessaoTrabalho).where(SessaoTrabalho.usuario_id == usuario_id, SessaoTrabalho.status == "ativa")).all())


def _responsaveis(client_admin: TestClient, demanda_id: str, *usuarios: Usuario) -> None:
    _patch(client_admin, demanda_id, usuarioResponsavelIds=[u.id for u in usuarios])


def _rascunho(client_admin: TestClient, *responsaveis: Usuario) -> dict:
    demanda = _demanda(client_admin, executando=False)
    if responsaveis:
        _responsaveis(client_admin, demanda["id"], *responsaveis)
    return demanda


def _status(db: Session, demanda_id: str) -> str:
    db.expire_all()
    return db.get(Demanda, demanda_id).status


# --------------------------------------------------------------------------------------
# A, B — o responsável inicia e troca o foco
# --------------------------------------------------------------------------------------


def test_responsavel_arrasta_para_em_execucao_e_abre_a_propria_sessao(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    op = operadores[0]
    b = _rascunho(client_admin, op)
    resposta = _iniciar(_client_para(app, op), b["id"])
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "em_execucao" and corpo["trabalhandoAgora"] is True
    (sessao,) = _ativas(db_session, op.id)
    assert sessao.demanda_id == b["id"]


def test_responsavel_em_a_arrasta_b_e_troca_atomicamente(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    op = operadores[0]
    a = _demanda(client_admin)
    _responsaveis(client_admin, a["id"], op)
    sessao_a = _abrir_ok(client_admin, a["id"], op.id)
    b = _rascunho(client_admin, op)

    assert _iniciar(_client_para(app, op), b["id"]).status_code == 200

    antiga = _sessao(db_session, sessao_a["id"])
    assert antiga.status == "encerrada" and antiga.motivo_encerramento == "substituicao_sessao_ativa"
    (ativa,) = _ativas(db_session, op.id)
    assert ativa.demanda_id == b["id"]
    assert _status(db_session, a["id"]) == "em_execucao"  # A NÃO é pausada: outra pessoa pode estar trabalhando nela


# --------------------------------------------------------------------------------------
# C, H — quem não executa não ganha sessão
# --------------------------------------------------------------------------------------


def test_gestor_nao_responsavel_move_o_status_sem_criar_sessao_pessoal(
    db_session: Session, client_admin: TestClient, client_gestor: TestClient, usuario_gestor: Usuario, operadores: list[Usuario]
) -> None:
    joao = operadores[0]
    b = _rascunho(client_admin, joao)
    resposta = _iniciar(client_gestor, b["id"])
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "em_execucao" and resposta.json()["trabalhandoAgora"] is False and resposta.json()["podeIniciarTrabalho"] is False
    assert _ativas(db_session, usuario_gestor.id) == []  # o gestor organizou; não está executando
    assert _sessoes(db_session, b["id"]) == []  # nem a sessão de João foi criada por ele


def test_gestor_nao_executor_nao_encerra_nem_troca_nada_dele_mesmo(
    db_session: Session, client_admin: TestClient, client_gestor: TestClient, usuario_gestor: Usuario, operadores: list[Usuario]
) -> None:
    """Mesmo com sessão ativa própria em outra demanda, mover uma tarefa alheia não troca o foco do gestor."""
    a = _demanda(client_admin)
    sessao = _abrir_ok(client_admin, a["id"], usuario_gestor.id)
    b = _rascunho(client_admin, operadores[0])
    assert _iniciar(client_gestor, b["id"]).status_code == 200
    assert _sessao(db_session, sessao["id"]).status == "ativa"


def test_operador_nao_executor_so_move_o_status_se_o_rbac_permitir_e_nao_ganha_sessao(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    dono, intruso = operadores[0], operadores[1]
    b = _rascunho(client_admin, dono)
    resposta = _iniciar(_client_para(app, intruso), b["id"])  # fora do escopo-base: 404, igual ao PATCH
    assert resposta.status_code == 404
    assert _status(db_session, b["id"]) == "rascunho" and _ativas(db_session, intruso.id) == []


def test_demanda_ja_em_execucao_por_quem_nao_e_executor_e_403(app, client_admin: TestClient, operadores: list[Usuario], db_session: Session) -> None:
    """Responsável da DEMANDA mas não da etapa atual: não há transição nem sessão a abrir — resposta explícita, sem no-op silencioso."""
    dono, outro = operadores[0], operadores[1]
    modelo = _demanda_com_workflow(client_admin, [_etapa("Etapa 1", usuarios=[outro.id]), _etapa("Etapa 2")])
    _responsaveis(client_admin, modelo["id"], dono, outro)
    _patch(client_admin, modelo["id"], status="em_execucao")
    resposta = _iniciar(_client_para(app, dono), modelo["id"])
    assert resposta.status_code == 403 and _ativas(db_session, dono.id) == []


# --------------------------------------------------------------------------------------
# D — multi-responsável
# --------------------------------------------------------------------------------------


def test_multi_responsavel_so_o_ator_troca_a_sessao(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    hudson, joao = operadores[0], operadores[1]
    a = _demanda(client_admin)
    _responsaveis(client_admin, a["id"], hudson, joao)
    sessao_hudson = _abrir_ok(client_admin, a["id"], hudson.id)
    sessao_joao = _abrir_ok(client_admin, a["id"], joao.id)
    b = _rascunho(client_admin, hudson, joao)

    assert _iniciar(_client_para(app, hudson), b["id"]).status_code == 200

    assert _sessao(db_session, sessao_hudson["id"]).status == "encerrada"
    assert _sessao(db_session, sessao_joao["id"]).status == "ativa"  # João segue em A
    assert [s.demanda_id for s in _ativas(db_session, hudson.id)] == [b["id"]]
    assert _ativas(db_session, joao.id)[0].demanda_id == a["id"]
    assert _status(db_session, a["id"]) == "em_execucao"


# --------------------------------------------------------------------------------------
# G, 9 — botão em demanda já em execução; sem redundância
# --------------------------------------------------------------------------------------


def test_iniciar_trabalho_em_demanda_que_ja_esta_em_execucao_abre_so_a_sessao(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    op = operadores[0]
    b = _demanda(client_admin)  # já em execução (outra pessoa/gestor colocou)
    _responsaveis(client_admin, b["id"], op)
    lista = _client_para(app, op).get("/demandas", params={"limit": 200}).json()
    item = next(d for d in lista if d["id"] == b["id"])
    assert item["status"] == "em_execucao" and item["podeIniciarTrabalho"] is True and item["trabalhandoAgora"] is False

    resposta = _iniciar(_client_para(app, op), b["id"])
    assert resposta.status_code == 200 and resposta.json()["trabalhandoAgora"] is True
    assert [s.demanda_id for s in _ativas(db_session, op.id)] == [b["id"]]


def test_iniciar_de_novo_na_mesma_demanda_e_idempotente(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    op = operadores[0]
    b = _rascunho(client_admin, op)
    cliente = _client_para(app, op)
    primeira = _iniciar(cliente, b["id"]).json()
    segunda = _iniciar(cliente, b["id"])
    assert segunda.status_code == 200 and segunda.json()["trabalhandoAgora"] is True
    assert len(_sessoes(db_session, b["id"])) == 1  # nenhuma segunda sessão, nenhum 409
    assert primeira["status"] == "em_execucao"


def test_flags_da_listagem_sem_consulta_extra_por_item(app, client_admin: TestClient, db_session: Session, operadores: list[Usuario]) -> None:
    from collections import Counter

    from sqlalchemy import event

    op = operadores[0]
    cliente = _client_para(app, op)
    for _ in range(2):
        _rascunho(client_admin, op)

    def comandos() -> Counter:
        cliente.get("/demandas", params={"limit": 200})  # aquece (objetos expirados por commits anteriores são recarregados 1x, não por item)
        capturados: list[str] = []

        def capturar(conn, cursor, statement, parameters, context, executemany):
            capturados.append(" ".join(statement.split())[:160])

        engine = db_session.get_bind()
        event.listen(engine, "before_cursor_execute", capturar)
        try:
            assert cliente.get("/demandas", params={"limit": 200}).status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", capturar)
        return Counter(capturados)

    cliente.get("/demandas")  # aquece caches
    pouco = comandos()
    for _ in range(6):
        _rascunho(client_admin, op)
    muito = comandos()
    assert muito == pouco, {k: (pouco.get(k, 0), v) for k, v in muito.items() if v != pouco.get(k, 0)}


# --------------------------------------------------------------------------------------
# E — atomicidade; I — intervalos
# --------------------------------------------------------------------------------------


def test_falha_ao_abrir_a_sessao_desfaz_tambem_a_mudanca_de_status_e_o_encerramento_da_anterior(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario], monkeypatch: pytest.MonkeyPatch
) -> None:
    op = operadores[0]
    a = _demanda(client_admin)
    _responsaveis(client_admin, a["id"], op)
    sessao_a = _abrir_ok(client_admin, a["id"], op.id)
    b = _rascunho(client_admin, op)

    def quebra(self, *args, **kwargs):
        raise RuntimeError("falha simulada ao abrir a sessão")

    monkeypatch.setattr(SessaoTrabalhoService, "abrir", quebra)
    cliente = _client_para(app, op)
    cliente_sem_propagar = TestClient(app, raise_server_exceptions=False, headers=dict(cliente.headers))
    assert _iniciar(cliente_sem_propagar, b["id"]).status_code == 500
    monkeypatch.undo()

    assert _status(db_session, b["id"]) == "rascunho"  # a transição para em_execucao NÃO ficou pela metade
    assert _sessao(db_session, sessao_a["id"]).status == "ativa"
    assert db_session.scalar(text("SELECT count(*) FROM demanda_status_intervalos WHERE demanda_id=:d AND status='em_execucao'"), {"d": b["id"]}) == 0


def test_etapa_atual_pausada_move_o_status_e_nao_cria_sessao(
    app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    """Etapa atual PAUSADA: o executor não é elegível a sessão — o comando não finge trabalho: o status é movido (organização) e nenhuma sessão nasce."""
    op = operadores[0]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Única", usuarios=[op.id])])
    _responsaveis(client_admin, demanda["id"], op)  # responsável da DEMANDA (escopo-base); a etapa atual pausada não admite sessão
    db_session.execute(text("UPDATE demanda_workflow_etapas SET status='pausada' WHERE demanda_id=:d"), {"d": demanda["id"]})
    db_session.flush()
    resposta = _iniciar(_client_para(app, op), demanda["id"])
    assert resposta.status_code == 200 and resposta.json()["trabalhandoAgora"] is False
    assert _ativas(db_session, op.id) == []


def test_intervalos_operacionais_seguem_o_status_e_nao_a_sessao(app, db_session: Session, client_admin: TestClient, operadores: list[Usuario]) -> None:
    op = operadores[0]
    a = _demanda(client_admin)
    _responsaveis(client_admin, a["id"], op)
    _abrir_ok(client_admin, a["id"], op.id)
    b = _rascunho(client_admin, op)

    def intervalos(demanda_id: str) -> list[tuple]:
        return sorted(
            tuple(linha)
            for linha in db_session.execute(
                text("SELECT status, fim_em IS NULL FROM demanda_status_intervalos WHERE demanda_id = :d"), {"d": demanda_id}
            ).all()
        )

    antes_a = intervalos(a["id"])
    _iniciar(_client_para(app, op), b["id"])
    assert intervalos(a["id"]) == antes_a  # A: nenhum intervalo aberto/fechado pela troca de foco
    abertos_b = [linha for linha in intervalos(b["id"]) if linha[1]]
    assert abertos_b == [("em_execucao", True)]  # B: exatamente o intervalo de status em execução, aberto


# --------------------------------------------------------------------------------------
# Regra pura do executor
# --------------------------------------------------------------------------------------


class _E:
    def __init__(self, ordem, status, usuarios=(), departamentos=()):
        self.ordem, self.status = ordem, status
        self.usuario_responsavel_ids, self.departamento_responsavel_ids = list(usuarios), list(departamentos)


class _U:
    def __init__(self, id, departamento_id=None):
        self.id, self.departamento_id = id, departamento_id


def test_regra_pura_do_executor() -> None:
    eu, outro = _U("eu", "dep-1"), _U("outro", "dep-9")
    etapas = [_E(1, "concluida", ["outro"]), _E(2, "pendente", ["eu"]), _E(3, "pendente", ["outro"])]
    assert eh_executor_da_demanda(eu, etapas=etapas, demanda_usuario_ids=[], demanda_departamento_ids=[]) is True  # só a ETAPA ATUAL conta
    assert eh_executor_da_demanda(outro, etapas=etapas, demanda_usuario_ids=["outro"], demanda_departamento_ids=[]) is False  # responsável de etapa futura não executa agora
    assert eh_executor_da_demanda(eu, etapas=[_E(1, "pendente", [], ["dep-1"])], demanda_usuario_ids=[], demanda_departamento_ids=[]) is True  # membro do departamento da etapa
    assert eh_executor_da_demanda(eu, etapas=[_E(1, "pausada", ["eu"])], demanda_usuario_ids=[], demanda_departamento_ids=[]) is False
    assert eh_executor_da_demanda(eu, etapas=[_E(1, "concluida", ["eu"])], demanda_usuario_ids=["eu"], demanda_departamento_ids=[]) is False  # workflow concluído
    assert eh_executor_da_demanda(eu, etapas=[_E(1, "pendente")], demanda_usuario_ids=["eu"], demanda_departamento_ids=[]) is True  # etapa sem responsáveis: vale a Demanda
    assert eh_executor_da_demanda(eu, etapas=[], demanda_usuario_ids=["eu"], demanda_departamento_ids=[]) is True  # sem workflow
    assert eh_executor_da_demanda(outro, etapas=[], demanda_usuario_ids=["eu"], demanda_departamento_ids=["dep-1"]) is False


# --------------------------------------------------------------------------------------
# F — concorrência real
# --------------------------------------------------------------------------------------


@pytest.fixture()
def cenario_commitado(test_engine):
    Fabrica = sessionmaker(bind=test_engine)
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(timezone.utc)
    with Fabrica() as db:
        empresa = Empresa(id=str(uuid.uuid4()), nome="Empresa Foco", codigo_interno=f"FOCO-{sufixo}".upper(), status="ativa", created_at=agora, updated_at=agora)
        db.add(empresa)
        db.flush()
        usuario = Usuario(
            id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"foco-{sufixo}", nome="Operador Foco", email=f"foco-{sufixo}@teste.taskfloww.local",
            perfil_base="operador", acesso_sistema=True, status="ativo", created_at=agora, updated_at=agora,
        )
        db.add(usuario)
        db.flush()
        demandas = []
        for i in (1, 2, 3):
            demanda = Demanda(
                id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"F26{sufixo[:5]}{i}", ano_referencia=26, sequencial_referencia=i,
                numero_operacional=i, identificador=f"#{i}", nome=f"Foco {i}", status="planejada", prioridade="media", sinalizada=False, created_at=agora, updated_at=agora,
            )
            db.add(demanda)
            db.flush()
            db.add(DemandaResponsavel(demanda_id=demanda.id, usuario_id=usuario.id, created_at=agora))
            demandas.append(demanda.id)
        db.commit()
        ids = {"empresa": empresa.id, "usuario": usuario.id, "demandas": demandas}
    try:
        yield Fabrica, ids
    finally:
        with Fabrica() as db:
            db.execute(text("DELETE FROM regra_expediente WHERE empresa_id = :e"), {"e": ids["empresa"]})
            for tabela in ("sessoes_trabalho", "eventos"):
                db.execute(text(f"DELETE FROM {tabela} WHERE empresa_id = :e"), {"e": ids["empresa"]})
            db.execute(text("DELETE FROM demandas WHERE empresa_id = :e"), {"e": ids["empresa"]})
            db.execute(text("DELETE FROM usuarios WHERE empresa_id = :e"), {"e": ids["empresa"]})
            db.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": ids["empresa"]})
            db.commit()


def test_corrida_de_inicios_nunca_deixa_duas_sessoes_abertas(cenario_commitado) -> None:
    Fabrica, ids = cenario_commitado
    barreira = threading.Barrier(3)
    resultados: list[str] = []
    trava = threading.Lock()

    def iniciar(demanda_id: str) -> None:
        with Fabrica() as db:
            servico = DemandaService()
            ator = db.get(Usuario, ids["usuario"])
            demanda = db.get(Demanda, demanda_id)
            barreira.wait(timeout=10)
            try:
                servico.iniciar_trabalho(db, demanda, actor=ator)
                saida = "ok"
            except Exception as exc:  # noqa: BLE001 — só o TIPO importa: conflito de domínio é válido, 500 não
                saida = type(exc).__name__
            with trava:
                resultados.append(saida)

    threads = [threading.Thread(target=iniciar, args=(d,)) for d in ids["demandas"]]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert all(r in ("ok", "SessaoTrabalhoConflitoError") for r in resultados), resultados
    assert "ok" in resultados
    with Fabrica() as db:
        ativas = db.scalar(select(func.count()).select_from(SessaoTrabalho).where(SessaoTrabalho.usuario_id == ids["usuario"], SessaoTrabalho.status == "ativa"))
        assert ativas == 1  # o índice único parcial é a barreira final
        # toda demanda cuja transição "perdeu" não ficou em_execucao sem causa: quem deu conflito foi desfeito por inteiro
        em_execucao = db.scalar(select(func.count()).select_from(Demanda).where(Demanda.empresa_id == ids["empresa"], Demanda.status == "em_execucao"))
        assert em_execucao == resultados.count("ok")
