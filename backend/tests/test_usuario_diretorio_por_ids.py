"""GET /usuarios/diretorio/por-ids — resolução de nome/avatar por ids conhecidos, em lote.

Substitui a varredura paginada do diretório (200 em 200) feita pelo frontend para nomear
responsáveis fora da primeira página. Mesma autoridade e mesma projeção de `/usuarios/diretorio`:
não pode ampliar acesso a dados de usuário.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario

URL = "/usuarios/diretorio/por-ids"


def _usuario(
    db: Session,
    empresa: Empresa,
    *,
    nome: str | None = None,
    status: str = "ativo",
    is_system_account: bool = False,
) -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:10]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"p-{sufixo}",
        nome=nome or f"Pessoa {sufixo}",
        email=f"p-{sufixo}@teste.local",
        telefone="11999990000",
        perfil_base="operador",
        acesso_sistema=True,
        status=status,
        is_system_account=is_system_account,
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _consultar(client: TestClient, ids: list[str]):
    return client.get(URL, params={"ids": ",".join(ids)})


# --------------------------------------------------------------------------------------
# Autenticação / autoridade
# --------------------------------------------------------------------------------------


def test_sem_autenticacao_401(client: TestClient) -> None:
    assert client.get(URL, params={"ids": str(uuid.uuid4())}).status_code == 401


def test_operador_sem_usuarios_visualizar_resolve_normalmente(
    client_operador: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """O operador que edita Demandas não tem `usuarios.visualizar`: a mesma chamada que o
    `/usuarios/{id}` recusa precisa funcionar aqui, e só aqui."""
    alvo = _usuario(db_session, empresa)

    assert client_operador.get(f"/usuarios/{alvo.id}").status_code == 403
    resposta = _consultar(client_operador, [alvo.id])
    assert resposta.status_code == 200, resposta.text
    assert [item["id"] for item in resposta.json()] == [alvo.id]


def test_perfis_admin_e_gestor_tambem_resolvem(
    client_admin: TestClient, client_gestor: TestClient, db_session: Session, empresa: Empresa
) -> None:
    alvo = _usuario(db_session, empresa)
    for cliente in (client_admin, client_gestor):
        resposta = _consultar(cliente, [alvo.id])
        assert resposta.status_code == 200, resposta.text
        assert [item["id"] for item in resposta.json()] == [alvo.id]


# --------------------------------------------------------------------------------------
# Resolução
# --------------------------------------------------------------------------------------


def test_um_id_e_varios_ids(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    a, b, c = (_usuario(db_session, empresa) for _ in range(3))

    um = _consultar(client_admin, [a.id])
    assert um.status_code == 200, um.text
    assert [item["id"] for item in um.json()] == [a.id]
    assert um.json()[0]["nome"] == a.nome

    varios = _consultar(client_admin, [a.id, b.id, c.id])
    assert varios.status_code == 200, varios.text
    assert {item["id"] for item in varios.json()} == {a.id, b.id, c.id}


def test_ids_repetidos_sao_deduplicados(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    a = _usuario(db_session, empresa)
    resposta = _consultar(client_admin, [a.id, a.id, a.id.upper(), f" {a.id} "])
    assert resposta.status_code == 200, resposta.text
    assert [item["id"] for item in resposta.json()] == [a.id]


def test_todos_os_status_sao_resolvidos(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    """Responsável já vinculado pode estar inativo/bloqueado/arquivado — não filtra status."""
    criados = {status: _usuario(db_session, empresa, status=status) for status in ("ativo", "inativo", "bloqueado", "arquivado")}

    resposta = _consultar(client_admin, [usuario.id for usuario in criados.values()])
    assert resposta.status_code == 200, resposta.text
    itens = {item["id"]: item["status"] for item in resposta.json()}
    for status, usuario in criados.items():
        assert itens.get(usuario.id) == status, f"status {status!r} não resolvido"


def test_conta_de_sistema_nunca_resolve(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    sistema = _usuario(db_session, empresa, is_system_account=True)
    comum = _usuario(db_session, empresa)

    resposta = _consultar(client_admin, [sistema.id, comum.id])
    assert resposta.status_code == 200, resposta.text
    assert [item["id"] for item in resposta.json()] == [comum.id]


def test_outra_empresa_e_inexistente_sao_indistinguiveis(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    de_outra = _usuario(db_session, outra_empresa)
    inexistente = str(uuid.uuid4())
    proprio = _usuario(db_session, empresa)

    so_alheios = _consultar(client_admin, [de_outra.id, inexistente])
    assert so_alheios.status_code == 200, so_alheios.text
    assert so_alheios.json() == []

    misto = _consultar(client_admin, [de_outra.id, proprio.id, inexistente])
    assert misto.status_code == 200, misto.text
    assert [item["id"] for item in misto.json()] == [proprio.id]
    # Nenhum sinal por item (placeholder/null/404) que permita mapear a base de outro tenant.
    assert de_outra.nome not in misto.text


def test_ordem_deterministica_nome_depois_id(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    zeta = _usuario(db_session, empresa, nome="Zeta Ordem")
    # Muitos homônimos: com poucos, a ordem de inserção coincidiria com a de id por acaso e o
    # desempate por id não seria exercitado.
    gemeos = [_usuario(db_session, empresa, nome="Alfa Ordem") for _ in range(8)]
    esperado = sorted(gemeo.id for gemeo in gemeos)
    esperado.append(zeta.id)

    entrada = [zeta.id] + [gemeo.id for gemeo in reversed(gemeos)]
    primeira = _consultar(client_admin, entrada).json()
    segunda = _consultar(client_admin, list(reversed(entrada))).json()
    assert [item["id"] for item in primeira] == esperado
    assert [item["id"] for item in segunda] == esperado


# --------------------------------------------------------------------------------------
# Validação
# --------------------------------------------------------------------------------------


def test_uuid_invalido_422(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    valido = _usuario(db_session, empresa)
    resposta = client_admin.get(URL, params={"ids": f"{valido.id},nao-e-uuid"})
    assert resposta.status_code == 422, resposta.text


def test_ids_ausente_ou_vazio_422(client_admin: TestClient) -> None:
    assert client_admin.get(URL).status_code == 422
    assert client_admin.get(URL, params={"ids": ""}).status_code == 422
    assert client_admin.get(URL, params={"ids": " , ,"}).status_code == 422


def test_limite_de_100_ids_unicos(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    usuarios = [_usuario(db_session, empresa) for _ in range(100)]
    no_limite = _consultar(client_admin, [usuario.id for usuario in usuarios])
    assert no_limite.status_code == 200, no_limite.text
    assert len(no_limite.json()) == 100

    acima = _consultar(client_admin, [usuario.id for usuario in usuarios] + [str(uuid.uuid4())])
    assert acima.status_code == 422, acima.text

    # O limite é sobre ids ÚNICOS: 101 entradas com repetição continuam valendo.
    repetidos = _consultar(client_admin, [usuarios[0].id] * 150)
    assert repetidos.status_code == 200, repetidos.text


# --------------------------------------------------------------------------------------
# Superfície (RBAC não ampliado) e SQL
# --------------------------------------------------------------------------------------


def test_projecao_identica_a_do_diretorio_sem_campos_sensiveis(
    client_operador: TestClient, db_session: Session, empresa: Empresa
) -> None:
    alvo = _usuario(db_session, empresa)

    por_ids = _consultar(client_operador, [alvo.id]).json()[0]
    diretorio = next(item for item in client_operador.get("/usuarios/diretorio", params={"limit": 200}).json() if item["id"] == alvo.id)

    assert por_ids == diretorio
    assert set(por_ids) == {"id", "codigoInterno", "nome", "status", "cargo", "departamentoId", "fotoUrl", "corIdentificacao"}
    texto = str(por_ids)
    assert alvo.email not in texto and "11999990000" not in texto


def _contar_sql(client: TestClient, db_session: Session, ids: list[str]) -> tuple[int, list[str]]:
    comandos: list[str] = []

    def _capturar(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _capturar)
    try:
        resposta = _consultar(client, ids)
    finally:
        event.remove(engine, "before_cursor_execute", _capturar)
    assert resposta.status_code == 200, resposta.text
    por_ids = [c for c in comandos if "usuarios.id IN" in c]
    return len(comandos), por_ids


def test_query_count_constante_e_uma_unica_busca_por_ids(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    usuarios = [_usuario(db_session, empresa) for _ in range(40)]

    total_1, por_ids_1 = _contar_sql(client_admin, db_session, [usuarios[0].id])
    total_5, por_ids_5 = _contar_sql(client_admin, db_session, [u.id for u in usuarios[:5]])
    total_40, por_ids_40 = _contar_sql(client_admin, db_session, [u.id for u in usuarios])

    assert total_1 == total_5 == total_40, (total_1, total_5, total_40)
    assert len(por_ids_1) == len(por_ids_5) == len(por_ids_40) == 1
    # Filtro de tenant e de conta de sistema estão na MESMA query.
    assert "usuarios.empresa_id" in por_ids_40[0]
    assert "is_system_account" in por_ids_40[0]


def test_usuario_230_resolvido_direto_sem_paginar_o_diretorio(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """>200 usuários: o 230º (por nome) está fora da primeira página de 200 do diretório e
    mesmo assim resolve numa única chamada."""
    for indice in range(1, 261):
        _usuario(db_session, empresa, nome=f"ZZPOR Usuario {indice:03d}")
    alvo = db_session.query(Usuario).filter(Usuario.nome == "ZZPOR Usuario 230").one()

    primeira_pagina = client_admin.get("/usuarios/diretorio", params={"limit": 200}).json()
    assert len(primeira_pagina) == 200
    assert alvo.id not in [item["id"] for item in primeira_pagina], "pré-condição: alvo fora da janela de 200"

    total, por_ids = _contar_sql(client_admin, db_session, [alvo.id])
    assert len(por_ids) == 1
    resposta = _consultar(client_admin, [alvo.id])
    assert [(item["id"], item["nome"]) for item in resposta.json()] == [(alvo.id, "ZZPOR Usuario 230")]
