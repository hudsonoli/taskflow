"""Fase 8C — notificação da PRÓXIMA etapa do Workflow na central existente (sem tabela, sem canal novo).

Quando a etapa atual é concluída/aprovada e a próxima passa a ser a atual, UM evento `demanda.workflow_etapa_atualizada` (na mesma transação da
progressão) leva os destinatários no payload: responsáveis individuais + Head de cada departamento responsável, sem duplicados, só gente ativa,
com acesso e da MESMA empresa. Retry/concorrência (409) não geram nada; a última etapa não gera; etapa sem responsável não falha. A central, o
contador e o "lida" são os de sempre.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.workflow_destinatarios import destinatarios_da_etapa
from app.models.demanda import Demanda
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _client_para, _operador_comum
from tests.test_demanda import _departamento
from tests.test_fase_8a_workflow_progressao import _demanda_com_workflow, _etapa, _por_ordem, _url

TIPO = "demanda.workflow_etapa_atualizada"


# ======================================================================================
# helpers
# ======================================================================================


def _central(client: TestClient) -> list[dict]:
    resposta = client.get("/notificacoes", params={"limit": 100})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["itens"]


def _da_etapa(client: TestClient, demanda_id: str | None = None) -> list[dict]:
    return [n for n in _central(client) if n["tipo"] == TIPO and (demanda_id is None or n["demandaId"] == demanda_id)]


def _resumo(client: TestClient) -> dict:
    resposta = client.get("/notificacoes/resumo")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["naoLidas"]


def _eventos(db: Session, demanda_id: str) -> list[Evento]:
    return list(db.scalars(select(Evento).where(Evento.entidade_id == demanda_id, Evento.tipo == TIPO).order_by(Evento.occurred_at.asc())).all())


def _avancar(client: TestClient, demanda: dict, ordem: int, acao: str = "concluir"):
    etapa = _por_ordem(demanda)[ordem - 1]
    return client.post(_url(demanda["id"], etapa["id"], acao))


def _op(db: Session, empresa: Empresa, nome: str) -> Usuario:
    return _operador_comum(db, empresa, sufixo=f"8c-{nome}-{uuid.uuid4().hex[:4]}")


# ======================================================================================
# destinatários
# ======================================================================================


def test_responsavel_individual_da_proxima_etapa_recebe_com_titulo_e_destino(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "a")
    demanda = _demanda_com_workflow(
        client_admin,
        [_etapa("Criação"), _etapa("Revisão final", usuarios=[a.id]), _etapa("Publicação")],
    )
    db_session.commit()
    ca = _client_para(app, a)
    assert _da_etapa(ca) == [] and _resumo(ca)["total"] == 0

    assert _avancar(client_admin, demanda, 1).status_code == 200
    itens = _da_etapa(ca, demanda["id"])
    assert len(itens) == 1
    n = itens[0]
    assert n["titulo"] == "Nova etapa de Workflow disponível"
    assert n["detalhe"] == "Etapa 2: Revisão final"
    assert n["demandaId"] == demanda["id"] and n["demandaNome"] == demanda["nome"]
    assert n["demandaIdentificador"] == demanda["identificador"]  # o persistido, não um #número montado
    assert n["lida"] is False and n["categoria"] == "minhas"
    assert _resumo(ca)["total"] == 1 and _resumo(ca)["minhas"] == 1


def test_etapa_de_aprovacao_usa_o_texto_de_aprovacao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    b = _op(db_session, empresa, "b")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Criar"), _etapa("Aprovar arte", "aprovacao", usuarios=[b.id])])
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200
    (n,) = _da_etapa(_client_para(app, b))
    assert n["titulo"] == "Uma etapa de aprovação está aguardando você"
    assert n["detalhe"] == "Etapa 2: Aprovar arte"


def test_aprovar_etapa_de_aprovacao_notifica_a_proxima_de_execucao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    c = _op(db_session, empresa, "c")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao"), _etapa("Publicar", usuarios=[c.id])])
    db_session.commit()
    assert _avancar(client_admin, demanda, 1, "aprovar").status_code == 200
    (n,) = _da_etapa(_client_para(app, c))
    assert n["titulo"] == "Nova etapa de Workflow disponível" and n["detalhe"] == "Etapa 2: Publicar"


def test_dois_responsaveis_recebem_e_duplicata_e_removida(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b = _op(db_session, empresa, "a"), _op(db_session, empresa, "b")
    # `a` é responsável individual E Head (formal) do departamento responsável: continua UMA notificação
    dep = _departamento(db_session, empresa, nome="Mídia", responsavel_usuario_id=a.id)
    demanda = _demanda_com_workflow(client_admin, [_etapa("Um"), _etapa("Dois", usuarios=[a.id, b.id], departamentos=[dep.id])])
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200
    assert len(_da_etapa(_client_para(app, a))) == 1
    assert len(_da_etapa(_client_para(app, b))) == 1
    (evento,) = _eventos(db_session, demanda["id"])
    assert sorted(evento.payload["destinatarioUsuarioIds"]) == sorted([a.id, b.id])  # sem repetição


def test_head_do_departamento_responsavel_recebe_e_demais_nao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    head_formal = _op(db_session, empresa, "headf")
    head_lider = _op(db_session, empresa, "headl")
    membro = _op(db_session, empresa, "membro")
    head_de_outro = _op(db_session, empresa, "outro")
    criacao = _departamento(db_session, empresa, nome="Criação", responsavel_usuario_id=head_formal.id)
    social = _departamento(db_session, empresa, nome="Social", responsavel_usuario_id=head_de_outro.id)
    head_lider.departamento_id, head_lider.lider_departamento = criacao.id, True  # Head por liderança dentro do departamento
    membro.departamento_id = criacao.id  # membro comum: NÃO é notificado
    db_session.flush()
    outra_lider = _op(db_session, empresa, "lider-social")
    outra_lider.departamento_id, outra_lider.lider_departamento = social.id, True
    demanda = _demanda_com_workflow(client_admin, [_etapa("Antes"), _etapa("No departamento", departamentos=[criacao.id])])
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200

    assert len(_da_etapa(_client_para(app, head_formal))) == 1
    assert len(_da_etapa(_client_para(app, head_lider))) == 1
    assert _da_etapa(_client_para(app, membro)) == []
    assert _da_etapa(_client_para(app, head_de_outro)) == []  # Head de OUTRO departamento
    assert _da_etapa(_client_para(app, outra_lider)) == []
    (evento,) = _eventos(db_session, demanda["id"])
    assert sorted(evento.payload["destinatarioUsuarioIds"]) == sorted([head_formal.id, head_lider.id])


def test_inativo_sem_acesso_e_conta_de_sistema_nao_recebem(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    ativo = _op(db_session, empresa, "ativo")
    inativo, bloqueado, sem_acesso, sistema = (_op(db_session, empresa, n) for n in ("inativo", "bloq", "semacesso", "sistema"))
    todos = [ativo, inativo, bloqueado, sem_acesso, sistema]
    demanda = _demanda_com_workflow(client_admin, [_etapa("Um"), _etapa("Dois")])
    etapa2 = _por_ordem(demanda)[1]
    agora = datetime.now(timezone.utc)
    for u in todos:
        db_session.add(DemandaWorkflowEtapaResponsavel(demanda_workflow_etapa_id=etapa2["id"], usuario_id=u.id, created_at=agora))
    inativo.status, bloqueado.status = "inativo", "bloqueado"
    sem_acesso.acesso_sistema = False
    sistema.is_system_account = True
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200
    (evento,) = _eventos(db_session, demanda["id"])
    assert evento.payload["destinatarioUsuarioIds"] == [ativo.id]
    assert len(_da_etapa(_client_para(app, ativo))) == 1
    for u in (inativo, bloqueado, sem_acesso):  # nem autenticam; e mesmo que lessem a central, nada foi endereçado a eles
        resposta = _client_para(app, u).get("/notificacoes", params={"limit": 100})
        assert resposta.status_code in (401, 403) or [n for n in resposta.json()["itens"] if n["tipo"] == TIPO] == []


def test_cross_tenant_nunca_e_destinatario(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient) -> None:
    meu = _op(db_session, empresa, "meu")
    de_fora = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="8c-fora")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Um"), _etapa("Dois", usuarios=[meu.id])])
    etapa2 = _por_ordem(demanda)[1]
    # dado inconsistente de propósito: um responsável de OUTRA empresa gravado na etapa
    db_session.add(DemandaWorkflowEtapaResponsavel(demanda_workflow_etapa_id=etapa2["id"], usuario_id=de_fora.id, created_at=datetime.now(timezone.utc)))
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200
    (evento,) = _eventos(db_session, demanda["id"])
    assert evento.payload["destinatarioUsuarioIds"] == [meu.id]
    assert _da_etapa(_client_para(app, de_fora)) == []
    # o filtro é do serviço, por empresa da DEMANDA — e pergunta direta também respeita o tenant
    assert destinatarios_da_etapa(db_session, empresa_id=outra_empresa.id, usuario_responsavel_ids=[meu.id], departamento_responsavel_ids=[]) == []


def test_atores_podem_receber_normalmente(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    """Sem exceção especial: quem concluiu a etapa anterior e é responsável pela próxima recebe como qualquer um."""
    a = _op(db_session, empresa, "ator")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Um", usuarios=[a.id]), _etapa("Dois", usuarios=[a.id])], usuarioResponsavelIds=[a.id])
    db_session.commit()
    ca = _client_para(app, a)
    assert ca.post(_url(demanda["id"], _por_ordem(demanda)[0]["id"], "concluir")).status_code == 200
    assert len(_da_etapa(ca, demanda["id"])) == 1


# ======================================================================================
# gatilho: quando NÃO notifica
# ======================================================================================


def test_proxima_sem_responsavel_nao_falha_e_nao_notifica_ninguem(app, db_session: Session, empresa: Empresa, client_admin: TestClient, client_gestor: TestClient) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Um"), _etapa("Sem responsável"), _etapa("Três")])
    resposta = _avancar(client_admin, demanda, 1)
    assert resposta.status_code == 200 and resposta.json()["etapaAtualId"] == _por_ordem(demanda)[1]["id"]  # o avanço segue
    assert _eventos(db_session, demanda["id"]) == []  # NO_RECIPIENT_BEHAVIOR: nenhum evento
    # admin/gestor NÃO recebem por padrão só porque a etapa não tem responsável
    assert _da_etapa(client_admin) == [] and _da_etapa(client_gestor) == []


def test_ultima_etapa_nao_gera_notificacao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "ult")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Primeira"), _etapa("Última", usuarios=[a.id])])
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200
    assert len(_eventos(db_session, demanda["id"])) == 1  # a da etapa 2
    assert _avancar(client_admin, demanda, 2).status_code == 200  # conclui o workflow
    assert len(_eventos(db_session, demanda["id"])) == 1  # nada novo
    assert len(_da_etapa(_client_para(app, a))) == 1


def test_409_e_recusas_nao_geram_notificacao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "rec")
    alheio = _op(db_session, empresa, "alheio")
    demanda = _demanda_com_workflow(
        client_admin, [_etapa("Um", usuarios=[a.id]), _etapa("Dois", "aprovacao", usuarios=[a.id]), _etapa("Três", usuarios=[a.id])], usuarioResponsavelIds=[a.id, alheio.id]
    )
    db_session.commit()
    e1, e2, e3 = _por_ordem(demanda)
    assert client_admin.post(_url(demanda["id"], e3["id"], "concluir")).status_code == 409  # saltar
    assert client_admin.post(_url(demanda["id"], e1["id"], "aprovar")).status_code == 422  # ação errada
    assert _client_para(app, alheio).post(_url(demanda["id"], e1["id"], "concluir")).status_code == 403  # sem autoridade
    assert _eventos(db_session, demanda["id"]) == []
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 200
    assert client_admin.post(_url(demanda["id"], e1["id"], "concluir")).status_code == 409  # retry
    assert len(_eventos(db_session, demanda["id"])) == 1  # só o vencedor
    assert len(_da_etapa(_client_para(app, a))) == 1


# ======================================================================================
# central: lida, contador, timeline, visibilidade
# ======================================================================================


def test_lida_e_contador_sao_por_usuario(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a, b = _op(db_session, empresa, "l1"), _op(db_session, empresa, "l2")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Um"), _etapa("Dois", usuarios=[a.id, b.id])])
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200
    ca, cb = _client_para(app, a), _client_para(app, b)
    assert _resumo(ca)["total"] == 1 and _resumo(cb)["total"] == 1
    (n,) = _da_etapa(ca)
    assert ca.post(f"/notificacoes/{n['id']}/lida").status_code in (200, 204)
    assert _resumo(ca)["total"] == 0 and _resumo(cb)["total"] == 1  # o outro destinatário segue com a dele
    assert _da_etapa(ca)[0]["lida"] is True and _da_etapa(cb)[0]["lida"] is False
    # quem não é destinatário não consegue marcar a notificação alheia
    assert _client_para(app, _op(db_session, empresa, "intruso")).post(f"/notificacoes/{n['id']}/lida").status_code == 404


def test_o_evento_nao_aparece_na_timeline_mas_a_transicao_sim(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "tl")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Um"), _etapa("Dois", usuarios=[a.id])])
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200
    tipos = [h["tipo"] for h in client_admin.get(f"/demandas/{demanda['id']}/historico").json()]
    assert "demanda.workflow_etapa_concluida" in tipos  # a transição (com a próxima no payload)
    assert TIPO not in tipos  # sem duplicar nem expor destinatários na timeline


def test_payload_minimo_sem_email(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _op(db_session, empresa, "pl")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Um"), _etapa("Dois", "aprovacao", usuarios=[a.id])])
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200
    (evento,) = _eventos(db_session, demanda["id"])
    etapa2 = _por_ordem(demanda)[1]
    assert evento.payload["workflowEtapaId"] == etapa2["id"] and evento.payload["etapaNome"] == "Dois"
    assert evento.payload["etapaOrdem"] == 2 and evento.payload["etapaTipo"] == "aprovacao"
    assert evento.payload["demanda_id"] == demanda["id"] and evento.entidade_id == demanda["id"] and evento.entidade_tipo == "demanda"
    assert "@" not in str(evento.payload)


def test_notificacao_e_acionavel_sem_conceder_edicao_geral(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    """Fase 8C.1: quem é responsável só pela ETAPA atual abre a demanda (escopo derivado do Workflow) e age nela, sem edição geral e sem Pauta."""
    a = _op(db_session, empresa, "vis")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Um"), _etapa("Dois", usuarios=[a.id])])  # `a` não é responsável pela demanda
    db_session.commit()
    assert _avancar(client_admin, demanda, 1).status_code == 200
    ca = _client_para(app, a)
    assert len(_da_etapa(ca, demanda["id"])) == 1
    detalhe = ca.get(f"/demandas/{demanda['id']}")
    assert detalhe.status_code == 200 and detalhe.json()["acessoApenasWorkflow"] is True  # o clique funciona
    assert ca.patch(f"/demandas/{demanda['id']}", json={"nome": "x"}).status_code == 404  # sem edição geral
    assert ca.get(f"/demandas/{demanda['id']}", params={"escopo": "pauta"}).status_code == 403  # nem a Pauta global é aberta por notificação


def test_tipos_antigos_continuam_filtrados_pela_regra_de_responsavel(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    """A central existente segue igual: status alterado só chega a quem é responsável da DEMANDA."""
    resp, outro = _op(db_session, empresa, "r"), _op(db_session, empresa, "o")
    demanda = client_admin.post("/demandas", json={"nome": "Normal", "usuarioResponsavelIds": [resp.id]}).json()
    db_session.commit()
    assert client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "planejada"}).status_code == 200
    assert any(n["tipo"] == "demanda.status_alterado" for n in _central(_client_para(app, resp)))
    assert _central(_client_para(app, outro)) == []


# ======================================================================================
# concorrência real
# ======================================================================================


@pytest.fixture()
def cenario_8c(test_engine):
    """Dados REAIS (commit): empresa, gestor, destinatário e demanda com 3 etapas (a 2ª tem responsável) — removidos no fim."""
    Fabrica = sessionmaker(bind=test_engine)
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(timezone.utc)
    with Fabrica() as db:
        empresa = Empresa(id=str(uuid.uuid4()), nome="Empresa 8C", codigo_interno=f"C8-{sufixo}".upper(), status="ativa", created_at=agora, updated_at=agora)
        db.add(empresa)
        db.flush()

        def usuario(perfil: str, nome: str) -> Usuario:
            u = Usuario(
                id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"{nome}-{sufixo}", nome=nome, email=f"{nome}-{sufixo}@teste.taskfloww.local",
                perfil_base=perfil, acesso_sistema=True, status="ativo", created_at=agora, updated_at=agora,
            )
            db.add(u)
            db.flush()
            return u

        gestor, destinatario = usuario("gestor", "gestor8c"), usuario("operador", "dest8c")
        demanda = Demanda(
            id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"T26{sufixo[:6]}", ano_referencia=26, sequencial_referencia=1,
            numero_operacional=1, identificador="#1", nome="Concorrência 8C", status="planejada", prioridade="media", sinalizada=False,
            created_at=agora, updated_at=agora,
        )
        db.add(demanda)
        db.flush()
        etapas = [
            DemandaWorkflowEtapa(
                id=str(uuid.uuid4()), demanda_id=demanda.id, ordem=i, nome=f"Etapa {i}", tipo="execucao", quantidade_antes_deadline=1,
                unidade_prazo="dias_corridos", status="pendente", iniciada_em=agora if i == 1 else None, created_at=agora, updated_at=agora,
            )
            for i in (1, 2, 3)
        ]
        db.add_all(etapas)
        db.flush()
        db.add(DemandaWorkflowEtapaResponsavel(demanda_workflow_etapa_id=etapas[1].id, usuario_id=destinatario.id, created_at=agora))
        db.commit()
        ids = {"empresa": empresa.id, "gestor": gestor.id, "destinatario": destinatario.id, "demanda": demanda.id, "etapas": [e.id for e in etapas]}
    try:
        yield Fabrica, ids
    finally:
        with Fabrica() as db:
            db.query(Evento).filter(Evento.entidade_id == ids["demanda"]).delete()
            db.query(Demanda).filter(Demanda.id == ids["demanda"]).delete()
            db.query(Usuario).filter(Usuario.empresa_id == ids["empresa"]).delete()
            db.query(Empresa).filter(Empresa.id == ids["empresa"]).delete()
            db.commit()


def test_concorrencia_real_gera_um_unico_conjunto_de_notificacoes(cenario_8c) -> None:
    from app.services.demanda_workflow_service import DemandaWorkflowConflitoError, DemandaWorkflowService

    Fabrica, ids = cenario_8c
    barreira = threading.Barrier(5)
    resultados: list[str] = []
    trava = threading.Lock()

    def tentar() -> None:
        with Fabrica() as db:
            ator = db.get(Usuario, ids["gestor"])
            demanda = db.get(Demanda, ids["demanda"])
            barreira.wait(timeout=10)
            try:
                DemandaWorkflowService().concluir_etapa(db, demanda, etapa_id=ids["etapas"][0], actor=ator)
                saida = "ok"
            except DemandaWorkflowConflitoError:
                saida = "conflito"
            with trava:
                resultados.append(saida)

    threads = [threading.Thread(target=tentar) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert sorted(resultados) == ["conflito"] * 4 + ["ok"], resultados

    with Fabrica() as db:
        eventos = list(db.scalars(select(Evento).where(Evento.entidade_id == ids["demanda"], Evento.tipo == TIPO)).all())
        assert len(eventos) == 1  # UM conjunto de notificações
        assert eventos[0].payload["destinatarioUsuarioIds"] == [ids["destinatario"]]
        assert db.scalar(select(func.count()).select_from(Evento).where(Evento.entidade_id == ids["demanda"], Evento.tipo == "demanda.workflow_etapa_concluida")) == 1
