"""Esforço é trabalho em minutos inteiros, independente de prazo."""
from typing import Annotated

from pydantic import Field

# Limite do INTEGER PostgreSQL. Strict recusa bool, strings e floats, inclusive 1.0.
EsforcoMinutos = Annotated[int, Field(strict=True, ge=0, le=2_147_483_647)]
