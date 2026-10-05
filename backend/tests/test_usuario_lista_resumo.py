"""GET /usuarios (paginação, busca, departamento, situação) e GET /usuarios/resumo.

Sustenta a tela de Usuários sem a janela fixa de 200: a listagem é paginada no servidor e os cards
vêm de agregados da empresa inteira (nunca da página nem dos filtros).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.usuario import Usuario


def _departamento(db: Session, empresa: Empresa, nome: str) -> Departamento:
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(timezone.utc)
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=nome,
        nome_normalizado=f"{nome.lower()}-{sufixo}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _usuario(
    db: Session,
    empresa: Empresa,
    *,
    nome: str | None = None,
    email: str | None = None,
    status: str = "ativo",
    perfil: str = "operador",
    departamento: Departamento | None = None,
    sistema: bool = False,
    criado_em: datetime | None = None,
) -> Usuario:
    agora = criado_em or datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:10]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"l-{sufixo}",
        nome=nome or f"Pessoa {sufixo}",
        email=email or f"l-{sufixo}@teste.local",
        perfil_base=perfil,
        acesso_sistema=True,
        status=status,
        departamento_id=departamento.id if departamento else None,
        is_system_account=sistema,
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _lista(client: TestClient, empresa: Empresa, **params):
    resposta = client.get("/usuarios", params={"empresaId": empresa.id, **params})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _ids(itens: list[dict]) -> set[str]:
    return {item["id"] for item in itens}


def _resumo(client: TestClient, empresa: Empresa) -> dict:
    resposta = client.get("/usuarios/resumo", params={"empresaId": empresa.id})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# --------------------------------------------------------------------------------------
# Autorização / tenant
# --------------------------------------------------------------------------------------


def test_resumo_mesma_autorizacao_da_listagem(
    client: TestClient,
    client_admin: TestClient,
    client_gestor: TestClient,
    client_operador: TestClient,
    empresa: Empresa,
    outra_empresa: Empresa,
) -> None:
    params = {"empresaId": empresa.id}
    assert client.get("/usuarios/resumo", params=params).status_code == 401
    assert client_operador.get("/usuarios/resumo", params=params).status_code == 403
    assert client_operador.get("/usuarios", params=params).status_code == 403
    assert client_admin.get("/usuarios/resumo", params=params).status_code == 200
    assert client_gestor.get("/usuarios/resumo", params=params).status_code == 200
    # Outra empresa na query: recusado, como em GET /usuarios.
    assert client_admin.get("/usuarios/resumo", params={"empresaId": outra_empresa.id}).status_code == 403
    assert client_admin.get("/usuarios", params={"empresaId": outra_empresa.id}).status_code == 403


def test_nada_de_outra_empresa_na_lista_nem_no_resumo(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    antes = _resumo(client_admin, empresa)
    alheio = _usuario(db_session, outra_empresa, nome="Alheio Cross Tenant")
    depto_alheio = _departamento(db_session, outra_empresa, "Departamento Alheio")
    _usuario(db_session, outra_empresa, perfil="gestor", departamento=depto_alheio)

    assert alheio.id not in _ids(_lista(client_admin, empresa, limit=200))
    assert _lista(client_admin, empresa, search="Alheio") == []
    assert _resumo(client_admin, empresa) == antes
    # Departamento de outra empresa como filtro: zero resultados, sem vazar nada.
    assert _lista(client_admin, empresa, departamentoId=depto_alheio.id) == []
    assert _lista(client_admin, empresa, search="Departamento Alheio") == []


# --------------------------------------------------------------------------------------
# >200: o bug antigo
# --------------------------------------------------------------------------------------


def test_mais_de_200_usuarios_paginacao_alcanca_todos_e_resumo_nao_para_em_200(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    base = datetime.now(timezone.utc) - timedelta(days=1)
    criados = [
        _usuario(db_session, empresa, nome=f"Zed Pessoa {indice:03d}", criado_em=base + timedelta(seconds=indice))
        for indice in range(1, 231)
    ]
    esperado = {usuario.id for usuario in criados}

    vistos: list[str] = []
    for pagina in range(10):
        itens = _lista(client_admin, empresa, limit=50, offset=pagina * 50)
        vistos.extend(item["id"] for item in itens)
        if len(itens) < 50:
            break
    assert len(vistos) == len(set(vistos)), "paginação repetiu linha"
    assert esperado <= set(vistos), "algum usuário ficou inalcançável"
    assert len(vistos) == 231  # 230 criados + o admin da fixture

    resumo = _resumo(client_admin, empresa)
    assert resumo["total"] == 231
    assert resumo["total"] > 200

    # O 230º criado (o mais antigo na ordem created_at desc) só aparece depois da posição 200.
    mais_antigo = criados[0]
    posicao = vistos.index(mais_antigo.id)
    assert posicao >= 200, posicao
    assert [i["id"] for i in _lista(client_admin, empresa, search="Zed Pessoa 001")] == [mais_antigo.id]


def test_paginacao_estavel_e_ordem_preservada(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    mesmo_instante = datetime.now(timezone.utc) - timedelta(hours=1)
    for _ in range(12):
        _usuario(db_session, empresa, nome="Homonimo Paginacao", criado_em=mesmo_instante)

    tudo = [item["id"] for item in _lista(client_admin, empresa, search="Homonimo Paginacao", limit=200)]
    paginado: list[str] = []
    for offset in range(0, 12, 5):
        paginado += [i["id"] for i in _lista(client_admin, empresa, search="Homonimo Paginacao", limit=5, offset=offset)]
    assert paginado == tudo and len(set(tudo)) == 12


def test_sem_parametros_novos_comportamento_antigo(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    arquivado = _usuario(db_session, empresa, status="arquivado")
    sistema = _usuario(db_session, empresa, sistema=True)
    ids = _ids(_lista(client_admin, empresa))
    assert arquivado.id not in ids and sistema.id not in ids
    assert _ids(_lista(client_admin, empresa, status="arquivado")) >= {arquivado.id}
    assert _lista(client_admin, empresa, limit=1) and len(_lista(client_admin, empresa, limit=1)) == 1


# --------------------------------------------------------------------------------------
# Situação (a regra exata da tela) e status
# --------------------------------------------------------------------------------------


def test_situacao_inativo_e_tudo_que_nao_e_ativo_exceto_arquivado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    por_status = {s: _usuario(db_session, empresa, status=s) for s in ("ativo", "inativo", "bloqueado", "arquivado")}

    ativos = _ids(_lista(client_admin, empresa, situacao="ativo", limit=200))
    assert por_status["ativo"].id in ativos
    assert not ({por_status[s].id for s in ("inativo", "bloqueado", "arquivado")} & ativos)

    inativos = _ids(_lista(client_admin, empresa, situacao="inativo", limit=200))
    # "Inativos" da tela = inativo + bloqueado (arquivado segue oculto, ativo nunca entra).
    assert {por_status["inativo"].id, por_status["bloqueado"].id} <= inativos
    assert por_status["ativo"].id not in inativos
    assert por_status["arquivado"].id not in inativos

    # `status` continua filtro exato e compatível: bloqueado NÃO entra em status=inativo.
    exato = _ids(_lista(client_admin, empresa, status="inativo", limit=200))
    assert por_status["inativo"].id in exato and por_status["bloqueado"].id not in exato

    # Arquivado só aparece pedindo explicitamente.
    assert por_status["arquivado"].id in _ids(_lista(client_admin, empresa, status="arquivado", limit=200))


def test_situacao_invalida_422(client_admin: TestClient, empresa: Empresa) -> None:
    resposta = client_admin.get("/usuarios", params={"empresaId": empresa.id, "situacao": "bloqueado"})
    assert resposta.status_code == 422


# --------------------------------------------------------------------------------------
# Departamento
# --------------------------------------------------------------------------------------


def test_filtro_por_departamento(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    dep_a, dep_b = _departamento(db_session, empresa, "Alfa"), _departamento(db_session, empresa, "Beta")
    a1, a2 = (_usuario(db_session, empresa, departamento=dep_a) for _ in range(2))
    b1 = _usuario(db_session, empresa, departamento=dep_b)
    sem = _usuario(db_session, empresa)

    assert _ids(_lista(client_admin, empresa, departamentoId=dep_a.id)) == {a1.id, a2.id}
    assert _ids(_lista(client_admin, empresa, departamentoId=dep_b.id)) == {b1.id}
    assert sem.id not in _ids(_lista(client_admin, empresa, departamentoId=dep_a.id))
    # Combina com situação e busca.
    a2.status = "inativo"
    db_session.flush()
    assert _ids(_lista(client_admin, empresa, departamentoId=dep_a.id, situacao="inativo")) == {a2.id}
    assert _ids(_lista(client_admin, empresa, departamentoId=dep_a.id, situacao="ativo")) == {a1.id}
    assert client_admin.get("/usuarios", params={"empresaId": empresa.id, "departamentoId": "x"}).status_code == 422


# --------------------------------------------------------------------------------------
# Busca (a da tela: nome, e-mail, departamento; sem acento; sem diferenciar maiúsculas)
# --------------------------------------------------------------------------------------


def test_busca_nome_email_codigo_e_departamento_sem_acento_e_sem_caixa(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    criacao = _departamento(db_session, empresa, "Criação")
    joao = _usuario(db_session, empresa, nome="João da Conceição", email="joao.unico@teste.local")
    na_criacao = _usuario(db_session, empresa, nome="Maria Sem Relacao", departamento=criacao)
    outro = _usuario(db_session, empresa, nome="Pedro Qualquer")

    assert _ids(_lista(client_admin, empresa, search="joao")) == {joao.id}
    assert _ids(_lista(client_admin, empresa, search="JOÃO")) == {joao.id}
    assert _ids(_lista(client_admin, empresa, search="conceicao")) == {joao.id}
    assert _ids(_lista(client_admin, empresa, search="JOAO.UNICO")) == {joao.id}  # e-mail
    assert _ids(_lista(client_admin, empresa, search=joao.codigo_interno)) == {joao.id}  # código interno
    # Nome do DEPARTAMENTO encontra quem está nele (sem acento / caixa).
    assert _ids(_lista(client_admin, empresa, search="criacao")) == {na_criacao.id}
    assert _ids(_lista(client_admin, empresa, search="CRIAÇÃO")) == {na_criacao.id}
    assert outro.id not in _ids(_lista(client_admin, empresa, search="criacao"))
    assert _lista(client_admin, empresa, search="   ") != []  # só espaços = sem busca


def test_busca_trata_curingas_como_texto(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    literal = _usuario(db_session, empresa, nome="Cem% Por_Cento")
    _usuario(db_session, empresa, nome="Cemx Porxcento")
    assert _ids(_lista(client_admin, empresa, search="cem% por_")) == {literal.id}
    assert _ids(_lista(client_admin, empresa, search="%")) == {literal.id}


# --------------------------------------------------------------------------------------
# Resumo (cards)
# --------------------------------------------------------------------------------------


def test_resumo_formulas_exatas(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    antes = _resumo(client_admin, empresa)  # só o admin da fixture: ativo, gestão, sem departamento
    assert antes == {"total": 1, "ativos": 1, "gestao": 1, "departamentos": 0}

    dep_a, dep_b = _departamento(db_session, empresa, "Resumo A"), _departamento(db_session, empresa, "Resumo B")
    _usuario(db_session, empresa, perfil="gestor", departamento=dep_a)  # ativo, gestão, A
    _usuario(db_session, empresa, perfil="operador", departamento=dep_a)  # ativo, A (A conta uma vez)
    _usuario(db_session, empresa, perfil="admin", status="inativo", departamento=dep_b)  # gestão, inativo, B
    _usuario(db_session, empresa, perfil="operador", status="bloqueado")  # não ativo, sem departamento
    # Fora da conta: arquivado e conta de sistema (não entram em NENHUM card).
    _usuario(db_session, empresa, perfil="admin", status="arquivado", departamento=_departamento(db_session, empresa, "Só Arquivado"))
    _usuario(db_session, empresa, perfil="admin", sistema=True)

    assert _resumo(client_admin, empresa) == {
        "total": 1 + 4,  # admin da fixture + os 4 contáveis acima (arquivado e sistema ficam de fora)
        "ativos": 1 + 2,
        "gestao": 1 + 2,  # gestor + admin inativo (perfil conta, status não)
        "departamentos": 2,  # A e B; "Só Arquivado" não conta
    }


def test_resumo_nao_depende_de_filtros_nem_de_pagina(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    for _ in range(60):
        _usuario(db_session, empresa)
    esperado = _resumo(client_admin, empresa)
    _lista(client_admin, empresa, limit=5, offset=10, situacao="inativo", search="zzzz")
    assert _resumo(client_admin, empresa) == esperado
    assert esperado["total"] == 61


# --------------------------------------------------------------------------------------
# SQL
# --------------------------------------------------------------------------------------


def _contar(client: TestClient, db_session: Session, caminho: str, params: dict) -> int:
    comandos: list[str] = []

    def _capturar(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _capturar)
    try:
        resposta = client.get(caminho, params=params)
    finally:
        event.remove(engine, "before_cursor_execute", _capturar)
    assert resposta.status_code == 200, resposta.text
    return len(comandos)


def test_query_count_constante_resumo_e_listagem(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa, "Contagem")
    for _ in range(3):
        _usuario(db_session, empresa, departamento=departamento)
    params = {"empresaId": empresa.id}

    resumo_pouco = _contar(client_admin, db_session, "/usuarios/resumo", params)
    lista_pouco = _contar(client_admin, db_session, "/usuarios", {**params, "limit": 200})
    busca_pouco = _contar(client_admin, db_session, "/usuarios", {**params, "limit": 200, "search": "contagem"})

    for _ in range(60):
        _usuario(db_session, empresa, departamento=departamento)

    assert _contar(client_admin, db_session, "/usuarios/resumo", params) == resumo_pouco
    assert _contar(client_admin, db_session, "/usuarios", {**params, "limit": 200}) == lista_pouco
    assert _contar(client_admin, db_session, "/usuarios", {**params, "limit": 200, "search": "contagem"}) == busca_pouco
