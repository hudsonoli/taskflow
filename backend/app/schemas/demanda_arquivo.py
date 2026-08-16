from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class DemandaArquivoRead(BaseModel):
    """Sem `url`: baixar exige o endpoint autenticado
    (`GET /demandas/{demandaId}/arquivos/{id}/download`), nunca um caminho estático — ver
    docs/pendencias-arquiteturais.md item 9."""

    id: UUID
    demanda_id: UUID = Field(alias="demandaId")
    nome_original: str = Field(alias="nomeOriginal")
    content_type: str | None = Field(default=None, alias="contentType")
    tamanho_bytes: int = Field(alias="tamanhoBytes")
    enviado_por_usuario_id: UUID | None = Field(default=None, alias="enviadoPorUsuarioId")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)
