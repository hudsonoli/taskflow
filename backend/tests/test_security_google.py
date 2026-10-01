"""Testes unitários de `verify_google_id_token` (app/core/security.py) — a camada que
delega a verificação real (assinatura, issuer, audience, expiração) à biblioteca oficial
`google-auth`. Nunca chamamos a internet aqui: `google.oauth2.id_token.verify_oauth2_token`
é monkeypatchado em todo teste — o que validamos é que ESTE wrapper (a) passa o client_id
certo como audience, (b) nunca deixa a exceção interna da biblioteca escapar sem virar
`AuthTokenError`, e (c) falha explicitamente sem `GOOGLE_OAUTH_CLIENT_ID` configurado."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.security import AuthConfigurationError, AuthTokenError, verify_google_id_token


def _settings(**overrides) -> Settings:
    base = {
        "auth_secret_key": "segredo-de-teste-bem-grande-o-suficiente",
        "google_oauth_client_id": "client-id-de-teste.apps.googleusercontent.com",
    }
    base.update(overrides)
    return Settings(**base)


def test_verify_google_id_token_sucesso_devolve_claims(monkeypatch):
    claims_esperadas = {"sub": "abc123", "email": "pessoa@empresa.com", "email_verified": True}
    capturado = {}

    def fake_verify(token, request, audience):
        capturado["token"] = token
        capturado["audience"] = audience
        return claims_esperadas

    monkeypatch.setattr("app.core.security.google_id_token.verify_oauth2_token", fake_verify)

    resultado = verify_google_id_token("token-qualquer", settings=_settings())

    assert resultado == claims_esperadas
    assert capturado["token"] == "token-qualquer"
    assert capturado["audience"] == "client-id-de-teste.apps.googleusercontent.com"


def test_verify_google_id_token_assinatura_invalida_vira_auth_token_error(monkeypatch):
    def fake_verify(token, request, audience):
        raise ValueError("Token has invalid signature")

    monkeypatch.setattr("app.core.security.google_id_token.verify_oauth2_token", fake_verify)

    with pytest.raises(AuthTokenError):
        verify_google_id_token("token-invalido", settings=_settings())


def test_verify_google_id_token_audience_invalida_vira_auth_token_error(monkeypatch):
    def fake_verify(token, request, audience):
        raise ValueError("Token has wrong audience")

    monkeypatch.setattr("app.core.security.google_id_token.verify_oauth2_token", fake_verify)

    with pytest.raises(AuthTokenError):
        verify_google_id_token("token-audience-errada", settings=_settings())


def test_verify_google_id_token_expirado_vira_auth_token_error(monkeypatch):
    def fake_verify(token, request, audience):
        raise ValueError("Token expired")

    monkeypatch.setattr("app.core.security.google_id_token.verify_oauth2_token", fake_verify)

    with pytest.raises(AuthTokenError):
        verify_google_id_token("token-expirado", settings=_settings())


def test_verify_google_id_token_sem_client_id_configurado_falha_explicito():
    with pytest.raises(AuthConfigurationError):
        verify_google_id_token("token-qualquer", settings=_settings(google_oauth_client_id=None))
