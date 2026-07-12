from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TimelineItem(BaseModel):
    id: UUID
    tipo: str
    titulo: str
    descricao: str
    usuario_id: str | None = Field(default=None, alias="usuarioId")
    empresa_id: str = Field(alias="empresaId")
    entidade_tipo: str = Field(alias="entidadeTipo")
    entidade_id: str = Field(alias="entidadeId")
    occurred_at: datetime = Field(alias="occurredAt")
    created_at: datetime = Field(alias="createdAt")
    payload: dict[str, Any]
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True)
