"""Parâmetros de filtro de listagem com vários valores (CSV) — usados pelos filtros avançados de
Arquivos e Tráfego. Regra única para todos: segmentos vazios são descartados, um valor inválido é 422
(nunca ignorado em silêncio) e há um teto de valores por filtro (a query nunca recebe uma lista sem limite)."""

from collections.abc import Collection
from uuid import UUID

from fastapi import HTTPException, status

MAX_VALORES_POR_FILTRO = 50


def _segmentos(raw: str | None, campo: str) -> list[str]:
    if raw is None:
        return []
    segmentos = [segmento.strip() for segmento in raw.split(",") if segmento.strip()]
    if len(segmentos) > MAX_VALORES_POR_FILTRO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{campo} aceita no máximo {MAX_VALORES_POR_FILTRO} valores",
        )
    return segmentos


def parse_csv_uuids(raw: str | None, campo: str) -> list[str] | None:
    """CSV de UUIDs → lista (ordem preservada, sem repetição); `None` se não há valor."""
    valores: list[str] = []
    for segmento in _segmentos(raw, campo):
        try:
            UUID(segmento)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{campo} inválido: '{segmento}' não é um UUID",
            ) from exc
        if segmento not in valores:
            valores.append(segmento)
    return valores or None


def parse_csv_enum(raw: str | None, campo: str, permitidos: Collection[str]) -> list[str] | None:
    """CSV de valores de uma enumeração fechada → lista; valor fora de `permitidos` é 422."""
    valores: list[str] = []
    for segmento in _segmentos(raw, campo):
        if segmento not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{campo} inválido: '{segmento}'",
            )
        if segmento not in valores:
            valores.append(segmento)
    return valores or None
