"""D1.1 — Política real de criação de Demandas (Fase 2G.10B).

Fecha deliberadamente o gap D1 (documentado em app/core/permissoes.py e no diagnóstico da
Fase 2G.10): `demandas.criar` sai do default de `PERFIL_OPERADOR`. `POST /demandas` passa a
usar `require_demandas_criar()` (app/dependencies/permissoes.py), que resolve:

    override explícito (negar/conceder) > perfil (admin/gestor) > relação (Head/Atendimento)

Só D1.1 — "quem pode chamar `POST /demandas`". D1.2 ("o que pode selecionar" — cliente,
projeto, responsáveis, departamentos) continua deliberadamente fora de escopo: um ator
autorizado por este arquivo ainda escolhe livremente qualquer recurso válido do próprio
tenant, exatamente como antes desta fase.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.models.usuario_permissao import UsuarioPermissao

from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_demanda import _departamento, _payload


def _client_para(app, usuario: Usuario) -> TestClient:
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


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


def _head_por_responsavel(db: Session, empresa: Empresa, usuario: Usuario) -> Departamento:
    return _departamento(db, empresa, responsavel_usuario_id=usuario.id)


def _head_por_lider(db: Session, empresa: Empresa, usuario: Usuario) -> Departamento:
    departamento = _departamento(db, empresa)
    usuario.departamento_id = departamento.id
    usuario.lider_departamento = True
    db.flush()
    return departamento


def _atendimento(db: Session, empresa: Empresa, usuario: Usuario) -> Departamento:
    departamento = _departamento(db, empresa, nome="Atendimento")
    usuario.departamento_id = departamento.id
    db.flush()
    return departamento


def _operador_comum(db: Session, empresa: Empresa, *, sufixo: str) -> Usuario:
    return _criar_usuario_com_credencial(db, empresa=empresa, perfil_base="operador", email_prefixo=f"op-{sufixo}")


# --------------------------------------------------------------------------------------
# Matriz — sem override.
# --------------------------------------------------------------------------------------


def test_admin_cria_sem_override(client_admin: TestClient) -> None:
    assert client_admin.post("/demandas", json=_payload()).status_code == 201


def test_gestor_cria_sem_override(client_gestor: TestClient) -> None:
    assert client_gestor.post("/demandas", json=_payload()).status_code == 201


def test_head_por_responsavel_cria_sem_override(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-resp")
    _head_por_responsavel(db_session, empresa, head)
    resposta = _client_para(app, head).post("/demandas", json=_payload())
    assert resposta.status_code == 201, resposta.text


def test_head_por_lider_departamento_cria_sem_override(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-lider")
    _head_por_lider(db_session, empresa, head)
    resposta = _client_para(app, head).post("/demandas", json=_payload())
    assert resposta.status_code == 201, resposta.text


def test_atendimento_cria_sem_override(app, db_session: Session, empresa: Empresa) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend")
    _atendimento(db_session, empresa, atendimento)
    resposta = _client_para(app, atendimento).post("/demandas", json=_payload())
    assert resposta.status_code == 201, resposta.text


def test_operador_comum_nao_cria_sem_override(app, db_session: Session, empresa: Empresa) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="comum")
    resposta = _client_para(app, operador).post("/demandas", json=_payload())
    assert resposta.status_code == 403


def test_operador_de_outro_departamento_nao_e_atendimento(app, db_session: Session, empresa: Empresa) -> None:
    """Reforça que a elegibilidade de Atendimento é pelo NOME do departamento, não por
    pertencer a qualquer departamento — operador de um departamento comum continua 403."""
    operador = _operador_comum(db_session, empresa, sufixo="outro-depto")
    outro_departamento = _departamento(db_session, empresa, nome="Criação")
    operador.departamento_id = outro_departamento.id
    db_session.flush()
    resposta = _client_para(app, operador).post("/demandas", json=_payload())
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Matriz — override conceder (libera todo mundo, inclusive operador comum).
# --------------------------------------------------------------------------------------


def test_admin_cria_com_grant(db_session: Session, client_admin: TestClient, usuario_admin: Usuario) -> None:
    _override(db_session, usuario=usuario_admin, permissao="demandas.criar", efeito="conceder")
    assert client_admin.post("/demandas", json=_payload()).status_code == 201


def test_gestor_cria_com_grant(db_session: Session, client_gestor: TestClient, usuario_gestor: Usuario) -> None:
    _override(db_session, usuario=usuario_gestor, permissao="demandas.criar", efeito="conceder")
    assert client_gestor.post("/demandas", json=_payload()).status_code == 201


def test_head_cria_com_grant(app, db_session: Session, empresa: Empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-grant")
    _head_por_responsavel(db_session, empresa, head)
    _override(db_session, usuario=head, permissao="demandas.criar", efeito="conceder")
    resposta = _client_para(app, head).post("/demandas", json=_payload())
    assert resposta.status_code == 201, resposta.text


def test_atendimento_cria_com_grant(app, db_session: Session, empresa: Empresa) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-grant")
    _atendimento(db_session, empresa, atendimento)
    _override(db_session, usuario=atendimento, permissao="demandas.criar", efeito="conceder")
    resposta = _client_para(app, atendimento).post("/demandas", json=_payload())
    assert resposta.status_code == 201, resposta.text


def test_operador_comum_cria_com_grant(app, db_session: Session, empresa: Empresa) -> None:
    """Política 1 (recomendada no diagnóstico): override individual libera criação para
    operador comum, sem relação nenhuma — igual a qualquer outra permissão do catálogo."""
    operador = _operador_comum(db_session, empresa, sufixo="comum-grant")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")
    resposta = _client_para(app, operador).post("/demandas", json=_payload())
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Matriz — override negar (bloqueia todo mundo, sem exceção — nem perfil, nem relação).
# --------------------------------------------------------------------------------------


def test_admin_nao_cria_com_deny(db_session: Session, client_admin: TestClient, usuario_admin: Usuario) -> None:
    _override(db_session, usuario=usuario_admin, permissao="demandas.criar", efeito="negar")
    assert client_admin.post("/demandas", json=_payload()).status_code == 403


def test_gestor_nao_cria_com_deny(db_session: Session, client_gestor: TestClient, usuario_gestor: Usuario) -> None:
    _override(db_session, usuario=usuario_gestor, permissao="demandas.criar", efeito="negar")
    assert client_gestor.post("/demandas", json=_payload()).status_code == 403


def test_head_nao_cria_com_deny(app, db_session: Session, empresa: Empresa) -> None:
    """Confirma a preferência explícita: um `negar` individual bloqueia mesmo uma capacidade
    que a relação de Head normalmente concede — override sempre vence a relação."""
    head = _operador_comum(db_session, empresa, sufixo="head-deny")
    _head_por_responsavel(db_session, empresa, head)
    _override(db_session, usuario=head, permissao="demandas.criar", efeito="negar")
    resposta = _client_para(app, head).post("/demandas", json=_payload())
    assert resposta.status_code == 403, resposta.text


def test_atendimento_nao_cria_com_deny(app, db_session: Session, empresa: Empresa) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-deny")
    _atendimento(db_session, empresa, atendimento)
    _override(db_session, usuario=atendimento, permissao="demandas.criar", efeito="negar")
    resposta = _client_para(app, atendimento).post("/demandas", json=_payload())
    assert resposta.status_code == 403, resposta.text


def test_operador_comum_nao_cria_com_deny(app, db_session: Session, empresa: Empresa) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="comum-deny")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="negar")
    resposta = _client_para(app, operador).post("/demandas", json=_payload())
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Numeração — 403 nunca reserva número, com override negar ou ausência de relação.
# --------------------------------------------------------------------------------------


def _numeracao(db: Session, empresa_id: str) -> tuple[int, int | None]:
    total = db.execute(
        text("SELECT COUNT(*) FROM demandas WHERE empresa_id = :e"), {"e": empresa_id}
    ).scalar_one()
    ultimo = db.execute(
        text("SELECT ultimo_numero FROM sequencias_operacionais WHERE empresa_id = :e AND tipo_entidade = 'demanda'"),
        {"e": empresa_id},
    ).scalar_one_or_none()
    return total, ultimo


def test_operador_comum_sem_override_nao_reserva_numero(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="numeracao")
    antes = _numeracao(db_session, empresa.id)

    resposta = _client_para(app, operador).post("/demandas", json=_payload())
    assert resposta.status_code == 403

    depois = _numeracao(db_session, empresa.id)
    assert depois == antes, "403 por falta de relação/permissão não pode ter reservado número"


def test_admin_com_deny_nao_reserva_numero(
    db_session: Session, client_admin: TestClient, usuario_admin: Usuario, empresa: Empresa
) -> None:
    antes = _numeracao(db_session, empresa.id)
    _override(db_session, usuario=usuario_admin, permissao="demandas.criar", efeito="negar")

    resposta = client_admin.post("/demandas", json=_payload())
    assert resposta.status_code == 403

    depois = _numeracao(db_session, empresa.id)
    assert depois == antes, "403 por override negar não pode ter reservado número"


# --------------------------------------------------------------------------------------
# Autenticação transversal — password_ready preservado no router.
# --------------------------------------------------------------------------------------


def test_senha_troca_obrigatoria_bloqueia_criacao(app, db_session: Session, empresa: Empresa) -> None:
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="admin", email_prefixo="senha-pendente-criar")
    credencial = db_session.query(UsuarioCredencial).filter_by(usuario_id=usuario.id).one()
    credencial.senha_deve_ser_alterada = True
    db_session.flush()
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base="admin")

    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    resposta = cliente.post("/demandas", json=_payload())

    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["detail"]["code"] == "SENHA_TROCA_OBRIGATORIA"


# --------------------------------------------------------------------------------------
# Performance — override é 1 query; caminho relacional soma no máximo mais 2, O(1), sem N+1.
# --------------------------------------------------------------------------------------


def _contador_de(tabela: str, alvo: list[str]):
    def _contar(conn, cursor, statement, parameters, context, executemany):
        if tabela in statement:
            alvo.append(statement)

    return _contar


def test_admin_sem_override_gera_uma_query(client_admin: TestClient, db_session: Session) -> None:
    chamadas: list[str] = []
    engine = db_session.get_bind()
    listener = _contador_de("usuario_permissao", chamadas)
    event.listen(engine, "before_cursor_execute", listener)
    try:
        resposta = client_admin.post("/demandas", json=_payload())
    finally:
        event.remove(engine, "before_cursor_execute", listener)

    assert resposta.status_code == 201
    assert len(chamadas) == 1


def test_operador_comum_sem_override_gera_no_maximo_tres_queries_relacionais(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="perf")
    cliente = _client_para(app, operador)

    chamadas_override: list[str] = []
    chamadas_departamentos: list[str] = []
    engine = db_session.get_bind()
    listener_override = _contador_de("usuario_permissao", chamadas_override)
    listener_departamentos = _contador_de("departamentos", chamadas_departamentos)
    event.listen(engine, "before_cursor_execute", listener_override)
    event.listen(engine, "before_cursor_execute", listener_departamentos)
    try:
        resposta = cliente.post("/demandas", json=_payload())
    finally:
        event.remove(engine, "before_cursor_execute", listener_override)
        event.remove(engine, "before_cursor_execute", listener_departamentos)

    assert resposta.status_code == 403
    assert len(chamadas_override) == 1
    # departamentos_como_head (1) + eh_atendimento (1, busca o próprio departamento do
    # usuário — aqui None, então nem chega a rodar) — no máximo 2, sem N+1.
    assert len(chamadas_departamentos) <= 2


# --------------------------------------------------------------------------------------
# Consistência de erro — 403 uniforme, igual a qualquer outra permissão do sistema.
# --------------------------------------------------------------------------------------


def test_403_tem_formato_consistente(app, db_session: Session, empresa: Empresa) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="formato")
    resposta = _client_para(app, operador).post("/demandas", json=_payload())
    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso negado"}


# --------------------------------------------------------------------------------------
# /auth/me — consequência deliberada e documentada (não escondida): Head/Atendimento
# conseguem criar por relação, mas `/auth/me` só reflete perfil+override, nunca relação —
# então `demandas.criar` NÃO aparece na lista deles, mesmo autorizados a criar. O frontend
# não depende dessa key (confirmado: nenhuma referência a "demandas.criar" nem ao campo
# `permissoes` em todo o código do frontend) — sem incoerência de contrato de API.
# --------------------------------------------------------------------------------------


def test_head_nao_ve_demandas_criar_em_auth_me_mesmo_podendo_criar(
    app, db_session: Session, empresa: Empresa
) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-authme")
    _head_por_responsavel(db_session, empresa, head)
    cliente = _client_para(app, head)

    resposta_me = cliente.get("/auth/me")
    assert resposta_me.status_code == 200
    assert "demandas.criar" not in resposta_me.json()["permissoes"]

    resposta_criar = cliente.post("/demandas", json=_payload())
    assert resposta_criar.status_code == 201, resposta_criar.text
