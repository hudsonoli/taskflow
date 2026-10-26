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


class DemandaComentarioCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    # @menções ESTRUTURADAS (ids de quem foi escolhido no autocomplete); o servidor revalida tenant, status, acesso e a presença do "@Nome" no texto. Ausente = nenhuma.
    mencoes_usuario_ids: list[UUID] | None = Field(default=None, alias="mencoesUsuarioIds", max_length=50)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("texto")
    @classmethod
    def texto_valido(cls, value: str) -> str:
        return _texto_nao_pode_ser_so_espaco(value)


class DemandaComentarioUpdate(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    # Ausente (None) = não mexer nas menções; lista (inclusive vazia) = o conjunto ATUAL de menções do comentário (novas notificam, removidas somem do estado).
    mencoes_usuario_ids: list[UUID] | None = Field(default=None, alias="mencoesUsuarioIds", max_length=50)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("texto")
    @classmethod
    def texto_valido(cls, value: str) -> str:
        return _texto_nao_pode_ser_so_espaco(value)


class MencaoRead(BaseModel):
    usuario_id: UUID = Field(alias="usuarioId")
    nome: str

    model_config = ConfigDict(populate_by_name=True)


class MencionavelRead(BaseModel):
    """Sugestão do autocomplete: só o necessário para escolher e inserir o token (sem e-mail, telefone ou documento)."""

    id: UUID
    nome: str
    cargo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DemandaComentarioRead(BaseModel):
    id: UUID
    demanda_id: UUID = Field(alias="demandaId")
    autor_usuario_id: UUID | None = Field(default=None, alias="autorUsuarioId")
    # Autor é conta de sistema: para o tenant o id some (None) e esta marca faz a UI mostrar "Sistema".
    autor_sistema: bool = Field(default=False, alias="autorSistema")
    texto: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    editado_em: datetime | None = Field(default=None, alias="editadoEm")
    mencoes: list[MencaoRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "editado_em")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
