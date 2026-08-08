"""Helpers de autenticação pros testes: login real via API (fluxo completo, não só o token
direto das fixtures em tests/fixtures/auth.py)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from httpx import Response

from app.models.empresa import Empresa
from app.models.usuario import Usuario


def login_via_api(client: TestClient, *, empresa: Empresa, usuario: Usuario, senha: str) -> Response:
    return client.post(
        "/auth/login",
        json={"empresaCodigo": empresa.codigo_interno, "email": usuario.email, "senha": senha},
    )
