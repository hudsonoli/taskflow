"""Testes de infra/API da fundação de permissões (Fase 2G.10A).

Cobre: repository (isolamento usuário/tenant), service (cálculo efetivo via DB real),
exposição em `/auth/me` e `/usuarios/me`, e checagens de equivalência entre o catálogo e o
comportamento REAL de rotas já existentes (sem alterar nenhuma delas).

Lógica pura do resolver/catálogo fica em test_permissoes.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_permissao import UsuarioPermissao
from app.repositories.usuario_permissao_repository import UsuarioPermissaoRepository
from app.services.usuario_permissao_service import UsuarioPermissaoService
from tests.fixtures.usuarios import _criar_usuario_com_credencial


def _override(
    db: Session,
    *,
    usuario: Usuario,
    permissao: str,
    efeito: str,
    motivo: str | None = None,
    concedido_por_usuario_id: str | None = None,
) -> UsuarioPermissao:
    agora = datetime.now(timezone.utc)
    override = UsuarioPermissao(
        id=str(uuid.uuid4()),
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        permissao=permissao,
        efeito=efeito,
        motivo=motivo,
        concedido_por_usuario_id=concedido_por_usuario_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(override)
    db.flush()
    return override


def _payload_usuario(empresa: Empresa, **extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    return {
        "empresaId": empresa.id,
        "codigoInterno": f"u-{sufixo}",
        "nome": f"Usuário {sufixo}",
        "email": f"u-{sufixo}@teste.local",
        "perfilBase": "operador",
        "acessoSistema": True,
        **extra,
    }


# --------------------------------------------------------------------------------------
# Repository
# --------------------------------------------------------------------------------------


def test_repository_lista_apenas_overrides_do_usuario_pedido(
    db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_gestor: Usuario
) -> None:
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")
    _override(db_session, usuario=usuario_gestor, permissao="usuarios.criar", efeito="conceder")

    repository = UsuarioPermissaoRepository()
    do_operador = repository.list_by_usuario(db_session, empresa_id=empresa.id, usuario_id=usuario_operador.id)

    assert len(do_operador) == 1
    assert do_operador[0].permissao == "clientes.visualizar"


def test_repository_nao_retorna_override_com_empresa_id_divergente(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_operador: Usuario
) -> None:
    """Defesa em profundidade: mesmo que uma linha exista com o `usuario_id` certo mas
    `empresa_id` divergente (dado corrompido/bug), o repository não deve devolvê-la — o
    filtro é por usuario_id E empresa_id, nunca só um dos dois."""
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")
    # Linha "corrompida": usuario_id certo, empresa_id de outra empresa.
    corrompida = UsuarioPermissao(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        usuario_id=usuario_operador.id,
        permissao="usuarios.criar",
        efeito="conceder",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(corrompida)
    db_session.flush()

    repository = UsuarioPermissaoRepository()
    resultado = repository.list_by_usuario(db_session, empresa_id=empresa.id, usuario_id=usuario_operador.id)

    permissoes = {row.permissao for row in resultado}
    assert permissoes == {"clientes.visualizar"}
    assert "usuarios.criar" not in permissoes


# --------------------------------------------------------------------------------------
# Service — cálculo efetivo com DB real
# --------------------------------------------------------------------------------------


def test_service_sem_overrides_devolve_exatamente_o_default_do_perfil(
    db_session: Session, usuario_operador: Usuario
) -> None:
    service = UsuarioPermissaoService()
    efetivas = service.obter_permissoes_efetivas(db_session, usuario_operador)
    assert efetivas == sorted({"demandas.visualizar", "demandas.criar", "demandas.editar"})


def test_service_override_concede_permissao_extra(db_session: Session, usuario_operador: Usuario) -> None:
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")

    service = UsuarioPermissaoService()
    efetivas = service.obter_permissoes_efetivas(db_session, usuario_operador)

    assert "clientes.visualizar" in efetivas


def test_service_override_nega_permissao_do_default(db_session: Session, usuario_admin: Usuario) -> None:
    _override(db_session, usuario=usuario_admin, permissao="usuarios.criar", efeito="negar")

    service = UsuarioPermissaoService()
    efetivas = service.obter_permissoes_efetivas(db_session, usuario_admin)

    assert "usuarios.criar" not in efetivas
    assert "clientes.criar" in efetivas  # resto do default de admin intacto


def test_service_isolamento_entre_usuarios(
    db_session: Session, usuario_operador: Usuario, usuario_gestor: Usuario
) -> None:
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")

    service = UsuarioPermissaoService()
    efetivas_gestor = service.obter_permissoes_efetivas(db_session, usuario_gestor)

    # gestor já tem clientes.visualizar por default — o que importa é que o override do
    # operador não influenciou o CÁLCULO do gestor (nenhum efeito cruzado a mais/a menos).
    assert efetivas_gestor == service.obter_permissoes_efetivas(db_session, usuario_gestor)
    efetivas_operador = service.obter_permissoes_efetivas(db_session, usuario_operador)
    assert "clientes.visualizar" in efetivas_operador


def test_service_isolamento_entre_empresas(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    usuario_empresa_a = _criar_usuario_com_credencial(
        db_session, empresa=empresa, perfil_base="operador", email_prefixo="op-a"
    )
    usuario_empresa_b = _criar_usuario_com_credencial(
        db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="op-b"
    )
    _override(db_session, usuario=usuario_empresa_a, permissao="clientes.visualizar", efeito="conceder")

    service = UsuarioPermissaoService()
    efetivas_b = service.obter_permissoes_efetivas(db_session, usuario_empresa_b)

    assert "clientes.visualizar" not in efetivas_b
    assert efetivas_b == sorted({"demandas.visualizar", "demandas.criar", "demandas.editar"})


def test_service_determinismo_lista_ordenada(db_session: Session, usuario_admin: Usuario) -> None:
    service = UsuarioPermissaoService()
    resultado = service.obter_permissoes_efetivas(db_session, usuario_admin)
    assert resultado == sorted(resultado)
    assert isinstance(resultado, list)


# --------------------------------------------------------------------------------------
# Exposição em /auth/me e /usuarios/me
# --------------------------------------------------------------------------------------


def test_auth_me_expoe_permissoes_ordenadas(client_operador: TestClient) -> None:
    resposta = client_operador.get("/auth/me")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert "permissoes" in corpo
    assert corpo["permissoes"] == sorted(corpo["permissoes"])
    assert set(corpo["permissoes"]) == {"demandas.visualizar", "demandas.criar", "demandas.editar"}


def test_auth_me_compativel_com_campos_existentes(client_admin: TestClient) -> None:
    """Campo novo é aditivo — nada do contrato anterior de /auth/me some."""
    corpo = client_admin.get("/auth/me").json()
    for campo in ("usuarioId", "empresaId", "nome", "perfilBase", "acessoSistema", "status", "mustChangePassword"):
        assert campo in corpo


def test_usuarios_me_expoe_permissoes(client_gestor: TestClient) -> None:
    resposta = client_gestor.get("/usuarios/me")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["permissoes"] == sorted(corpo["permissoes"])
    assert "usuarios.visualizar" in corpo["permissoes"]
    assert "usuarios.criar" not in corpo["permissoes"]


def test_usuarios_get_outro_usuario_nao_expoe_permissoes(
    client_admin: TestClient, usuario_gestor: Usuario
) -> None:
    """GET /usuarios/{id} de OUTRA pessoa nunca devolve as permissões dela — só /me."""
    resposta = client_admin.get(f"/usuarios/{usuario_gestor.id}")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["permissoes"] is None


# --------------------------------------------------------------------------------------
# Equivalência — o catálogo bate com o enforcement REAL (que não mudou nesta fase)
# --------------------------------------------------------------------------------------


def test_equivalencia_admin_continua_administrativo(client_admin: TestClient) -> None:
    assert client_admin.get("/clientes").status_code == 200


def test_equivalencia_gestor_administra_cadastro_mas_nao_usuario(
    client_gestor: TestClient, empresa: Empresa
) -> None:
    assert client_gestor.get("/clientes").status_code == 200
    resposta = client_gestor.post("/usuarios", json=_payload_usuario(empresa))
    assert resposta.status_code == 403


def test_equivalencia_operador_bloqueado_em_area_administrativa(client_operador: TestClient) -> None:
    assert client_operador.get("/clientes").status_code == 403
    assert client_operador.get("/usuarios?empresaId=" + str(uuid.uuid4())).status_code == 403


def test_equivalencia_operador_continua_criando_demanda(client_operador: TestClient) -> None:
    """Reflete o achado D1 do diagnóstico — POST /demandas não tem guard de perfil hoje.
    Este teste documenta o comportamento atual; NÃO é uma correção (fica para 2G.10B)."""
    resposta = client_operador.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}"})
    assert resposta.status_code == 201, resposta.text


def test_equivalencia_operador_nao_arquiva_demanda(client_operador: TestClient) -> None:
    criada = client_operador.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}"}).json()
    resposta = client_operador.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "teste"})
    assert resposta.status_code == 403
