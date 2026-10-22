"""`GET /demandas?sort=operacional` — ordem operacional das Tarefas, decidida no SERVIDOR (a tela pagina por offset).

Não terminal primeiro (inclui rascunho/planejada), por prazo ASC com SEM prazo por último, desempate alta → média → baixa e número operacional; depois o bloco terminal
(concluída/cancelada/arquivada), mais recentemente atualizada primeiro. `prazo_asc` mantém a semântica literal (a Pauta depende dela).
"""

from __future__ import annotations

import itertools
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.empresa import Empresa
from tests.test_d1_criacao_demandas import _client_para

_numero = itertools.count(1000)
AGORA = datetime.now(timezone.utc)


def _demanda(db: Session, empresa: Empresa, nome: str, *, status: str = "em_execucao", prioridade: str = "media", prazo: timedelta | None = None, atualizada_ha: timedelta = timedelta(0), criado_por: str | None = None) -> Demanda:
    n = next(_numero)
    momento = AGORA - atualizada_ha
    demanda = Demanda(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"S26{n}", ano_referencia=26, sequencial_referencia=n, numero_operacional=n, identificador=f"#{n}",
        nome=nome, status=status, prioridade=prioridade, sinalizada=False, prazo_etapa_atual=None if prazo is None else AGORA + prazo,
        criado_por_usuario_id=criado_por, created_at=momento, updated_at=momento,
    )
    db.add(demanda)
    db.flush()
    return demanda


def _nomes(client: TestClient, **params) -> list[str]:
    resposta = client.get("/demandas", params={"sort": "operacional", "limit": 200, **params})
    assert resposta.status_code == 200, resposta.text
    return [d["nome"] for d in resposta.json()]


