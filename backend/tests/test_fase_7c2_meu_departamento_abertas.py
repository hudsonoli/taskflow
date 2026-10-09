"""Fase 7C.2 — Meu Departamento abre na operação EM ABERTO (concluída/cancelada só por filtro explícito de Status).

- sem `status`: só demandas não finalizadas do departamento liderado (planejada, em execução, pausada, aguardando… e sem prazo/atrasada);
- `status=concluida` / `cancelada`: o Head continua consultando o que terminou, sempre do próprio departamento;
- aplicado no servidor ANTES de limit/offset; filtro nunca amplia o escopo (outro departamento jamais aparece).
"""

from __future__ import annotations

import pytest

from app.models.demanda import Demanda
from tests.test_demanda import _criar
from tests.test_fase_7c_visoes_lideranca import _cenario, _client_para, _ids, _lista

MD = "meu-departamento"


def _status(db, demanda: dict, status: str) -> None:
    db.get(Demanda, demanda["id"]).status = status
    db.commit()


def _head_com_estados(app, db, empresa, client_admin):
    """Criação (do cenário) ganha: 2 planejadas, 1 em execução, 1 pausada, 1 aguardando cliente, 1 concluída, 1 cancelada, 1 arquivada.
    Outro departamento (Digital) também tem uma concluída e uma aberta."""
    c = _cenario(app, db, empresa, client_admin)
    # o cenário traz 8 demandas de Criação "planejada"; aqui trabalhamos só com as novas, identificadas por id
    criacao = c["criacao"].id
    novas = {nome: _criar(client_admin, departamentoResponsavelIds=[criacao]) for nome in
             ("planejada1", "planejada2", "execucao", "pausada", "aguardando", "concluida", "cancelada", "arquivada")}
    for nome, status in (("execucao", "em_execucao"), ("pausada", "pausada"), ("aguardando", "aguardando_cliente"),
                         ("concluida", "concluida"), ("cancelada", "cancelada"), ("arquivada", "arquivada")):
        _status(db, novas[nome], status)
    digital_concluida = _criar(client_admin, departamentoResponsavelIds=[c["outros"]["Digital"].id])
    _status(db, digital_concluida, "concluida")
    return c, novas, digital_concluida


def test_padrao_mostra_somente_abertas_de_criacao(app, db_session, empresa, client_admin) -> None:
    c, novas, digital_concluida = _head_com_estados(app, db_session, empresa, client_admin)
    ids = _ids(_lista(_client_para(app, c["maria"]), MD))
    abertas = {novas[n]["id"] for n in ("planejada1", "planejada2", "execucao", "pausada", "aguardando")}
    assert abertas <= ids
    for nome in ("concluida", "cancelada", "arquivada"):
        assert novas[nome]["id"] not in ids, nome
    assert digital_concluida["id"] not in ids
    # tudo que veio é de Criação e aberto: as 8 do cenário (todas planejadas) + as 5 abertas novas
    assert len(ids) == 8 + 5
    assert ids <= _ids(c["criacao_todas"]) | abertas


def test_sem_prazo_e_atrasada_continuam_na_lista_padrao(app, db_session, empresa, client_admin) -> None:
    c = _cenario(app, db_session, empresa, client_admin)
    sem_prazo = _criar(client_admin, departamentoResponsavelIds=[c["criacao"].id])
    assert sem_prazo["prazoEtapaAtual"] is None
    atrasada = _criar(client_admin, departamentoResponsavelIds=[c["criacao"].id], prazoEtapaAtual="2020-01-01T10:00:00Z")
    ids = _ids(_lista(_client_para(app, c["maria"]), MD))
    assert {sem_prazo["id"], atrasada["id"]} <= ids


def test_status_concluida_explicito_consulta_as_concluidas_do_departamento(app, db_session, empresa, client_admin) -> None:
    c, novas, digital_concluida = _head_com_estados(app, db_session, empresa, client_admin)
    maria = _client_para(app, c["maria"])
    assert _ids(_lista(maria, MD, status="concluida")) == {novas["concluida"]["id"]}  # nunca a de Digital


def test_status_cancelada_explicito_retorna_somente_a_cancelada_do_departamento(app, db_session, empresa, client_admin) -> None:
    c, novas, _ = _head_com_estados(app, db_session, empresa, client_admin)
    assert _ids(_lista(_client_para(app, c["maria"]), MD, status="cancelada")) == {novas["cancelada"]["id"]}


