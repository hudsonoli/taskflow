"""Enforcement por permissão — Bloco 2B.1 da Fase 2G.10B: Tráfego / Sessões de Trabalho.

`list/get/abrir/fechar` migraram de `require_admin_or_gestor` (redefinição local) para
`require_trafego_gerenciar()` (app/dependencies/permissoes.py) — equivalente por padrão, mas
que NUNCA libera para `perfil_base == "operador"`, mesmo com `trafego.gerenciar = conceder`,
porque essas rotas expõem `inicioEm`/`fimEm`/`duracaoSegundos` por sessão (dado suficiente
para reconstruir métricas de horas). O teste mais importante deste arquivo é
`test_operador_com_grant_continua_403_nas_quatro_rotas`.

`GET /sessoes-trabalho/horas` não foi tocada — continua `get_current_user_password_ready` +
`pode_consultar_horas_departamento` (escopo/relação de Head). Este arquivo prova
explicitamente que overrides de `trafego.gerenciar` não vazam para ela.
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

from tests.test_sessao_trabalho import _client_para, _departamento, _usuario


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


def _abrir_payload(empresa_id: str, usuario_id: str) -> dict:
    return {"empresaId": empresa_id, "demandaId": str(uuid.uuid4()), "usuarioId": usuario_id}


def _abrir(client: TestClient, empresa_id: str, usuario_id: str) -> dict:
    resposta = client.post("/sessoes-trabalho/abrir", json=_abrir_payload(empresa_id, usuario_id))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# --------------------------------------------------------------------------------------
# Equivalência — admin e gestor permitido, operador 403, nas 4 rotas administrativas.
# --------------------------------------------------------------------------------------


def test_admin_lista(client_admin: TestClient, empresa: Empresa) -> None:
    assert client_admin.get("/sessoes-trabalho").status_code == 200


def test_gestor_lista(client_gestor: TestClient, empresa: Empresa) -> None:
    assert client_gestor.get("/sessoes-trabalho").status_code == 200


def test_operador_nao_lista(client_operador: TestClient) -> None:
    assert client_operador.get("/sessoes-trabalho").status_code == 403


def test_admin_abre_e_fecha(client_admin: TestClient, empresa: Empresa, usuario_operador: Usuario) -> None:
    sessao = _abrir(client_admin, empresa.id, usuario_operador.id)
    resposta = client_admin.post(f"/sessoes-trabalho/{sessao['id']}/fechar", json={"motivoEncerramento": "conclusao"})
    assert resposta.status_code == 200


def test_gestor_abre_e_fecha(client_gestor: TestClient, empresa: Empresa, usuario_operador: Usuario) -> None:
    sessao = _abrir(client_gestor, empresa.id, usuario_operador.id)
    resposta = client_gestor.post(f"/sessoes-trabalho/{sessao['id']}/fechar", json={"motivoEncerramento": "conclusao"})
    assert resposta.status_code == 200


def test_operador_nao_abre(client_operador: TestClient, empresa: Empresa, usuario_operador: Usuario) -> None:
    resposta = client_operador.post("/sessoes-trabalho/abrir", json=_abrir_payload(empresa.id, usuario_operador.id))
    assert resposta.status_code == 403


def test_admin_consulta_detalhe(client_admin: TestClient, empresa: Empresa, usuario_operador: Usuario) -> None:
    sessao = _abrir(client_admin, empresa.id, usuario_operador.id)
    assert client_admin.get(f"/sessoes-trabalho/{sessao['id']}").status_code == 200


def test_operador_nao_consulta_detalhe(
    client_admin: TestClient, client_operador: TestClient, empresa: Empresa, usuario_operador: Usuario
) -> None:
    sessao = _abrir(client_admin, empresa.id, usuario_operador.id)
    assert client_operador.get(f"/sessoes-trabalho/{sessao['id']}").status_code == 403


def test_operador_nao_fecha(
    client_admin: TestClient, client_operador: TestClient, empresa: Empresa, usuario_operador: Usuario
) -> None:
    sessao = _abrir(client_admin, empresa.id, usuario_operador.id)
    resposta = client_operador.post(f"/sessoes-trabalho/{sessao['id']}/fechar", json={"motivoEncerramento": "conclusao"})
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Overrides — deny em admin/gestor (sem bypass) e o teste crítico: grant em operador
# continua 403 nas 4 rotas.
# --------------------------------------------------------------------------------------


def test_admin_com_deny_recebe_403_nas_quatro_rotas(
    db_session: Session, client_admin: TestClient, usuario_admin: Usuario, empresa: Empresa, usuario_operador: Usuario
) -> None:
    sessao = _abrir(client_admin, empresa.id, usuario_operador.id)  # aberta ANTES do deny
    _override(db_session, usuario=usuario_admin, permissao="trafego.gerenciar", efeito="negar")

    assert client_admin.get("/sessoes-trabalho").status_code == 403
    assert client_admin.get(f"/sessoes-trabalho/{sessao['id']}").status_code == 403
    assert client_admin.post("/sessoes-trabalho/abrir", json=_abrir_payload(empresa.id, usuario_operador.id)).status_code == 403
    assert (
        client_admin.post(f"/sessoes-trabalho/{sessao['id']}/fechar", json={"motivoEncerramento": "conclusao"}).status_code
        == 403
    )


def test_gestor_com_deny_recebe_403_nas_quatro_rotas(
    db_session: Session, client_gestor: TestClient, usuario_gestor: Usuario
) -> None:
    _override(db_session, usuario=usuario_gestor, permissao="trafego.gerenciar", efeito="negar")

    assert client_gestor.get("/sessoes-trabalho").status_code == 403
    assert client_gestor.get(f"/sessoes-trabalho/{uuid.uuid4()}").status_code == 403
    assert client_gestor.post("/sessoes-trabalho/abrir", json={}).status_code == 403
    assert client_gestor.post(f"/sessoes-trabalho/{uuid.uuid4()}/fechar", json={"motivoEncerramento": "conclusao"}).status_code == 403


def test_operador_com_grant_continua_403_nas_quatro_rotas(
    db_session: Session, client_operador: TestClient, usuario_operador: Usuario, empresa: Empresa
) -> None:
    """O TESTE MAIS IMPORTANTE deste bloco: o override existe e é resolvido normalmente
    (`trafego.gerenciar` entra no conjunto efetivo do operador), mas a invariante de domínio
    de `require_trafego_gerenciar` prevalece — nenhuma das 4 rotas libera."""
    _override(db_session, usuario=usuario_operador, permissao="trafego.gerenciar", efeito="conceder")

    assert client_operador.get("/sessoes-trabalho").status_code == 403
    assert client_operador.get(f"/sessoes-trabalho/{uuid.uuid4()}").status_code == 403
    assert client_operador.post("/sessoes-trabalho/abrir", json=_abrir_payload(empresa.id, usuario_operador.id)).status_code == 403
    assert client_operador.post(f"/sessoes-trabalho/{uuid.uuid4()}/fechar", json={"motivoEncerramento": "conclusao"}).status_code == 403


# --------------------------------------------------------------------------------------
# Head — não confundir com operador comum. Head (perfil_base=operador, relação real com
# departamento) continua 403 nas 4 rotas administrativas; /horas continua liberado só para
# o próprio departamento, exatamente como antes desta fase.
# --------------------------------------------------------------------------------------


def test_head_continua_403_nas_quatro_rotas_administrativas(
    app, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    head = _usuario(db_session, empresa)
    departamento.responsavel_usuario_id = head.id
    db_session.flush()

    cliente = _client_para(app, head)
    assert cliente.get("/sessoes-trabalho").status_code == 403
    assert cliente.get(f"/sessoes-trabalho/{uuid.uuid4()}").status_code == 403
    assert cliente.post("/sessoes-trabalho/abrir", json=_abrir_payload(empresa.id, head.id)).status_code == 403
    assert cliente.post(f"/sessoes-trabalho/{uuid.uuid4()}/fechar", json={"motivoEncerramento": "conclusao"}).status_code == 403


def test_head_acessa_horas_do_proprio_departamento(app, db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    head = _usuario(db_session, empresa)
    departamento.responsavel_usuario_id = head.id
    db_session.flush()

    cliente = _client_para(app, head)
    resposta = cliente.get(f"/sessoes-trabalho/horas?departamentoId={departamento.id}")
    assert resposta.status_code == 200


def test_head_nao_acessa_horas_de_outro_departamento(app, db_session: Session, empresa: Empresa) -> None:
    departamento_do_head = _departamento(db_session, empresa)
    outro_departamento = _departamento(db_session, empresa)
    head = _usuario(db_session, empresa)
    departamento_do_head.responsavel_usuario_id = head.id
    db_session.flush()

    cliente = _client_para(app, head)
    resposta = cliente.get(f"/sessoes-trabalho/horas?departamentoId={outro_departamento.id}")
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# /horas isolado do override — a razão de existir deste bloco. Operador com
# `trafego.gerenciar = conceder` continua 403 em /horas, porque essa rota não usa
# `require_trafego_gerenciar` nem qualquer permissão — não porque o helper "também" roda lá.
# --------------------------------------------------------------------------------------


def test_operador_com_grant_continua_403_em_horas(
    db_session: Session, client_operador: TestClient, usuario_operador: Usuario, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    _override(db_session, usuario=usuario_operador, permissao="trafego.gerenciar", efeito="conceder")

    resposta = client_operador.get(f"/sessoes-trabalho/horas?departamentoId={departamento.id}")
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Tenant — preservado nas 4 rotas migradas, independente de `require_trafego_gerenciar`.
# --------------------------------------------------------------------------------------


def test_lista_filtrada_por_empresa(
    app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient, usuario_operador: Usuario
) -> None:
    _abrir(client_admin, empresa.id, usuario_operador.id)

    outro_admin = _usuario(db_session, outra_empresa)
    outro_admin.perfil_base = "admin"
    db_session.flush()
    token_outro_admin = create_access_token(sub=outro_admin.id, empresa_id=outro_admin.empresa_id, perfil_base="admin")
    cliente_empresa_b = TestClient(app)
    cliente_empresa_b.headers["Authorization"] = f"Bearer {token_outro_admin}"

    resposta = cliente_empresa_b.get("/sessoes-trabalho")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_consultar_sessao_de_outra_empresa_404(
    app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient, usuario_operador: Usuario
) -> None:
    sessao = _abrir(client_admin, empresa.id, usuario_operador.id)

    outro_admin = _usuario(db_session, outra_empresa)
    outro_admin.perfil_base = "admin"
    db_session.flush()
    cliente_empresa_b = _client_para(app, outro_admin)

    assert cliente_empresa_b.get(f"/sessoes-trabalho/{sessao['id']}").status_code == 404


def test_fechar_sessao_de_outra_empresa_404(
    app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient, usuario_operador: Usuario
) -> None:
    sessao = _abrir(client_admin, empresa.id, usuario_operador.id)

    outro_admin = _usuario(db_session, outra_empresa)
    outro_admin.perfil_base = "admin"
    db_session.flush()
    cliente_empresa_b = _client_para(app, outro_admin)

    resposta = cliente_empresa_b.post(f"/sessoes-trabalho/{sessao['id']}/fechar", json={"motivoEncerramento": "conclusao"})
    assert resposta.status_code == 404


def test_abrir_com_usuario_de_outra_empresa_rejeitado(
    db_session: Session, client_admin: TestClient, empresa: Empresa, outra_empresa: Empresa
) -> None:
    usuario_outra_empresa = _usuario(db_session, outra_empresa)
    resposta = client_admin.post("/sessoes-trabalho/abrir", json=_abrir_payload(empresa.id, usuario_outra_empresa.id))
    assert resposta.status_code == 422


# --------------------------------------------------------------------------------------
# Performance — 1 resolução de usuario_permissao por request, do ator, sem N+1 por sessão
# listada.
# --------------------------------------------------------------------------------------


def test_lista_nao_gera_n_mais_1_de_overrides(
    client_admin: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_admin: Usuario
) -> None:
    for _ in range(5):
        _abrir(client_admin, empresa.id, usuario_operador.id)

    chamadas = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "usuario_permissao" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = client_admin.get("/sessoes-trabalho")
    finally:
        event.remove(engine, "before_cursor_execute", _contar)

    assert resposta.status_code == 200
    assert len(resposta.json()) >= 5
    assert len(chamadas) == 1


# --------------------------------------------------------------------------------------
# Autenticação transversal — senha pendente continua bloqueando rota migrada, igual aos
# blocos anteriores.
# --------------------------------------------------------------------------------------


def test_senha_troca_obrigatoria_bloqueia_rota_de_trafego_migrada(app, db_session: Session, empresa: Empresa) -> None:
    usuario = _usuario(db_session, empresa)
    usuario.perfil_base = "admin"
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
    resposta = cliente.get("/sessoes-trabalho")

    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["detail"]["code"] == "SENHA_TROCA_OBRIGATORIA"


# --------------------------------------------------------------------------------------
# Consistência de erro — 403 uniforme, igual aos blocos anteriores.
# --------------------------------------------------------------------------------------


def test_403_por_falta_de_permissao_tem_formato_consistente(client_operador: TestClient) -> None:
    resposta = client_operador.get("/sessoes-trabalho")
    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso negado"}


def test_403_do_piso_de_operador_tem_mesmo_formato(
    db_session: Session, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    """O 403 do piso de `require_trafego_gerenciar` (operador com grant) usa a MESMA
    constante de mensagem do 403 comum de falta de permissão — não um formato diferente que
    entregaria por acidente qual dos dois motivos bloqueou."""
    _override(db_session, usuario=usuario_operador, permissao="trafego.gerenciar", efeito="conceder")
    resposta = client_operador.get("/sessoes-trabalho")
    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso negado"}