def test_ordem_operacional_ativas_por_prazo_prioridade_depois_sem_prazo_depois_terminais(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    dia = timedelta(days=1)
    _demanda(db_session, empresa, "G cancelada antiga", status="cancelada", prazo=-300 * dia, atualizada_ha=timedelta(days=5))
    _demanda(db_session, empresa, "E sem prazo alta", prioridade="alta")
    _demanda(db_session, empresa, "F concluída antiga", status="concluida", prazo=-400 * dia, atualizada_ha=timedelta(days=1))
    _demanda(db_session, empresa, "D amanhã alta", prioridade="alta", prazo=dia)
    _demanda(db_session, empresa, "C hoje média", prioridade="media", prazo=timedelta(hours=1))
    _demanda(db_session, empresa, "B ontem baixa", prioridade="baixa", prazo=-dia)
    _demanda(db_session, empresa, "A ontem alta", prioridade="alta", prazo=-dia)
    assert _nomes(client_admin) == [
        "A ontem alta", "B ontem baixa", "C hoje média", "D amanhã alta", "E sem prazo alta",  # ativas: prazo, prioridade, sem prazo por último
        "F concluída antiga", "G cancelada antiga",  # terminais: mais recentemente atualizada primeiro; o prazo de algo encerrado não ordena
    ]


def test_rascunho_e_planejada_participam_como_ativas(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    dia = timedelta(days=1)
    _demanda(db_session, empresa, "concluída", status="concluida", prazo=-10 * dia)
    _demanda(db_session, empresa, "rascunho longe", status="rascunho", prazo=20 * dia)
    _demanda(db_session, empresa, "planejada perto", status="planejada", prazo=2 * dia)
    _demanda(db_session, empresa, "bloqueada sem prazo", status="bloqueada")
    assert _nomes(client_admin) == ["planejada perto", "rascunho longe", "bloqueada sem prazo", "concluída"]


def test_mesmo_prazo_desempata_por_prioridade_e_depois_numero_desc(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    prazo = timedelta(days=3)
    baixa = _demanda(db_session, empresa, "baixa", prioridade="baixa", prazo=prazo)
    media_antiga = _demanda(db_session, empresa, "media antiga", prioridade="media", prazo=prazo)
    media_nova = _demanda(db_session, empresa, "media nova", prioridade="media", prazo=prazo)
    alta = _demanda(db_session, empresa, "alta", prioridade="alta", prazo=prazo)
    # prazos idênticos (mesmo instante): a ordem só pode vir de prioridade e número
    for d in (baixa, media_antiga, media_nova, alta):
        d.prazo_etapa_atual = AGORA + prazo
    db_session.flush()
    assert _nomes(client_admin) == ["alta", "media nova", "media antiga", "baixa"]


def test_ativa_sem_prazo_vem_depois_das_com_prazo_mas_antes_dos_terminais(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    _demanda(db_session, empresa, "sem prazo", prioridade="alta")
    _demanda(db_session, empresa, "prazo distante", prioridade="baixa", prazo=timedelta(days=500))
    _demanda(db_session, empresa, "terminal", status="concluida", prazo=timedelta(days=1))
    assert _nomes(client_admin) == ["prazo distante", "sem prazo", "terminal"]


def test_paginacao_global_ativos_prioritarios_na_primeira_pagina(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    """Gate: 60 terminais com prazo vencido há meses + ativos atuais. Com a ordem pelo prazo "puro", os terminais dominariam a página 1 e os ativos iriam para a 2."""
    dia = timedelta(days=1)
    for i in range(60):
        _demanda(db_session, empresa, f"terminal {i:02d}", status="concluida" if i % 2 else "cancelada", prazo=-(100 + i) * dia, atualizada_ha=timedelta(minutes=i))
    ativos = [
        _demanda(db_session, empresa, "ativo atrasado", prioridade="alta", prazo=-dia),
        _demanda(db_session, empresa, "ativo hoje", prioridade="media", prazo=timedelta(hours=2)),
        _demanda(db_session, empresa, "ativo futuro", prioridade="baixa", prazo=7 * dia),
        _demanda(db_session, empresa, "ativo sem prazo", prioridade="alta"),
    ]
    pagina1 = client_admin.get("/demandas", params={"sort": "operacional", "limit": 50, "offset": 0}).json()
    nomes1 = [d["nome"] for d in pagina1]
    assert nomes1[:4] == ["ativo atrasado", "ativo hoje", "ativo futuro", "ativo sem prazo"]
    assert all(n.startswith("terminal") for n in nomes1[4:])
    pagina2 = client_admin.get("/demandas", params={"sort": "operacional", "limit": 50, "offset": 50}).json()
    todos = nomes1 + [d["nome"] for d in pagina2]
    assert len(todos) == len(set(todos)) == 64  # paginação estável: nenhuma repetição nem perda entre páginas
    assert len(ativos) == 4
    # contraste: o prazo_asc literal (contrato da Pauta) NÃO foi alterado e põe o terminal mais antigo primeiro
    literal = client_admin.get("/demandas", params={"sort": "prazo_asc", "limit": 5}).json()
    assert literal[0]["nome"].startswith("terminal")


def test_default_da_api_continua_numero_operacional_desc(db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    a = _demanda(db_session, empresa, "a", prazo=timedelta(days=9))
    b = _demanda(db_session, empresa, "b", prazo=timedelta(days=1))
    nomes = [d["nome"] for d in client_admin.get("/demandas", params={"limit": 200}).json()]
    assert nomes == ["b", "a"] and b.numero_operacional > a.numero_operacional  # sem sort: o contrato antigo (consumidores existentes)


def test_sort_desconhecido_e_422(client_admin: TestClient) -> None:
    assert client_admin.get("/demandas", params={"sort": "prazo_prioridade"}).status_code == 422


def test_ordem_compoe_com_filtros_e_escopo_solicitadas(app, db_session: Session, empresa: Empresa, client_admin: TestClient, usuario_operador) -> None:
    dia = timedelta(days=1)
    mine = [
        _demanda(db_session, empresa, "minha longe", prazo=9 * dia, criado_por=usuario_operador.id),
        _demanda(db_session, empresa, "minha perto", prazo=dia, criado_por=usuario_operador.id),
        _demanda(db_session, empresa, "minha concluída", status="concluida", prazo=-dia, criado_por=usuario_operador.id),
    ]
    _demanda(db_session, empresa, "de outro", prazo=dia // 2)
    cliente = _client_para(app, usuario_operador)
    assert _nomes(cliente, escopo="solicitadas") == ["minha perto", "minha longe", "minha concluída"]  # Solicitadas por mim usa a mesma ordem
    assert _nomes(client_admin, status="em_execucao") == ["de outro", "minha perto", "minha longe"]  # filtro de status compõe
    assert len(mine) == 3
    assert _nomes(client_admin, search="minha") == ["minha perto", "minha longe", "minha concluída"]  # busca compõe