def test_status_explicito_de_aberto_e_multivalor_respeitam_o_pedido(app, db_session, empresa, client_admin) -> None:
    c, novas, _ = _head_com_estados(app, db_session, empresa, client_admin)
    maria = _client_para(app, c["maria"])
    assert _ids(_lista(maria, MD, status="em_execucao")) == {novas["execucao"]["id"]}
    assert _ids(_lista(maria, MD, status="concluida,cancelada")) == {novas["concluida"]["id"], novas["cancelada"]["id"]}


def test_filtros_combinam_com_o_padrao_aberto(app, db_session, empresa, client_admin) -> None:
    c, novas, _ = _head_com_estados(app, db_session, empresa, client_admin)
    maria = _client_para(app, c["maria"])
    # prioridade/outros filtros refinam a lista aberta; a concluída continua fora sem status explícito
    todas = _ids(_lista(maria, MD, prioridade="media,alta,baixa"))
    assert novas["concluida"]["id"] not in todas and novas["execucao"]["id"] in todas
    assert _ids(_lista(maria, MD, statusExcluir="em_execucao")) & {novas["execucao"]["id"]} == set()
    assert novas["concluida"]["id"] not in _ids(_lista(maria, MD, statusExcluir="em_execucao"))


@pytest.mark.parametrize("status", [None, "concluida", "cancelada"])
def test_nunca_retorna_outro_departamento(app, db_session, empresa, client_admin, status) -> None:
    c, novas, digital_concluida = _head_com_estados(app, db_session, empresa, client_admin)
    extra = {"status": status} if status else {}
    ids = _ids(_lista(_client_para(app, c["maria"]), MD, **extra))
    fora = {d["id"] for d in c["social"] + c["digital"] + c["redacao"] + c["midia"]}
    assert not (ids & (fora | {digital_concluida["id"]}))
    # `departamentoId` de outro setor não amplia: o servidor continua no departamento liderado
    outro = c["outros"]["Digital"].id
    assert not (_ids(_lista(_client_para(app, c["maria"]), MD, departamentoId=outro, **extra)) & (fora | {digital_concluida["id"]}))


def test_padrao_aberto_vale_antes_da_paginacao(app, db_session, empresa, client_admin) -> None:
    c, novas, _ = _head_com_estados(app, db_session, empresa, client_admin)
    maria = _client_para(app, c["maria"])
    total = len(_lista(maria, MD))
    paginas, vistos = [], set()
    for offset in range(0, total + 5, 4):
        pagina = _lista(maria, MD, limit=4, offset=offset)
        paginas.append(len(pagina))
        vistos |= _ids(pagina)
    assert len(vistos) == total == 13  # mesmo universo em todas as páginas: nenhuma finalizada "vaza" no carregamento seguinte
    assert not (vistos & {novas[n]["id"] for n in ("concluida", "cancelada", "arquivada")})
    assert paginas[:3] == [4, 4, 4]  # páginas cheias: o filtro não deixou buracos (filtrou antes de limit/offset)


def test_head_ainda_exigido_e_pauta_e_meu_dia_nao_mudaram(app, db_session, empresa, client_admin) -> None:
    c, novas, digital_concluida = _head_com_estados(app, db_session, empresa, client_admin)
    assert _client_para(app, c["joao"]).get("/demandas", params={"escopo": MD}).status_code == 403  # operador comum
    assert _client_para(app, c["ana"]).get("/demandas", params={"escopo": MD}).status_code == 403
    # Pauta: empresa toda, abertas (já era assim); concluída só some, não é um efeito novo
    pauta = _ids(_lista(_client_para(app, c["ana"]), "pauta"))
    assert novas["execucao"]["id"] in pauta and novas["concluida"]["id"] not in pauta
    # Meu Dia: só o atribuído (a concluída/qualquer outra não entra)
    meu_dia = _ids(_lista(_client_para(app, c["maria"]), "meus"))
    assert meu_dia == _ids(c["da_maria"])
    # outras listagens sem escopo (Tarefas) continuam devolvendo finalizadas quando pedidas: o padrão aberto é só do Meu Departamento
    assert novas["concluida"]["id"] in _ids(client_admin.get("/demandas", params={"limit": 200}).json())
