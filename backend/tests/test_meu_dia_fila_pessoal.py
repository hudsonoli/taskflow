"""Fase 7B — Meu Dia: a fila operacional PESSOAL (`GET /demandas?escopo=meus&naoFinalizada=true&sort=fila_pessoal`).

Garantias:
- universo = demandas em que o usuário do TOKEN é responsável e que ainda não terminaram — NUNCA criadas por ele, carteira de clientes,
  departamento, Head, Atendimento ou Gestor (a autoridade maior não amplia a fila pessoal);
- ninguém troca o usuário do Meu Dia: o servidor deriva o usuário do token; um `responsavelId` alheio só estreita (resulta vazio);
- ordem: sessão ativa do próprio usuário > atrasadas > vencem hoje > prazo futuro > sem prazo; "em execução" vem da SESSÃO real,
  não do status; tudo no SQL antes de limit/offset (paginação mantém o escopo pessoal);
- `GET /sessoes-trabalho/minhas-ativas` devolve só ids de demanda do próprio usuário, sem tempo.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _atendimento, _client_para, _head_por_responsavel, _operador_comum
from tests.test_demanda import _criar, _departamento
from tests.test_trafego_carga import _sessao

AGORA = datetime.now(timezone.utc)
FRONTEIRAS = {
    "agora": AGORA.isoformat(),
    "hojeInicio": (AGORA - timedelta(hours=6)).isoformat(),
    "hojeFim": (AGORA + timedelta(hours=6)).isoformat(),
}


def _fila(client: TestClient, **extra) -> list[dict]:
    params = {"escopo": "meus", "naoFinalizada": "true", "sort": "fila_pessoal", "limit": 200, **FRONTEIRAS, **extra}
    resposta = client.get("/demandas", params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _ids(itens: list[dict]) -> list[str]:
    return [item["id"] for item in itens]


def _prazo(delta: timedelta | None) -> dict:
    return {} if delta is None else {"prazoEtapaAtual": (AGORA + delta).isoformat()}


def _definir_status(db: Session, demanda: dict, status: str) -> None:
    db.get(Demanda, demanda["id"]).status = status
    db.commit()


# ======================================================================================
# UNIVERSO — só o que está designado para MIM e ainda não terminou
# ======================================================================================


def test_mostra_fila_do_joao_e_nao_mostra_concluida_cancelada_arquivada_nem_de_outra_pessoa(app, db_session, empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-joao")
    maria = _operador_comum(db_session, empresa, sufixo="md-maria")
    db_session.commit()
    resp = lambda *u: {"usuarioResponsavelIds": [x.id for x in u]}  # noqa: E731
    a = _criar(client_admin, **resp(joao))  # planejada (padrão)
    b = _criar(client_admin, **resp(joao))
    c = _criar(client_admin, **resp(joao))
    d = _criar(client_admin, **resp(joao))
    e = _criar(client_admin, **resp(joao))
    f = _criar(client_admin, **resp(joao))
    cancelada = _criar(client_admin, **resp(joao))
    arquivada = _criar(client_admin, **resp(joao))
    g = _criar(client_admin, **resp(maria))
    for demanda, status in ((b, "em_execucao"), (c, "pausada"), (d, "aguardando_cliente"), (e, "bloqueada"), (f, "concluida"), (cancelada, "cancelada"), (arquivada, "arquivada")):
        _definir_status(db_session, demanda, status)

    fila = set(_ids(_fila(_client_para(app, joao))))
    assert fila == {a["id"], b["id"], c["id"], d["id"], e["id"]}  # fila, em execução, pausada, aguardando cliente, bloqueada
    assert not ({f["id"], cancelada["id"], arquivada["id"], g["id"]} & fila)


def test_demanda_atribuida_a_varios_aparece_para_cada_responsavel(app, db_session, empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-multi-j")
    maria = _operador_comum(db_session, empresa, sufixo="md-multi-m")
    db_session.commit()
    compartilhada = _criar(client_admin, usuarioResponsavelIds=[joao.id, maria.id])
    assert compartilhada["id"] in _ids(_fila(_client_para(app, joao)))
    assert compartilhada["id"] in _ids(_fila(_client_para(app, maria)))


# ======================================================================================
# PERFIL NÃO AMPLIA — Head, Gestor e Atendimento continuam com a fila PESSOAL
# ======================================================================================


def test_head_continua_pessoal_nao_ve_o_departamento(app, db_session, empresa, client_admin) -> None:
    head = _operador_comum(db_session, empresa, sufixo="md-head")
    departamento = _head_por_responsavel(db_session, empresa, head)
    outro = _operador_comum(db_session, empresa, sufixo="md-head-outro")
    db_session.commit()
    minha = _criar(client_admin, usuarioResponsavelIds=[head.id], departamentoResponsavelIds=[departamento.id])
    do_depto = _criar(client_admin, usuarioResponsavelIds=[outro.id], departamentoResponsavelIds=[departamento.id])
    cliente = _client_para(app, head)
    assert do_depto["id"] in {item["id"] for item in cliente.get("/demandas").json()}  # o escopo-base enxerga o departamento...
    assert _ids(_fila(cliente)) == [minha["id"]]  # ...mas o Meu Dia é só o que está designado para ele


def test_gestor_continua_pessoal_mesmo_com_visao_total(app, db_session, empresa, client_admin) -> None:
    gestor = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="gestor", email_prefixo="md-gestor")
    outro = _operador_comum(db_session, empresa, sufixo="md-gestor-outro")
    db_session.commit()
    minha = _criar(client_admin, usuarioResponsavelIds=[gestor.id])
    alheia = _criar(client_admin, usuarioResponsavelIds=[outro.id])
    cliente = _client_para(app, gestor)
    assert alheia["id"] in {item["id"] for item in cliente.get("/demandas", params={"limit": 200}).json()}  # vê tudo na visão normal
    assert _ids(_fila(cliente)) == [minha["id"]]


def test_atendimento_nao_recebe_no_meu_dia_o_que_criou_nem_a_carteira(app, db_session, empresa, client_admin) -> None:
    atendente = _operador_comum(db_session, empresa, sufixo="md-atend")
    _atendimento(db_session, empresa, atendente)
    outro = _operador_comum(db_session, empresa, sufixo="md-atend-outro")
    destino = _departamento(db_session, empresa, nome="Criação")
    db_session.commit()
    cliente = _client_para(app, atendente)
    criada_para_outro = cliente.post(
        "/demandas", json={"nome": "criada pelo atendimento", "usuarioResponsavelIds": [outro.id], "departamentoResponsavelIds": [destino.id]}
    ).json()
    minha = _criar(client_admin, usuarioResponsavelIds=[atendente.id])
    # a visão normal do Atendimento inclui o que ele criou...
    assert criada_para_outro["id"] in {item["id"] for item in cliente.get("/demandas").json()}
    # ...mas o Meu Dia não: é só o que está designado para ele
    assert _ids(_fila(cliente)) == [minha["id"]]


def test_quem_nao_tem_nada_designado_recebe_fila_vazia(app, db_session, empresa, client_admin) -> None:
    sozinho = _operador_comum(db_session, empresa, sufixo="md-vazio")
    db_session.commit()
    _criar(client_admin)
    assert _fila(_client_para(app, sozinho)) == []


# ======================================================================================
# SEGURANÇA — ninguém troca o usuário do Meu Dia
# ======================================================================================


def test_usuario_nao_consegue_trocar_o_dia_para_outra_pessoa(app, db_session, empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-troca-j")
    maria = _operador_comum(db_session, empresa, sufixo="md-troca-m")
    db_session.commit()
    da_maria = _criar(client_admin, usuarioResponsavelIds=[maria.id])
    da_joao = _criar(client_admin, usuarioResponsavelIds=[joao.id])
    cliente = _client_para(app, joao)
    assert _fila(cliente, responsavelId=maria.id) == []  # só ESTREITA dentro do escopo pessoal: nunca vira o dia da Maria
    assert da_maria["id"] not in _ids(_fila(cliente, responsavelId=maria.id, usuarioId=maria.id, usuarioResponsavelId=maria.id))
    assert _ids(_fila(cliente)) == [da_joao["id"]]


def test_empresa_vem_do_token_outro_tenant_nao_aparece(app, db_session, empresa, outra_empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-tenant")
    db_session.commit()
    mina = _criar(client_admin, usuarioResponsavelIds=[joao.id])
    assert _ids(_fila(_client_para(app, joao))) == [mina["id"]]


# ======================================================================================
# ORDEM — sessão ativa real, atrasadas, hoje, futuro, sem prazo
# ======================================================================================


def test_ordem_operacional_da_fila(app, db_session, empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-ordem")
    db_session.commit()
    mk = lambda **extra: _criar(client_admin, usuarioResponsavelIds=[joao.id], **extra)  # noqa: E731
    sem_prazo = mk()
    futuro_longe = mk(**_prazo(timedelta(days=9)))
    futuro_perto = mk(**_prazo(timedelta(days=2)))
    hoje = mk(**_prazo(timedelta(hours=3)))
    atrasada_antiga = mk(**_prazo(timedelta(days=-3)))
    atrasada_recente = mk(**_prazo(timedelta(hours=-2)))
    com_sessao = mk(**_prazo(timedelta(days=30)))  # prazo distante, mas há sessão ATIVA do próprio João
    so_status = mk(**_prazo(timedelta(days=40)))
    _definir_status(db_session, so_status, "em_execucao")  # status "em execução" SEM sessão: não sobe para o topo
    _sessao(db_session, empresa, decorrido=600, usuario=joao, demanda_id=com_sessao["id"])
    db_session.commit()

    ordem = _ids(_fila(_client_para(app, joao)))
    assert ordem == [
        com_sessao["id"],  # 0 — sessão ativa real
        atrasada_antiga["id"],  # 1 — atrasadas, a mais antiga primeiro
        atrasada_recente["id"],
        hoje["id"],  # 2 — vence hoje
        futuro_perto["id"],  # 3 — prazo futuro mais próximo
        futuro_longe["id"],
        so_status["id"],  # status em_execucao sozinho não é "trabalhando agora": segue o prazo (mais distante)
        sem_prazo["id"],  # 4 — sem prazo
    ]


def test_sessao_ativa_de_outra_pessoa_ou_encerrada_nao_destaca(app, db_session, empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-sess-j")
    maria = _operador_comum(db_session, empresa, sufixo="md-sess-m")
    db_session.commit()
    mk = lambda **extra: _criar(client_admin, usuarioResponsavelIds=[joao.id], **extra)  # noqa: E731
    perto = mk(**_prazo(timedelta(days=1)))
    longe_da_maria = mk(**_prazo(timedelta(days=20)))
    longe_encerrada = mk(**_prazo(timedelta(days=25)))
    _sessao(db_session, empresa, decorrido=100, usuario=maria, demanda_id=longe_da_maria["id"])  # sessão ativa, mas da Maria
    _sessao(db_session, empresa, status="encerrada", usuario=joao, demanda_id=longe_encerrada["id"])
    db_session.commit()
    assert _ids(_fila(_client_para(app, joao))) == [perto["id"], longe_da_maria["id"], longe_encerrada["id"]]


def test_prioridade_e_criterio_secundario_dentro_do_mesmo_prazo(app, db_session, empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-prio")
    db_session.commit()
    mesmo_prazo = (AGORA + timedelta(days=3)).isoformat()
    mk = lambda prioridade: _criar(client_admin, usuarioResponsavelIds=[joao.id], prioridade=prioridade, prazoEtapaAtual=mesmo_prazo)  # noqa: E731
    baixa, media, alta = mk("baixa"), mk("media"), mk("alta")
    assert _ids(_fila(_client_para(app, joao))) == [alta["id"], media["id"], baixa["id"]]


def test_sinalizada_vem_primeiro_dentro_da_mesma_faixa(app, db_session, empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-sinal")
    db_session.commit()
    normal = _criar(client_admin, usuarioResponsavelIds=[joao.id], **_prazo(timedelta(days=2)))
    sinalizada = _criar(client_admin, usuarioResponsavelIds=[joao.id], sinalizada=True, **_prazo(timedelta(days=5)))
    assert _ids(_fila(_client_para(app, joao))) == [sinalizada["id"], normal["id"]]


@pytest.mark.parametrize("faltando", ["agora", "hojeInicio", "hojeFim"])
def test_fila_pessoal_exige_as_fronteiras_do_dia(app, db_session, empresa, faltando) -> None:
    joao = _operador_comum(db_session, empresa, sufixo=f"md-422-{faltando}")
    db_session.commit()
    params = {"escopo": "meus", "sort": "fila_pessoal", **{k: v for k, v in FRONTEIRAS.items() if k != faltando}}
    assert _client_para(app, joao).get("/demandas", params=params).status_code == 422


def test_fronteira_sem_fuso_e_422(app, db_session, empresa) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-422-naive")
    db_session.commit()
    params = {"escopo": "meus", "sort": "fila_pessoal", **{**FRONTEIRAS, "agora": "2026-10-15T16:30:00"}}
    assert _client_para(app, joao).get("/demandas", params=params).status_code == 422


# ======================================================================================
# PAGINAÇÃO — mesmo escopo pessoal em todas as páginas (> 50)
# ======================================================================================


def test_paginacao_acima_de_50_mantem_escopo_ordem_e_sem_duplicata(app, db_session, empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-pag-j")
    maria = _operador_comum(db_session, empresa, sufixo="md-pag-m")
    db_session.commit()
    dele = [_criar(client_admin, usuarioResponsavelIds=[joao.id], **_prazo(timedelta(hours=i + 1))) for i in range(55)]
    da_maria = [_criar(client_admin, usuarioResponsavelIds=[maria.id]) for _ in range(3)]  # visíveis ao admin, nunca na fila do João
    cliente = _client_para(app, joao)

    pagina1 = _fila(cliente, limit=50, offset=0)
    pagina2 = _fila(cliente, limit=50, offset=50)
    assert len(pagina1) == 50 and len(pagina2) == 5
    todos = _ids(pagina1) + _ids(pagina2)
    assert len(set(todos)) == 55  # sem repetição entre páginas
    assert set(todos) == {d["id"] for d in dele}  # e nenhuma da Maria
    assert not ({d["id"] for d in da_maria} & set(todos))
    assert todos == [d["id"] for d in dele]  # mesma ordem em qualquer página (prazo mais próximo primeiro)


# ======================================================================================
# SESSÃO ATIVA — endpoint pessoal
# ======================================================================================


def test_minhas_ativas_devolve_so_as_demandas_do_proprio_usuario_sem_tempo(app, db_session, empresa, client_admin) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-ativas-j")
    maria = _operador_comum(db_session, empresa, sufixo="md-ativas-m")
    db_session.commit()
    d1, d2 = _criar(client_admin, usuarioResponsavelIds=[joao.id]), _criar(client_admin, usuarioResponsavelIds=[joao.id])
    _sessao(db_session, empresa, decorrido=500, usuario=joao, demanda_id=d1["id"])
    _sessao(db_session, empresa, decorrido=500, usuario=maria, demanda_id=d2["id"])  # sessão da Maria
    _sessao(db_session, empresa, status="encerrada", usuario=joao, demanda_id=d2["id"])
    db_session.commit()

    resposta = _client_para(app, joao).get("/sessoes-trabalho/minhas-ativas")
    assert resposta.status_code == 200
    assert resposta.json() == {"demandaIds": [d1["id"]]}  # só ids: nenhum tempo/duração exposto


def test_minhas_ativas_exige_login_e_nao_aceita_outro_usuario(app, db_session, empresa) -> None:
    joao = _operador_comum(db_session, empresa, sufixo="md-ativas-auth")
    db_session.commit()
    assert TestClient(app).get("/sessoes-trabalho/minhas-ativas").status_code == 401
    # parâmetro de usuário é ignorado: não existe caminho para consultar a sessão de outra pessoa
    resposta = _client_para(app, joao).get("/sessoes-trabalho/minhas-ativas", params={"usuarioId": str(uuid.uuid4())})
    assert resposta.status_code == 200 and resposta.json() == {"demandaIds": []}
