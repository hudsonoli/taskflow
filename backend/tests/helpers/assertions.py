"""Assertions pro formato de erro padronizado da API — ver docs/padrao-arquivamento.md."""

from __future__ import annotations

from httpx import Response


def assert_erro_simples(response: Response, status_code: int, mensagem_contem: str | None = None) -> None:
    assert response.status_code == status_code, response.text
    if mensagem_contem is not None:
        detail = response.json().get("detail")
        assert isinstance(detail, str) and mensagem_contem in detail, response.text


def assert_conflito_arquivado(response: Response, *, code: str) -> dict:
    """Confirma o formato {"detail": {"code": ..., "message": ..., "<entidade>ArquivadoId": ...}}
    documentado em docs/padrao-arquivamento.md. Retorna o corpo de `detail` pra asserts extras."""
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == code, detail
    assert "message" in detail
    return detail
