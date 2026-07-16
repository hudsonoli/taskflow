from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    AuthConfigurationError,
    AuthTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def settings(secret: str | None = "test-secret", algorithm: str = "HS256") -> Settings:
    return Settings(
        auth_secret_key=secret,
        auth_algorithm=algorithm,
        auth_access_token_expire_minutes=30,
    )


def token_subjects():
    return {
        "sub": str(uuid4()),
        "empresa_id": str(uuid4()),
        "perfil_base": "admin",
    }


def test_hash_password_does_not_store_plain_password():
    password = "senha-super-segura"

    hashed = hash_password(password)

    assert hashed != password
    assert password not in hashed


def test_verify_password_accepts_correct_password():
    hashed = hash_password("senha-correta")

    assert verify_password("senha-correta", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("senha-correta")

    assert verify_password("senha-errada", hashed) is False


def test_same_password_generates_different_hashes():
    first = hash_password("senha-repetida")
    second = hash_password("senha-repetida")

    assert first != second


def test_hash_empty_password_raises_controlled_error():
    with pytest.raises(ValueError, match="Senha não pode ser vazia"):
        hash_password("")


def test_verify_empty_password_or_hash_returns_false():
    assert verify_password("", hash_password("senha")) is False
    assert verify_password("senha", "") is False
    assert verify_password("senha", "hash-invalido") is False


def test_create_and_decode_valid_access_token():
    claims = token_subjects()

    token = create_access_token(**claims, settings=settings())
    decoded = decode_access_token(token, settings=settings())

    assert decoded["sub"] == claims["sub"]
    assert decoded["empresa_id"] == claims["empresa_id"]
    assert decoded["perfil_base"] == "admin"
    assert decoded["tipo"] == "access"
    assert decoded["iat"]
    assert decoded["exp"]


def test_access_token_has_no_sensitive_claims():
    token = create_access_token(**token_subjects(), settings=settings())
    decoded = decode_access_token(token, settings=settings())

    assert set(decoded) == {"sub", "empresa_id", "perfil_base", "iat", "exp", "tipo"}
    assert "email" not in decoded
    assert "senha" not in decoded
    assert "senha_hash" not in decoded
    assert "token" not in decoded


def test_expired_token_is_rejected():
    token = create_access_token(
        **token_subjects(),
        settings=settings(),
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(AuthTokenError, match="Token expirado"):
        decode_access_token(token, settings=settings())


def test_invalid_signature_is_rejected():
    token = create_access_token(**token_subjects(), settings=settings("secret-a"))

    with pytest.raises(AuthTokenError, match="Assinatura do token inválida"):
        decode_access_token(token, settings=settings("secret-b"))


def test_invalid_algorithm_is_rejected():
    claims = token_subjects()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            **claims,
            "iat": now,
            "exp": now + timedelta(minutes=30),
            "tipo": "access",
        },
        "test-secret",
        algorithm="HS512",
    )

    with pytest.raises(AuthTokenError, match="Algoritmo do token inválido"):
        decode_access_token(token, settings=settings(algorithm="HS256"))


def test_invalid_type_is_rejected():
    claims = token_subjects()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            **claims,
            "iat": now,
            "exp": now + timedelta(minutes=30),
            "tipo": "refresh",
        },
        "test-secret",
        algorithm="HS256",
    )

    with pytest.raises(AuthTokenError, match="Tipo do token inválido"):
        decode_access_token(token, settings=settings())


@pytest.mark.parametrize("missing_claim", ["sub", "empresa_id", "perfil_base", "iat", "exp", "tipo"])
def test_missing_required_claim_is_rejected(missing_claim):
    claims = token_subjects()
    now = datetime.now(timezone.utc)
    payload = {
        **claims,
        "iat": now,
        "exp": now + timedelta(minutes=30),
        "tipo": "access",
    }
    payload.pop(missing_claim)
    token = jwt.encode(payload, "test-secret", algorithm="HS256")

    with pytest.raises(AuthTokenError, match="Token inválido|Claims obrigatórias ausentes"):
        decode_access_token(token, settings=settings())


def test_invalid_sub_is_rejected_on_create():
    claims = token_subjects()
    claims["sub"] = "usuario-invalido"

    with pytest.raises(AuthTokenError, match="Claim sub inválida"):
        create_access_token(**claims, settings=settings())


def test_invalid_empresa_id_is_rejected_on_create():
    claims = token_subjects()
    claims["empresa_id"] = "empresa-invalida"

    with pytest.raises(AuthTokenError, match="Claim empresa_id inválida"):
        create_access_token(**claims, settings=settings())


def test_missing_secret_on_create_raises_controlled_error():
    with pytest.raises(AuthConfigurationError, match="AUTH_SECRET_KEY não configurado"):
        create_access_token(**token_subjects(), settings=settings(secret=None))


def test_missing_secret_on_decode_raises_controlled_error():
    token = create_access_token(**token_subjects(), settings=settings())

    with pytest.raises(AuthConfigurationError, match="AUTH_SECRET_KEY não configurado"):
        decode_access_token(token, settings=settings(secret=None))


def test_naive_datetime_is_rejected_on_create():
    with pytest.raises(ValueError, match="datetime deve possuir timezone"):
        create_access_token(**token_subjects(), settings=settings(), now=datetime(2026, 7, 15, 12, 0, 0))
