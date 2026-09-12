"""Enforcement por permissão — primeira onda (Fase 2G.10B).

Cobre o que os testes de negócio de cada domínio (test_cliente.py, test_departamento.py, ...)
não têm como cobrir sozinhos: que `require_permissao` — o mecanismo novo — se comporta como
`require_admin_or_gestor` se comportava, e que o que mudou de propósito (diretórios que já
eram admin/gestor, overrides) funciona conforme o catálogo.

Os 468 testes já existentes desses 12 domínios continuam passando sem nenhuma alteração
neles — a prova de negócio por domínio já existe. Este arquivo prova o mecanismo em si.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissoes import PermissaoInvalidaError
from app.dependencies.permissoes import require_permissao
from app.models.usuario import Usuario
from app.models.usuario_permissao import UsuarioPermissao
from datetime import datetime, timezone

from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_cliente import _criar as _criar_cliente
from tests.test_departamento import _criar as _criar_departamento_response
from tests.test_tipo_tarefa import _criar as _criar_tipo_tarefa
from tests.test_workflow_modelo import _payload as _payload_workflow_modelo


def _criar_departamento(client: TestClient, **extra) -> dict:
    resposta = _criar_departamento_response(client, **extra)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()

# --------------------------------------------------------------------------------------
# Equivalência — GET (visualizar) nos 12 módulos da primeira onda, parametrizado.
#
# Cadastros cujo /diretorio JÁ era require_admin_or_gestor (achado do diagnóstico, item 13)
# migraram para a mesma permissão de "visualizar" — por isso entram na tabela com o path de
# diretório também. Os que tinham /diretorio aberto a qualquer autenticado (clientes,
# fornecedores, departamentos, equipes, grupos-cliente, workflows, projetos) NÃO entram aqui
# com esse path — ver test_diretorios_abertos_preservados abaixo.
# --------------------------------------------------------------------------------------

LISTAGENS_ADMIN_OU_GESTOR = [
    "/clientes",
    "/fornecedores",
    "/departamentos",
    "/equipes",
    "/grupos-cliente",
    "/pecas",
    "/pecas/diretorio",
    "/categorias-peca",
    "/categorias-peca/diretorio",
    "/workflow-modelos",
    "/tipos-tarefa",
    "/tipos-tarefa/diretorio",
    "/slas",
    "/modelos-campanha",
    "/modelos-campanha/diretorio",
    "/projetos",
]


@pytest.mark.parametrize("path", LISTAGENS_ADMIN_OU_GESTOR)
def test_admin_visualiza(client_admin: TestClient, path: str) -> None:
    assert client_admin.get(path).status_code == 200


@pytest.mark.parametrize("path", LISTAGENS_ADMIN_OU_GESTOR)
def test_gestor_visualiza(client_gestor: TestClient, path: str) -> None:
    assert client_gestor.get(path).status_code == 200


@pytest.mark.parametrize("path", LISTAGENS_ADMIN_OU_GESTOR)
def test_operador_nao_visualiza(client_operador: TestClient, path: str) -> None:
    assert client_operador.get(path).status_code == 403


# --------------------------------------------------------------------------------------
# Diretórios abertos preservados (item 13) — NÃO foram tocados nesta onda.
# --------------------------------------------------------------------------------------

DIRETORIOS_ABERTOS = [
    "/clientes/diretorio",
    "/fornecedores/diretorio",
    "/departamentos/diretorio",
    "/equipes/diretorio",
    "/grupos-cliente/diretorio",
    "/workflow-modelos/diretorio",
    "/projetos/diretorio",
]


@pytest.mark.parametrize("path", DIRETORIOS_ABERTOS)
def test_diretorios_abertos_preservados(client_operador: TestClient, path: str) -> None:
    """operador não tem `<modulo>.visualizar`, mas esses diretórios nunca dependeram disso —
    continuam abertos a qualquer autenticado, exatamente como antes desta fase."""
    assert client_operador.get(path).status_code == 200


def test_workflow_modelo_detalhe_continua_aberto(client_operador: TestClient, client_admin: TestClient) -> None:
    """GET /workflow-modelos/{id} não foi migrado — continua `get_current_user_password_ready`,
    igual antes (ver docstring da rota: quem cria Demanda precisa ver etapas)."""
    resposta_criacao = client_admin.post("/workflow-modelos", json=_payload_workflow_modelo())
    assert resposta_criacao.status_code == 201, resposta_criacao.text
    criado = resposta_criacao.json()
    resposta = client_operador.get(f"/workflow-modelos/{criado['id']}")
    assert resposta.status_code == 200, resposta.text


# --------------------------------------------------------------------------------------
# Ciclo completo (criar/editar/arquivar/restaurar) em 3 módulos com formatos de payload
# distintos — prova que a permissão certa é exigida em cada ação, não só em "visualizar".
# --------------------------------------------------------------------------------------


def test_cliente_ciclo_completo_por_permissao(client_admin: TestClient, client_gestor: TestClient, client_operador: TestClient) -> None:
    # operador: bloqueado em toda ação administrativa do cadastro.
    assert client_operador.post("/clientes", json={"nome": "x", "tipoDocumento": "cnpj", "corIdentificacao": "blue"}).status_code == 403

    criado = _criar_cliente(client_admin)
    assert client_operador.get(f"/clientes/{criado['id']}").status_code == 403
    assert client_operador.patch(f"/clientes/{criado['id']}", json={"nome": "y"}).status_code == 403
    assert client_operador.post(f"/clientes/{criado['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code == 403

    # gestor: mesmo acesso de admin (equivalência a require_admin_or_gestor).
    assert client_gestor.get(f"/clientes/{criado['id']}").status_code == 200
    assert client_gestor.patch(f"/clientes/{criado['id']}", json={"nome": "Cliente Editado"}).status_code == 200
    resposta = client_gestor.post(f"/clientes/{criado['id']}/arquivar", json={"motivoArquivamento": "teste"})
    assert resposta.status_code == 200
    assert client_gestor.post(f"/clientes/{criado['id']}/restaurar").status_code == 200


def test_departamento_ciclo_completo_por_permissao(client_admin: TestClient, client_operador: TestClient) -> None:
    assert client_operador.post("/departamentos", json={"nome": "x", "corIdentificacao": "blue"}).status_code == 403
    criado = _criar_departamento(client_admin)
    assert client_operador.patch(f"/departamentos/{criado['id']}", json={"nome": "y"}).status_code == 403
    assert client_admin.patch(f"/departamentos/{criado['id']}", json={"nome": "Depto Editado"}).status_code == 200
    assert client_operador.post(f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code == 403
    assert client_admin.post(f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "teste"}).status_code == 200


def test_tipo_tarefa_ciclo_completo_por_permissao(client_admin: TestClient, client_operador: TestClient) -> None:
    assert client_operador.post("/tipos-tarefa", json={"nome": "x"}).status_code == 403
    criado = _criar_tipo_tarefa(client_admin)
    assert client_operador.patch(f"/tipos-tarefa/{criado['id']}", json={"nome": "y"}).status_code == 403
    assert client_admin.patch(f"/tipos-tarefa/{criado['id']}", json={"nome": "Tipo Editado"}).status_code == 200
    assert client_operador.post(f"/tipos-tarefa/{criado['id']}/arquivar", json={"motivoArquivamento": "x"}).status_code == 403


# --------------------------------------------------------------------------------------
# Overrides (kickoff item 8 — decisão: `require_permissao` já usa `permissoes_efetivas`
# completo, defaults + overrides) e isolamento de usuário/tenant (itens 11-12).
# --------------------------------------------------------------------------------------


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


def test_override_conceder_libera_apenas_a_permissao_concedida(
    db_session: Session, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    """operador com `conceder clientes.visualizar` passa a listar clientes, mas continua sem
    `clientes.criar` — o override é pontual, não promove o perfil inteiro."""
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")

    assert client_operador.get("/clientes").status_code == 200
    assert client_operador.post("/clientes", json={"nome": "x", "tipoDocumento": "cnpj", "corIdentificacao": "blue"}).status_code == 403


def test_override_negar_bloqueia_gestor_em_acao_que_o_perfil_permitiria(
    db_session: Session, client_gestor: TestClient, usuario_gestor: Usuario
) -> None:
    """gestor tem `clientes.editar` por default — uma negação individual vence isso."""
    _override(db_session, usuario=usuario_gestor, permissao="clientes.editar", efeito="negar")

    criado = _criar_cliente(client_gestor)
    assert client_gestor.patch(f"/clientes/{criado['id']}", json={"nome": "y"}).status_code == 403
    # o resto do perfil continua intacto — visualizar não foi negado.
    assert client_gestor.get(f"/clientes/{criado['id']}").status_code == 200


def test_override_nao_afeta_outro_usuario(
    db_session: Session, empresa, client_operador: TestClient
) -> None:
    """Override de um operador não vaza para outro operador da MESMA empresa."""
    outro_operador = _criar_usuario_com_credencial(
        db_session, empresa=empresa, perfil_base="operador", email_prefixo="outro-operador"
    )
    _override(db_session, usuario=outro_operador, permissao="clientes.visualizar", efeito="conceder")

    # client_operador é uma pessoa DIFERENTE de outro_operador — nunca recebeu o override.
    assert client_operador.get("/clientes").status_code == 403


def test_override_nao_atravessa_tenant(
    db_session: Session, outra_empresa, client_operador: TestClient
) -> None:
    """Override de um usuário de OUTRA empresa nunca é considerado para ninguém desta."""
    usuario_outra_empresa = _criar_usuario_com_credencial(
        db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="op-outra-empresa"
    )
    _override(db_session, usuario=usuario_outra_empresa, permissao="clientes.visualizar", efeito="conceder")

    assert client_operador.get("/clientes").status_code == 403


# --------------------------------------------------------------------------------------
# Fail-closed (item 5) — chave inexistente falha na hora de declarar a dependency, não em
# runtime nem liberando acesso.
# --------------------------------------------------------------------------------------


def test_require_permissao_com_chave_inexistente_falha_na_definicao() -> None:
    with pytest.raises(PermissaoInvalidaError):
        require_permissao("modulo_que_nao_existe.acao_fantasma")


def test_require_permissao_e_reutilizavel_como_dependency_normal() -> None:
    """Só uma checagem de forma — `require_permissao(...)` devolve um callable usável em
    `Depends(...)`, mesmo formato de `require_admin_or_gestor`."""
    dependency = require_permissao("clientes.visualizar")
    assert callable(dependency)
    # Não executa a dependency de verdade aqui — isso já é coberto pelos testes de rota acima
    # (que exercitam o FastAPI real, com DB e resolução de usuário).
    assert Depends(dependency) is not None
