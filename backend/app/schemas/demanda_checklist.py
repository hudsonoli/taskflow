from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _texto_nao_pode_ser_so_espaco(value: str) -> str:
    limpo = value.strip()
    if not limpo:
        raise ValueError("texto não pode conter apenas espaços")
    return limpo


class DemandaChecklistItemCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("texto")
    @classmethod
    def texto_valido(cls, value: str) -> str:
        return _texto_nao_pode_ser_so_espaco(value)


# Um único endpoint de edição cobre texto e conclusão — a UI atual não precisa de mais que
# isso, e dois campos opcionais evitam multiplicar rota (ver instrução da Fase 2E.3, item 9:
# "não criar dezenas de endpoints se um desenho mais simples atender").
class DemandaChecklistItemUpdate(BaseModel):
    texto: str | None = Field(default=None, min_length=1, max_length=500)
    concluido: bool | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("texto")
    @classmethod
    def texto_valido(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _texto_nao_pode_ser_so_espaco(value)


class DemandaChecklistReordenar(BaseModel):
    """Lista completa de ids na nova ordem — o service valida que é exatamente o mesmo
    conjunto de itens já existentes da Demanda, nem a mais nem a menos."""

    item_ids: list[UUID] = Field(alias="itemIds", min_length=1)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DemandaChecklistItemRead(BaseModel):
    id: UUID
    demanda_id: UUID = Field(alias="demandaId")
    texto: str
    ordem: int
    concluido: bool
    concluido_em: datetime | None = Field(default=None, alias="concluidoEm")
    concluido_por_usuario_id: UUID | None = Field(default=None, alias="concluidoPorUsuarioId")
    criado_por_usuario_id: UUID | None = Field(default=None, alias="criadoPorUsuarioId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("concluido_em", "created_at", "updated_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
