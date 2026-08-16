from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def ensure_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class DemandaHistoricoEventoRead(BaseModel):
    """Representação de leitura da timeline — **não** é o `Evento` genérico repassado cru.

    Deliberadamente sem `correlationId`/`causationId`/`metadata`/campos internos de
    auditoria: a UI de uma Demanda não precisa (nem deve) conhecer o envelope de
    rastreabilidade do barramento de eventos, só o que aconteceu, quem fez e quando.
    `dados` é o `payload` do evento como já era publicado — já é seguro para exposição (o
    publisher recusa payload com chave sensível antes mesmo de persistir).
    """

    id: UUID
    tipo: str
    usuario_id: UUID | None = Field(default=None, alias="usuarioId")
    occurred_at: datetime = Field(alias="occurredAt")
    dados: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("occurred_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)
