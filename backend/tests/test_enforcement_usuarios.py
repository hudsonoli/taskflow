"""Enforcement por permissão — segunda onda, bloco 2A (Fase 2G.10B): Usuários.

Usuários é o único cadastro em que visualizar é mais permissivo que
criar/editar/suspender (`require_admin_or_gestor` vs `require_admin` puro — ver
app/core/permissoes.py, docstring de MODULO_USUARIOS). Este arquivo prova que
`require_permissao` reproduz exatamente essa assimetria, que `/me` e `/diretorio`
continuam fora do enforcement (self-service e seletor, respectivamente), e que a
proteção de conta de sistema (nível de serviço, não de rota) continua valendo mesmo
com a permissão certa.

Fora de escopo desta onda (não testado aqui de propósito — ver kickoff do bloco 2A):
corrigir self-lockout, último admin, expansão de perfis, PATCH /usuarios/me. As
proteções de self-lockout JÁ EXISTENTES (inativar/bloquear/excluir contra si mesmo) são
confirmadas abaixo como regressão — não alteradas por esta fase, só verificadas.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.models.usuario_permissao import UsuarioPermissao

from tests.fixtures.usuarios import _criar_usuario_com_credencial


def _payload_usuario(empresa_id: str, **overrides) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    payload = {
        "empresaId": empresa_id,
        "codigoInterno": f"enf-usr-{sufixo}",
        "nome": "Usuário Enforcement Teste",
        "email": f"enf-usr-{sufixo}@teste.taskfloww.local",
        "perfilBase": "operador",
    }
    payload.update(overrides)
    return payload


def _criar_usuario(client: TestClient, empresa_id: str, **overrides) -> dict:
    resposta = client.post("/usuarios", json=_payload_usuario(empresa_id, **overrides))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


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
# Equivalência — visualizar (usuarios.visualizar): admin e gestor, operador não.
# Assimetria real do domínio (diferente dos outros 12 cadastros da primeira onda).
# --------------------------------------------------------------------------------------


def test_admin_visualiza_lista(client_admin: TestClient, empresa: Empresa) -> None:
    resposta = client_admin.get("/usuarios", params={"empresaId": empresa.id})
    assert resposta.status_code == 200


def test_gestor_visualiza_lista(client_gestor: TestClient, empresa: Empresa) -> None:
    resposta = client_gestor.get("/usuarios", params={"empresaId": empresa.id})
    assert resposta.status_code == 200


def test_operador_nao_visualiza_lista(client_operador: TestClient, empresa: Empresa) -> None:
    resposta = client_operador.get("/usuarios", params={"empresaId": empresa.id})
    assert resposta.status_code == 403


def test_admin_visualiza_detalhe(client_admin: TestClient, usuario_operador: Usuario) -> None:
    assert client_admin.get(f"/usuarios/{usuario_operador.id}").status_code == 200


def test_gestor_visualiza_detalhe(client_gestor: TestClient, usuario_operador: Usuario) -> None:
    assert client_gestor.get(f"/usuarios/{usuario_operador.id}").status_code == 200


def test_operador_nao_visualiza_detalhe_de_outro(client_operador: TestClient, usuario_gestor: Usuario) -> None:
    assert client_operador.get(f"/usuarios/{usuario_gestor.id}").status_code == 403


# --------------------------------------------------------------------------------------
# Equivalência — criar (usuarios.criar): só admin. Mais restrito que visualizar.
# --------------------------------------------------------------------------------------


def test_admin_cria(client_admin: TestClient, empresa: Empresa) -> None:
    criado = _criar_usuario(client_admin, empresa.id)
    assert criado["perfilBase"] == "operador"


def test_gestor_nao_cria(client_gestor: TestClient, empresa: Empresa) -> None:
    resposta = client_gestor.post("/usuarios", json=_payload_usuario(empresa.id))
    assert resposta.status_code == 403


def test_operador_nao_cria(client_operador: TestClient, empresa: Empresa) -> None:
    resposta = client_operador.post("/usuarios", json=_payload_usuario(empresa.id))
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Equivalência — editar (usuarios.editar): só admin.
# --------------------------------------------------------------------------------------


def test_admin_edita(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.patch(f"/usuarios/{usuario_operador.id}", json={"nome": "Editado"})
    assert resposta.status_code == 200


def test_gestor_nao_edita(client_gestor: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_gestor.patch(f"/usuarios/{usuario_operador.id}", json={"nome": "Editado"})
    assert resposta.status_code == 403


def test_operador_nao_edita(client_operador: TestClient, usuario_gestor: Usuario) -> None:
    resposta = client_operador.patch(f"/usuarios/{usuario_gestor.id}", json={"nome": "Editado"})
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Equivalência — ações de status (usuarios.suspender): só admin. Cobre as 6 rotas que
# compartilham a mesma permission key (inativar/reativar/bloquear/desbloquear/excluir/
# restaurar) — cada uma tem formato de payload/guard de auto-alvo próprio, então são
# exercitadas individualmente, não parametrizadas por path genérico.
# --------------------------------------------------------------------------------------


def test_admin_inativa(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.post(f"/usuarios/{usuario_operador.id}/inativar", json={})
    assert resposta.status_code == 200


def test_gestor_nao_inativa(client_gestor: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_gestor.post(f"/usuarios/{usuario_operador.id}/inativar", json={})
    assert resposta.status_code == 403


def test_operador_nao_inativa(client_operador: TestClient, usuario_gestor: Usuario) -> None:
    resposta = client_operador.post(f"/usuarios/{usuario_gestor.id}/inativar", json={})
    assert resposta.status_code == 403


def test_admin_reativa(client_admin: TestClient, usuario_operador: Usuario) -> None:
    client_admin.post(f"/usuarios/{usuario_operador.id}/inativar", json={})
    resposta = client_admin.post(f"/usuarios/{usuario_operador.id}/reativar")
    assert resposta.status_code == 200


def test_gestor_nao_reativa(client_admin: TestClient, client_gestor: TestClient, usuario_operador: Usuario) -> None:
    client_admin.post(f"/usuarios/{usuario_operador.id}/inativar", json={})
    resposta = client_gestor.post(f"/usuarios/{usuario_operador.id}/reativar")
    assert resposta.status_code == 403


def test_admin_bloqueia(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.post(f"/usuarios/{usuario_operador.id}/bloquear")
    assert resposta.status_code == 200


def test_gestor_nao_bloqueia(client_gestor: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_gestor.post(f"/usuarios/{usuario_operador.id}/bloquear")
    assert resposta.status_code == 403


def test_admin_desbloqueia(client_admin: TestClient, usuario_operador: Usuario) -> None:
    client_admin.post(f"/usuarios/{usuario_operador.id}/bloquear")
    resposta = client_admin.post(f"/usuarios/{usuario_operador.id}/desbloquear")
    assert resposta.status_code == 200


def test_gestor_nao_desbloqueia(client_admin: TestClient, client_gestor: TestClient, usuario_operador: Usuario) -> None:
    client_admin.post(f"/usuarios/{usuario_operador.id}/bloquear")
    resposta = client_gestor.post(f"/usuarios/{usuario_operador.id}/desbloquear")
    assert resposta.status_code == 403


def test_admin_exclui(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.post(
        f"/usuarios/{usuario_operador.id}/excluir", json={"motivoArquivamento": "teste"}
    )
    assert resposta.status_code == 200


def test_gestor_nao_exclui(client_gestor: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_gestor.post(
        f"/usuarios/{usuario_operador.id}/excluir", json={"motivoArquivamento": "teste"}
    )
    assert resposta.status_code == 403


def test_admin_restaura(client_admin: TestClient, usuario_operador: Usuario) -> None:
    client_admin.post(f"/usuarios/{usuario_operador.id}/excluir", json={"motivoArquivamento": "teste"})
    resposta = client_admin.post(f"/usuarios/{usuario_operador.id}/restaurar")
    assert resposta.status_code == 200


def test_gestor_nao_restaura(client_admin: TestClient, client_gestor: TestClient, usuario_operador: Usuario) -> None:
    client_admin.post(f"/usuarios/{usuario_operador.id}/excluir", json={"motivoArquivamento": "teste"})
    resposta = client_gestor.post(f"/usuarios/{usuario_operador.id}/restaurar")
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# /me e /diretorio preservados — NÃO migrados, continuam abertos a qualquer autenticado
# (kickoff itens 5-6).
# --------------------------------------------------------------------------------------


def test_me_continua_aberto_a_qualquer_autenticado(client_operador: TestClient) -> None:
    assert client_operador.get("/usuarios/me").status_code == 200


def test_diretorio_continua_aberto_a_qualquer_autenticado(client_operador: TestClient) -> None:
    assert client_operador.get("/usuarios/diretorio").status_code == 200


# --------------------------------------------------------------------------------------
# Overrides (kickoff item 10) — comportamento já provado no mecanismo genérico
# (test_enforcement_cadastros.py); aqui confirma especificamente a assimetria de
# Usuários (visualizar != criar/editar/suspender).
# --------------------------------------------------------------------------------------


def test_gestor_com_grant_cria(db_session: Session, client_gestor: TestClient, usuario_gestor: Usuario, empresa: Empresa) -> None:
    _override(db_session, usuario=usuario_gestor, permissao="usuarios.criar", efeito="conceder")
    criado = _criar_usuario(client_gestor, empresa.id)
    assert criado["perfilBase"] == "operador"


def test_gestor_sem_grant_continua_403(client_gestor: TestClient, empresa: Empresa) -> None:
    resposta = client_gestor.post("/usuarios", json=_payload_usuario(empresa.id))
    assert resposta.status_code == 403


def test_gestor_com_grant_criar_nao_ganha_editar_nem_suspender(
    db_session: Session, client_gestor: TestClient, usuario_gestor: Usuario, usuario_operador: Usuario, empresa: Empresa
) -> None:
    """`usuarios.criar = conceder` é pontual — não implica `usuarios.editar` nem
    `usuarios.suspender`. gestor já tem `usuarios.visualizar` por default (não é efeito do
    override), então visualizar continua funcionando; criar/editar/suspender continua
    seguindo cada chave isoladamente."""
    _override(db_session, usuario=usuario_gestor, permissao="usuarios.criar", efeito="conceder")

    criado = _criar_usuario(client_gestor, empresa.id)
    assert client_gestor.get(f"/usuarios/{usuario_operador.id}").status_code == 200  # default, não o override
    assert client_gestor.patch(f"/usuarios/{criado['id']}", json={"nome": "y"}).status_code == 403
    assert client_gestor.post(f"/usuarios/{criado['id']}/inativar", json={}).status_code == 403


def test_admin_com_deny_editar_recebe_403(
    db_session: Session, client_admin: TestClient, usuario_admin: Usuario, usuario_operador: Usuario
) -> None:
    _override(db_session, usuario=usuario_admin, permissao="usuarios.editar", efeito="negar")
    resposta = client_admin.patch(f"/usuarios/{usuario_operador.id}", json={"nome": "y"})
    assert resposta.status_code == 403
    # o resto do perfil de admin continua intacto — só a chave negada foi afetada.
    assert client_admin.get(f"/usuarios/{usuario_operador.id}").status_code == 200
    assert client_admin.post(f"/usuarios/{usuario_operador.id}/inativar", json={}).status_code == 200


def test_operador_com_grant_visualizar_nao_ganha_outras_acoes(
    db_session: Session, client_operador: TestClient, usuario_operador: Usuario, usuario_gestor: Usuario, empresa: Empresa
) -> None:
    _override(db_session, usuario=usuario_operador, permissao="usuarios.visualizar", efeito="conceder")

    assert client_operador.get("/usuarios", params={"empresaId": empresa.id}).status_code == 200
    assert client_operador.get(f"/usuarios/{usuario_gestor.id}").status_code == 200
    assert client_operador.post("/usuarios", json=_payload_usuario(empresa.id)).status_code == 403
    assert client_operador.patch(f"/usuarios/{usuario_gestor.id}", json={"nome": "y"}).status_code == 403
    assert client_operador.post(f"/usuarios/{usuario_gestor.id}/inativar", json={}).status_code == 403


# --------------------------------------------------------------------------------------
# Tenant (kickoff item 11) — usuarios.visualizar não atravessa empresa, com ou sem
# override.
# --------------------------------------------------------------------------------------


def test_gestor_nao_visualiza_usuario_de_outra_empresa(
    db_session: Session, outra_empresa: Empresa, client_gestor: TestClient
) -> None:
    usuario_outra_empresa = _criar_usuario_com_credencial(
        db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="op-outra-empresa-usr"
    )
    assert client_gestor.get(f"/usuarios/{usuario_outra_empresa.id}").status_code == 404


def test_admin_com_permission_key_valida_nao_atravessa_tenant(
    db_session: Session, outra_empresa: Empresa, client_admin: TestClient
) -> None:
    """admin tem `usuarios.visualizar`/`usuarios.editar` por default — isso nunca autoriza
    cruzar tenant. A única defesa aqui é `ensure_resource_empresa`, que não foi tocada por
    esta fase (mesma garantia já provada nos 12 cadastros da primeira onda)."""
    usuario_outra_empresa = _criar_usuario_com_credencial(
        db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="op-outra-empresa-admin"
    )
    assert client_admin.get(f"/usuarios/{usuario_outra_empresa.id}").status_code == 404
    assert client_admin.patch(f"/usuarios/{usuario_outra_empresa.id}", json={"nome": "y"}).status_code == 404
    assert client_admin.post(f"/usuarios/{usuario_outra_empresa.id}/inativar", json={}).status_code == 404


def test_override_conceder_nao_ultrapassa_tenant(
    app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_operador: Usuario
) -> None:
    usuario_outra_empresa = _criar_usuario_com_credencial(
        db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="op-outra-empresa-usr2"
    )
    _override(db_session, usuario=usuario_operador, permissao="usuarios.visualizar", efeito="conceder")
    token_operador = create_access_token(
        sub=usuario_operador.id, empresa_id=usuario_operador.empresa_id, perfil_base="operador"
    )
    cliente_operador = TestClient(app)
    cliente_operador.headers["Authorization"] = f"Bearer {token_operador}"

    resposta = cliente_operador.get(f"/usuarios/{usuario_outra_empresa.id}")
    assert resposta.status_code == 404, resposta.text


# --------------------------------------------------------------------------------------
# Conta de sistema (kickoff item 12) — proteção vive no service (`get_by_id_visible`
# exclui a conta de sistema da busca administrativa), não na rota. Com a permission key
# certa concedida pelo perfil, admin ainda recebe 404 — não 200, não 403 por falta de
# permissão. `require_permissao` não alterou nem contornou essa proteção.
# --------------------------------------------------------------------------------------


def test_admin_nao_edita_conta_de_sistema(client_admin: TestClient, db_session: Session, usuario_operador: Usuario) -> None:
    usuario_operador.is_system_account = True
    db_session.flush()

    resposta = client_admin.patch(f"/usuarios/{usuario_operador.id}", json={"nome": "y"})

    assert resposta.status_code == 404, resposta.text


def test_admin_nao_bloqueia_conta_de_sistema(client_admin: TestClient, db_session: Session, usuario_operador: Usuario) -> None:
    usuario_operador.is_system_account = True
    db_session.flush()

    resposta = client_admin.post(f"/usuarios/{usuario_operador.id}/bloquear")

    assert resposta.status_code == 404, resposta.text


# --------------------------------------------------------------------------------------
# Self-lockout (revisão pré-merge, item 3) — proteções JÁ EXISTENTES antes desta fase
# (inativar/bloquear/excluir contra o próprio ID) continuam firmando mesmo passando por
# `require_permissao` em vez de `require_admin`. Não corrige o gap conhecido (reativar/
# desbloquear/restaurar/PATCH não têm essa checagem) — só confirma que o que já existia
# não regrediu.
# --------------------------------------------------------------------------------------


def test_admin_nao_inativa_a_si_mesmo(client_admin: TestClient, usuario_admin: Usuario) -> None:
    resposta = client_admin.post(f"/usuarios/{usuario_admin.id}/inativar", json={})
    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso negado"}


def test_admin_nao_bloqueia_a_si_mesmo(client_admin: TestClient, usuario_admin: Usuario) -> None:
    resposta = client_admin.post(f"/usuarios/{usuario_admin.id}/bloquear")
    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso negado"}


def test_admin_nao_exclui_a_si_mesmo(client_admin: TestClient, usuario_admin: Usuario) -> None:
    resposta = client_admin.post(f"/usuarios/{usuario_admin.id}/excluir", json={"motivoArquivamento": "x"})
    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso negado"}


# --------------------------------------------------------------------------------------
# /usuarios/diretorio (revisão pré-merge, item 6) — nunca chamou o serviço de permissões,
# diferente de /me (que só popula `permissoes` nele mesmo, ver Fase 2G.10A). Zero consultas
# a usuario_permissao, não uma.
# --------------------------------------------------------------------------------------


def test_diretorio_nao_consulta_overrides(client_operador: TestClient, db_session: Session) -> None:
    consultas = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "usuario_permissao" in statement:
            consultas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = client_operador.get("/usuarios/diretorio")
    finally:
        event.remove(engine, "before_cursor_execute", _contar)

    assert resposta.status_code == 200
    assert len(consultas) == 0


# --------------------------------------------------------------------------------------
# Autenticação transversal (revisão pré-merge, item 12) — teste representativo de que o
# router de Usuários mantém `get_current_user_password_ready` por cima do enforcement
# novo, igual ao provado genericamente na primeira onda (test_enforcement_cadastros.py).
# --------------------------------------------------------------------------------------


def test_senha_troca_obrigatoria_bloqueia_rota_de_usuarios_migrada(app, db_session: Session, empresa: Empresa) -> None:
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="admin", email_prefixo="senha-pendente-usr")
    credencial = db_session.query(UsuarioCredencial).filter_by(usuario_id=usuario.id).one()
    credencial.senha_deve_ser_alterada = True
    db_session.flush()
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base="admin")

    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    resposta = cliente.get("/usuarios", params={"empresaId": empresa.id})

    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["detail"]["code"] == "SENHA_TROCA_OBRIGATORIA"


# --------------------------------------------------------------------------------------
# Consistência de erro — 403 uniforme para falta de permissão, igual à primeira onda.
# --------------------------------------------------------------------------------------


def test_403_por_falta_de_permissao_tem_formato_consistente(client_operador: TestClient, empresa: Empresa) -> None:
    resposta = client_operador.get("/usuarios", params={"empresaId": empresa.id})
    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso negado"}
