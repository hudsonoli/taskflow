"""Wrappers finos sobre TestClient — só pra não repetir `headers={"Authorization": ...}` em
todo teste. Nenhuma lógica além de montar o header opcional."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from httpx import Response


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def get(client: TestClient, url: str, *, token: str | None = None, **kwargs: Any) -> Response:
    return client.get(url, headers=_headers(token), **kwargs)


def post_json(client: TestClient, url: str, json: dict[str, Any], *, token: str | None = None, **kwargs: Any) -> Response:
    return client.post(url, json=json, headers=_headers(token), **kwargs)


def patch_json(client: TestClient, url: str, json: dict[str, Any], *, token: str | None = None, **kwargs: Any) -> Response:
    return client.patch(url, json=json, headers=_headers(token), **kwargs)
