"""Enforcement por permissão — Bloco 2C.1 da Fase 2G.10B: rotas principais de Demandas.

`list/diretorio/get` migraram para `require_permissao("demandas.visualizar")`, `create` para
`require_permissao("demandas.criar")`, `update` para `require_permissao("demandas.editar")`,
`arquivar/restaurar` de `require_admin_or_gestor` (redefinição local) para
`require_permissao("demandas.arquivar")`. Os defaults do catálogo já espelhavam o
comportamento real de hoje (ver app/core/permissoes.py) — esta migração é equivalência pura,
não fecha o gap D1 (`POST /demandas` continua aberto a operador comum por decisão explícita
desta fase, ver `test_operador_continua_criando_por_default_d1_nao_fechado`).

Permissão nunca substitui escopo: toda rota continua chamando `resolver_escopo_demanda`/
`get_no_escopo` depois do guard — os dois se SOMAM, nunca um substitui o outro. O teste mais
importante deste arquivo, além do documental de D1, é
`test_override_editar_nao_amplia_escopo_para_fora_dele`.

Fora de escopo (não tocados): `/ajustes`, `/conclusao-email` (continuam
`get_current_user_password_ready` + escopo, sem permission key), e os routers satélite
(checklist, comentários, arquivos, histórico).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.models.usuario_permissao import UsuarioPermissao

from tests.test_demanda import _criar, _departamento, _payload


def _override(db: Session, *, usuario: Usuario, permissao: str, efeito: str) -> UsuarioPermissao:
    agora = datetime.now(timezone.utc)
    override = UsuarioPermissao(
        id=str(uuid.uuid4()),
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        permissao=permissao,
        efeito=efeito,
        created_at=agora,
        updated_at=agora,
    )
    db.add(override)
    db.flush()
    return override


# --------------------------------------------------------------------------------------
# Equivalência — admin/gestor/operador, defaults do catálogo (usuario_permissao vazia).
# --------------------------------------------------------------------------------------


def test_admin_visualiza_lista(client_admin: TestClient) -> None:
    assert client_admin.get("/demandas").status_code == 200


def test_gestor_visualiza_lista(client_gestor: TestClient) -> None:
    assert client_gestor.get("/demandas").status_code == 200


def test_operador_visualiza_lista_dentro_do_proprio_escopo(client_operador: TestClient) -> None:
    """operador tem `demandas.visualizar` por default — 200, mesmo sem nenhuma demanda no
    escopo (lista vazia não é falta de permissão)."""
    resposta = client_operador.get("/demandas")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_admin_visualiza_diretorio(client_admin: TestClient) -> None:
    assert client_admin.get("/demandas/diretorio").status_code == 200


def test_operador_visualiza_diretorio(client_operador: TestClient) -> None:
    assert client_operador.get("/demandas/diretorio").status_code == 200


def test_override_visualizar_nao_amplia_escopo_do_diretorio(
    db_session: Session, client_operador: TestClient, usuario_operador: Usuario, client_admin: TestClient
) -> None:
    """`demandas.visualizar = conceder` (redundante — operador já tem por default) não
    transforma `/demandas/diretorio` em visão total; a resolução de escopo é a mesma da
    listagem principal, revalidada aqui separadamente."""
    _override(db_session, usuario=usuario_operador, permissao="demandas.visualizar", efeito="conceder")
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    _criar(client_admin)  # de outra pessoa, fora do escopo do operador

    achados = client_operador.get("/demandas/diretorio").json()
    assert [d["id"] for d in achados] == [minha["id"]]


def test_diretorio_nao_gera_n_mais_1_de_overrides(client_admin: TestClient, db_session: Session) -> None:
    for _ in range(5):
        _criar(client_admin)

    chamadas = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "usuario_permissao" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = client_admin.get("/demandas/diretorio")
    finally:
        event.remove(engine, "before_cursor_execute", _contar)

    assert resposta.status_code == 200
    assert len(resposta.json()) >= 5
    assert len(chamadas) == 1


def test_admin_cria(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    assert criada["nome"]


def test_gestor_cria(client_gestor: TestClient) -> None:
    criada = _criar(client_gestor)
    assert criada["nome"]


def test_operador_cria(client_operador: TestClient) -> None:
    """default atual do catálogo — ver seção D1 abaixo."""
    criada = _criar(client_operador)
    assert criada["nome"]


def test_admin_edita(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"nome": "Editada"})
    assert resposta.status_code == 200


def test_operador_edita_demanda_do_proprio_escopo(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    resposta = client_operador.patch(f"/demandas/{minha['id']}", json={"nome": "Editada pelo operador"})
    assert resposta.status_code == 200


def test_admin_arquiva_e_restaura(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    resposta = client_admin.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "teste"})
    assert resposta.status_code == 200
    assert client_admin.post(f"/demandas/{criada['id']}/restaurar").status_code == 200


def test_gestor_arquiva(client_gestor: TestClient) -> None:
    criada = _criar(client_gestor)
    resposta = client_gestor.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "teste"})
    assert resposta.status_code == 200


def test_operador_nao_arquiva(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    resposta = client_operador.post(f"/demandas/{minha['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert resposta.status_code == 403


def test_operador_nao_restaura(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    client_admin.post(f"/demandas/{minha['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_operador.post(f"/demandas/{minha['id']}/restaurar")
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# D1 — documental. Esta fase NÃO fecha o gap: operador comum continua criando demanda por
# default, exatamente como antes da migração. A restrição (admin/gestor/Head/Atendimento,
# ver `podeCriarDemanda` no frontend) é decisão funcional separada, fora desta fase.
# --------------------------------------------------------------------------------------


def test_operador_continua_criando_por_default_d1_nao_fechado(client_operador: TestClient) -> None:
    """Prova que o Bloco 2C.1 não fechou D1 por acidente: operador comum, sem Head, sem
    Atendimento, sem nenhum override, continua com 201 em POST /demandas — igual ao
    comportamento de antes desta migração (`get_current_user_password_ready` sozinho)."""
    resposta = client_operador.post("/demandas", json=_payload())
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Overrides — deny (sem bypass) e grant (sem ampliar escopo).
# --------------------------------------------------------------------------------------


def test_admin_com_deny_visualizar_recebe_403(
    db_session: Session, client_admin: TestClient, usuario_admin: Usuario
) -> None:
    _override(db_session, usuario=usuario_admin, permissao="demandas.visualizar", efeito="negar")
    assert client_admin.get("/demandas").status_code == 403
    assert client_admin.get("/demandas/diretorio").status_code == 403
    assert client_admin.get(f"/demandas/{uuid.uuid4()}").status_code == 403


def test_gestor_com_deny_criar_recebe_403(db_session: Session, client_gestor: TestClient, usuario_gestor: Usuario) -> None:
    _override(db_session, usuario=usuario_gestor, permissao="demandas.criar", efeito="negar")
    resposta = client_gestor.post("/demandas", json=_payload())
    assert resposta.status_code == 403


def test_admin_com_deny_editar_recebe_403(client_admin: TestClient, db_session: Session, usuario_admin: Usuario) -> None:
    criada = _criar(client_admin)
    _override(db_session, usuario=usuario_admin, permissao="demandas.editar", efeito="negar")
    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"nome": "y"})
    assert resposta.status_code == 403
    # resto do perfil intacto — visualizar não foi negado.
    assert client_admin.get(f"/demandas/{criada['id']}").status_code == 200


def test_admin_com_deny_arquivar_recebe_403(client_admin: TestClient, db_session: Session, usuario_admin: Usuario) -> None:
    criada = _criar(client_admin)
    _override(db_session, usuario=usuario_admin, permissao="demandas.arquivar", efeito="negar")
    resposta = client_admin.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert resposta.status_code == 403


def test_gestor_com_deny_arquivar_recebe_403(client_gestor: TestClient, db_session: Session, usuario_gestor: Usuario) -> None:
    criada = _criar(client_gestor)
    _override(db_session, usuario=usuario_gestor, permissao="demandas.arquivar", efeito="negar")
    resposta = client_gestor.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert resposta.status_code == 403


def test_override_editar_nao_amplia_escopo_para_fora_dele(
    db_session: Session, client_operador: TestClient, usuario_operador: Usuario, client_admin: TestClient
) -> None:
    """O TESTE MAIS IMPORTANTE deste bloco (além do documental de D1): um override
    redundante de `demandas.editar = conceder` — operador já tem essa permissão por default —
    não transforma o operador em visão total. Dentro do escopo continua editando; fora,
    continua 404, nunca 200."""
    _override(db_session, usuario=usuario_operador, permissao="demandas.editar", efeito="conceder")

    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    de_outro = _criar(client_admin)

    assert client_operador.patch(f"/demandas/{minha['id']}", json={"nome": "y"}).status_code == 200
    assert client_operador.patch(f"/demandas/{de_outro['id']}", json={"nome": "y"}).status_code == 404


def test_override_visualizar_nao_atravessa_tenant(
    db_session: Session, outra_empresa: Empresa, client_admin: TestClient, usuario_admin: Usuario
) -> None:
    _override(db_session, usuario=usuario_admin, permissao="demandas.visualizar", efeito="conceder")

    outro_admin_token_owner = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"adm-{uuid.uuid4().hex[:8]}",
        nome="Admin outra empresa",
        email=f"adm-{uuid.uuid4().hex[:8]}@teste.local",
        perfil_base="admin",
        acesso_sistema=True,
        status="ativo",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(outro_admin_token_owner)
    db_session.flush()
    token_outro_admin = create_access_token(
        sub=outro_admin_token_owner.id, empresa_id=outro_admin_token_owner.empresa_id, perfil_base="admin"
    )
    cliente_empresa_b = TestClient(client_admin.app)
    cliente_empresa_b.headers["Authorization"] = f"Bearer {token_outro_admin}"
    de_outra_empresa = _criar(cliente_empresa_b)

    resposta = client_admin.get(f"/demandas/{de_outra_empresa['id']}")
    assert resposta.status_code == 404, resposta.text


def test_operador_com_grant_arquivar_ainda_respeita_escopo(
    db_session: Session, client_operador: TestClient, usuario_operador: Usuario, client_admin: TestClient
) -> None:
    """`demandas.arquivar = conceder` para operador libera a AÇÃO (gate passa), mas o
    RECURSO continua isolado por escopo — a mesma independência já provada em editar."""
    _override(db_session, usuario=usuario_operador, permissao="demandas.arquivar", efeito="conceder")

    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    de_outro = _criar(client_admin)

    assert (
        client_operador.post(f"/demandas/{minha['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code
        == 200
    )
    assert (
        client_operador.post(f"/demandas/{de_outro['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code
        == 404
    )


# --------------------------------------------------------------------------------------
# Escopo fora — reforço direto do item 16 do kickoff.
# --------------------------------------------------------------------------------------


def test_operador_recebe_404_ao_editar_fora_do_escopo(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    de_outro = _criar(client_admin)

    assert client_operador.patch(f"/demandas/{minha['id']}", json={"nome": "y"}).status_code == 200
    assert client_operador.patch(f"/demandas/{de_outro['id']}", json={"nome": "y"}).status_code == 404


# --------------------------------------------------------------------------------------
# Numeração — 403 por falta de permissão nunca reserva número. Teste crítico.
# --------------------------------------------------------------------------------------


def test_403_por_permissao_nao_reserva_numero_operacional(
    db_session: Session, client_gestor: TestClient, usuario_gestor: Usuario, empresa: Empresa
) -> None:
    total_antes = db_session.execute(
        text("SELECT COUNT(*) FROM demandas WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    ultimo_antes = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_operacionais "
            "WHERE empresa_id = :e AND tipo_entidade = 'demanda'"
        ),
        {"e": empresa.id},
    ).scalar_one_or_none()

    _override(db_session, usuario=usuario_gestor, permissao="demandas.criar", efeito="negar")
    resposta = client_gestor.post("/demandas", json=_payload())
    assert resposta.status_code == 403

    total_depois = db_session.execute(
        text("SELECT COUNT(*) FROM demandas WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    ultimo_depois = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_operacionais "
            "WHERE empresa_id = :e AND tipo_entidade = 'demanda'"
        ),
        {"e": empresa.id},
    ).scalar_one_or_none()

    assert total_depois == total_antes, "403 por falta de permissão não pode ter criado Demanda"
    assert ultimo_depois == ultimo_antes, "número operacional não pode ter sido reservado antes da permissão"


# --------------------------------------------------------------------------------------
# Autenticação transversal.
# --------------------------------------------------------------------------------------


def test_senha_troca_obrigatoria_bloqueia_rota_de_demandas_migrada(app, db_session: Session, empresa: Empresa) -> None:
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"adm-senha-{uuid.uuid4().hex[:8]}",
        nome="Admin senha pendente",
        email=f"adm-senha-{uuid.uuid4().hex[:8]}@teste.local",
        perfil_base="admin",
        acesso_sistema=True,
        status="ativo",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(usuario)
    db_session.flush()
    credencial = UsuarioCredencial(
        id=str(uuid.uuid4()),
        usuario_id=usuario.id,
        senha_hash="x",
        senha_definida_em=datetime.now(timezone.utc),
        senha_deve_ser_alterada=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(credencial)
    db_session.flush()
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base="admin")

    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    resposta = cliente.get("/demandas")

    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["detail"]["code"] == "SENHA_TROCA_OBRIGATORIA"


# --------------------------------------------------------------------------------------
# Performance — 1 resolução de usuario_permissao por request, do ator, sem N+1 por demanda
# listada.
# --------------------------------------------------------------------------------------


def test_lista_nao_gera_n_mais_1_de_overrides(client_admin: TestClient, db_session: Session) -> None:
    for _ in range(5):
        _criar(client_admin)

    chamadas = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "usuario_permissao" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = client_admin.get("/demandas")
    finally:
        event.remove(engine, "before_cursor_execute", _contar)

    assert resposta.status_code == 200
    assert len(resposta.json()) >= 5
    assert len(chamadas) == 1


# --------------------------------------------------------------------------------------
# Consistência de erro.
# --------------------------------------------------------------------------------------


def test_403_por_falta_de_permissao_tem_formato_consistente(client_operador: TestClient, db_session: Session, usuario_operador: Usuario) -> None:
    _override(db_session, usuario=usuario_operador, permissao="demandas.visualizar", efeito="negar")
    resposta = client_operador.get("/demandas")
    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso negado"}
