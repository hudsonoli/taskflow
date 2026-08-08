from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from jwt import ExpiredSignatureError, InvalidAlgorithmError, InvalidSignatureError, InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import Settings, get_settings

password_hash = PasswordHash.recommended()
REQUIRED_ACCESS_TOKEN_CLAIMS = {"sub", "empresa_id", "perfil_base", "iat", "exp", "tipo"}
ALLOWED_PERFIS_BASE = {"admin", "gestor", "operador"}


class AuthConfigurationError(RuntimeError):
    pass


class AuthTokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("Senha não pode ser vazia")
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    if not isinstance(password, str) or not password:
        return False
    if not isinstance(hashed_password, str) or not hashed_password:
        return False
    try:
        return password_hash.verify(password, hashed_password)
    except Exception:
        return False


def create_access_token(
    *,
    sub: str,
    empresa_id: str,
    perfil_base: str,
    settings: Settings | None = None,
    now: datetime | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    resolved_settings = settings or get_settings()
    secret = _require_auth_secret(resolved_settings)
    issued_at = _ensure_utc(now or datetime.now(timezone.utc))
    expiration = issued_at + (expires_delta or timedelta(minutes=resolved_settings.auth_access_token_expire_minutes))

    _validate_uuid_claim("sub", sub)
    _validate_uuid_claim("empresa_id", empresa_id)
    _validate_perfil_base(perfil_base)

    payload = {
        "sub": sub,
        "empresa_id": empresa_id,
        "perfil_base": perfil_base,
        "iat": issued_at,
        "exp": expiration,
        "tipo": "access",
    }
    return jwt.encode(payload, secret, algorithm=resolved_settings.auth_algorithm)


def decode_access_token(
    token: str,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(token, str) or not token:
        raise AuthTokenError("Token inválido")

    resolved_settings = settings or get_settings()
    secret = _require_auth_secret(resolved_settings)
    options: dict[str, Any] = {"require": sorted(REQUIRED_ACCESS_TOKEN_CLAIMS)}
    if now is not None:
        options["verify_exp"] = False

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[resolved_settings.auth_algorithm],
            options=options,
        )
    except ExpiredSignatureError as exc:
        raise AuthTokenError("Token expirado") from exc
    except InvalidAlgorithmError as exc:
        raise AuthTokenError("Algoritmo do token inválido") from exc
    except InvalidSignatureError as exc:
        raise AuthTokenError("Assinatura do token inválida") from exc
    except InvalidTokenError as exc:
        raise AuthTokenError("Token inválido") from exc

    missing_claims = REQUIRED_ACCESS_TOKEN_CLAIMS - set(payload)
    if missing_claims:
        raise AuthTokenError("Claims obrigatórias ausentes")

    if now is not None:
        current_time = _ensure_utc(now).timestamp()
        exp = _claim_timestamp(payload["exp"])
        if exp <= current_time:
            raise AuthTokenError("Token expirado")

    if payload.get("tipo") != "access":
        raise AuthTokenError("Tipo do token inválido")

    _validate_uuid_claim("sub", payload.get("sub"))
    _validate_uuid_claim("empresa_id", payload.get("empresa_id"))
    _validate_perfil_base(payload.get("perfil_base"))

    return payload


def _require_auth_secret(settings: Settings) -> str:
    if not settings.auth_secret_key:
        raise AuthConfigurationError("AUTH_SECRET_KEY não configurado")
    return settings.auth_secret_key


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("datetime deve possuir timezone")
    return value.astimezone(timezone.utc)


def _validate_uuid_claim(name: str, value: Any) -> None:
    if not isinstance(value, str):
        raise AuthTokenError(f"Claim {name} inválida")
    try:
        UUID(value)
    except (TypeError, ValueError) as exc:
        raise AuthTokenError(f"Claim {name} inválida") from exc


def _validate_perfil_base(value: Any) -> None:
    if value not in ALLOWED_PERFIS_BASE:
        raise AuthTokenError("perfil_base inválido")


def _claim_timestamp(value: Any) -> float:
    if isinstance(value, datetime):
        return _ensure_utc(value).timestamp()
    if isinstance(value, int | float):
        return float(value)
    raise AuthTokenError("Claim exp inválida")
