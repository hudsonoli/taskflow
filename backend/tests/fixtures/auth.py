"""Fixtures de autenticação: tokens diretos (rápidos, pra testes de autorização) e um
TestClient novo por perfil (admin/gestor/operador), cada um com sua própria instância — sem
Authorization compartilhado ou mutado entre eles."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.usuario import Usuario


@pytest.fixture()
def token_admin(usuario_admin: Usuario) -> str:
    return create_access_token(sub=usuario_admin.id, empresa_id=usuario_admin.empresa_id, perfil_base="admin")


@pytest.fixture()
def token_gestor(usuario_gestor: Usuario) -> str:
    return create_access_token(sub=usuario_gestor.id, empresa_id=usuario_gestor.empresa_id, perfil_base="gestor")


@pytest.fixture()
def token_operador(usuario_operador: Usuario) -> str:
    return create_access_token(sub=usuario_operador.id, empresa_id=usuario_operador.empresa_id, perfil_base="operador")


@pytest.fixture()
def client_admin(app, token_admin: str) -> TestClient:
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token_admin}"
    return cliente


@pytest.fixture()
def client_gestor(app, token_gestor: str) -> TestClient:
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token_gestor}"
    return cliente


@pytest.fixture()
def client_operador(app, token_operador: str) -> TestClient:
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token_operador}"
    return cliente
