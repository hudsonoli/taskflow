"""Testes de validação da infraestrutura de testes — não são cobertura de negócio.

Cada teste prova uma garantia específica da infra (isolamento, autenticação, autorização,
não-vazamento entre testes). Nenhum depende de ordem de execução nem de estado deixado por
outro teste.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.services.usuario_service import UsuarioService
from app.schemas.usuario import UsuarioCreate
from tests.fixtures.usuarios import SENHA_CONHECIDA
from tests.helpers.assertions import assert_erro_simples
from tests.helpers.auth import login_via_api


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_login_real_via_api_com_credencial_correta(
    client: TestClient, empresa: Empresa, usuario_admin: Usuario
) -> None:
    response = login_via_api(client, empresa=empresa, usuario=usuario_admin, senha=SENHA_CONHECIDA)
    assert response.status_code == 200, response.text
    corpo = response.json()
    assert corpo["accessToken"]
    assert corpo["mustChangePassword"] is False


def test_login_real_via_api_com_senha_errada(client: TestClient, empresa: Empresa, usuario_admin: Usuario) -> None:
    response = login_via_api(client, empresa=empresa, usuario=usuario_admin, senha="senha-errada-qualquer")
    assert_erro_simples(response, 401)


def test_admin_cria_usuario_e_le_de_volta(client_admin: TestClient, empresa: Empresa) -> None:
    sufixo = uuid.uuid4().hex[:8]
    payload = {
        "empresaId": empresa.id,
        "codigoInterno": f"novo-usuario-{sufixo}",
        "nome": "Novo Usuário",
        "email": f"novo-usuario-{sufixo}@teste.taskfloww.local",
        "perfilBase": "operador",
        "acessoSistema": True,
    }
    criado = client_admin.post("/usuarios", json=payload)
    assert criado.status_code == 201, criado.text
    usuario_id = criado.json()["id"]

    lido = client_admin.get(f"/usuarios/{usuario_id}")
    assert lido.status_code == 200, lido.text
    assert lido.json()["email"] == payload["email"]


def test_isolamento_por_empresa_retorna_404(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    usuario_outra_empresa = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"usuario-outra-empresa-{uuid.uuid4().hex[:8]}",
        nome="Usuário de Outra Empresa",
        email=f"outra-empresa-{uuid.uuid4().hex[:8]}@teste.taskfloww.local",
        perfil_base="operador",
        acesso_sistema=True,
        status="ativo",
    )
    agora = datetime.now(timezone.utc)
    usuario_outra_empresa.created_at = agora
    usuario_outra_empresa.updated_at = agora
    db_session.add(usuario_outra_empresa)
    db_session.flush()

    resposta = client_admin.get(f"/usuarios/{usuario_outra_empresa.id}")
    assert resposta.status_code == 404, resposta.text


def test_operador_recebe_403_em_rota_restrita_a_admin(client_operador: TestClient, empresa: Empresa) -> None:
    payload = {
        "empresaId": empresa.id,
        "codigoInterno": f"tentativa-{uuid.uuid4().hex[:8]}",
        "nome": "Tentativa Bloqueada",
        "email": f"tentativa-{uuid.uuid4().hex[:8]}@teste.taskfloww.local",
        "perfilBase": "operador",
        "acessoSistema": True,
    }
    resposta = client_operador.post("/usuarios", json=payload)
    assert resposta.status_code == 403, resposta.text


EMPRESA_ID_PROVA_COMMIT = "00000000-0000-4000-8000-000000000001"
EMPRESA_CODIGO_PROVA_COMMIT = "empresa-prova-commit-fixa"


def test_commit_nao_vaza_a(db_session: Session) -> None:
    """Cria um usuário com chave única fixa (mesmo empresa_id + codigo_interno + email) via
    service com commit() real, de forma totalmente independente do teste `_b` abaixo — não
    usa a fixture `empresa` (que gera um ID novo por teste), justamente pra garantir que os
    dois testes disputem a MESMA chave. Se o isolamento por savepoint falhar, um dos dois
    (não importa qual roda primeiro, nem se rodam sozinhos ou juntos) vê um conflito de
    unicidade ao tentar inserir a mesma empresa/usuário que o outro já commitou de verdade."""
    _criar_usuario_chave_fixa(db_session)


def test_commit_nao_vaza_b(db_session: Session) -> None:
    _criar_usuario_chave_fixa(db_session)


def _criar_usuario_chave_fixa(db_session: Session) -> None:
    agora = datetime.now(timezone.utc)
    empresa_fixa = Empresa(
        id=EMPRESA_ID_PROVA_COMMIT,
        nome="Empresa Prova Commit",
        documento=None,
        codigo_interno=EMPRESA_CODIGO_PROVA_COMMIT,
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(empresa_fixa)
    db_session.flush()

    service = UsuarioService()
    payload = UsuarioCreate(
        empresaId=empresa_fixa.id,
        codigoInterno="prova-commit-nao-vaza",
        nome="Prova Commit",
        email="prova-commit-nao-vaza@teste.taskfloww.local",
        perfilBase="operador",
        acessoSistema=True,
    )
    service.create_usuario(db_session, payload, actor_usuario_id=None)
