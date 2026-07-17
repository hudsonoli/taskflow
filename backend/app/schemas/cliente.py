from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.cliente import ClienteStatus, ClienteTipoPessoa


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def validate_documento_for_tipo(documento: str | None, tipo_pessoa: ClienteTipoPessoa | None) -> None:
    if documento is None:
        return
    if not documento.isdigit():
        raise ValueError("documento deve conter apenas dígitos")
    if tipo_pessoa == ClienteTipoPessoa.FISICA and len(documento) != 11:
        raise ValueError("documento de pessoa física deve conter 11 dígitos")
    if tipo_pessoa == ClienteTipoPessoa.JURIDICA and len(documento) != 14:
        raise ValueError("documento de pessoa jurídica deve conter 14 dígitos")
    if tipo_pessoa is None and len(documento) not in {11, 14}:
        raise ValueError("documento deve conter 11 ou 14 dígitos")


class ClienteBase(BaseModel):
    agencia_id: UUID | None = Field(default=None, alias="agenciaId")
    codigo_interno: str = Field(alias="codigoInterno", min_length=1, max_length=64)
    tipo_pessoa: ClienteTipoPessoa = Field(alias="tipoPessoa")
    documento: str | None = Field(default=None, min_length=11, max_length=14)
    razao_social: str | None = Field(default=None, alias="razaoSocial", max_length=255)
    nome_fantasia: str | None = Field(default=None, alias="nomeFantasia", max_length=255)
    nome: str | None = Field(default=None, max_length=255)
    sigla: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    telefone: str | None = Field(default=None, max_length=32)
    celular: str | None = Field(default=None, max_length=32)
    site: str | None = Field(default=None, max_length=255)
    codigo_externo: str | None = Field(default=None, alias="codigoExterno", max_length=128)
    observacoes: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator(
        "codigo_interno",
        "documento",
        "razao_social",
        "nome_fantasia",
        "nome",
        "sigla",
        "email",
        "telefone",
        "celular",
        "site",
        "codigo_externo",
        "observacoes",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def validate_cliente_domain(self):
        validate_documento_for_tipo(self.documento, self.tipo_pessoa)
        if self.tipo_pessoa == ClienteTipoPessoa.FISICA and not self.nome:
            raise ValueError("nome é obrigatório para pessoa física")
        if self.tipo_pessoa == ClienteTipoPessoa.JURIDICA and not (self.razao_social or self.nome_fantasia):
            raise ValueError("razão social ou nome fantasia é obrigatório para pessoa jurídica")
        return self


class ClienteCreate(ClienteBase):
    empresa_id: UUID = Field(alias="empresaId")
    status: ClienteStatus = ClienteStatus.ATIVO

    @model_validator(mode="after")
    def validate_initial_status(self):
        if self.status != ClienteStatus.ATIVO:
            raise ValueError("Cliente deve ser criado com status ativo")
        return self


class ClienteUpdate(BaseModel):
    agencia_id: UUID | None = Field(default=None, alias="agenciaId")
    codigo_interno: str | None = Field(default=None, alias="codigoInterno", min_length=1, max_length=64)
    tipo_pessoa: ClienteTipoPessoa | None = Field(default=None, alias="tipoPessoa")
    documento: str | None = Field(default=None, min_length=11, max_length=14)
    razao_social: str | None = Field(default=None, alias="razaoSocial", max_length=255)
    nome_fantasia: str | None = Field(default=None, alias="nomeFantasia", max_length=255)
    nome: str | None = Field(default=None, max_length=255)
    sigla: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    telefone: str | None = Field(default=None, max_length=32)
    celular: str | None = Field(default=None, max_length=32)
    site: str | None = Field(default=None, max_length=255)
    codigo_externo: str | None = Field(default=None, alias="codigoExterno", max_length=128)
    observacoes: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator(
        "codigo_interno",
        "documento",
        "razao_social",
        "nome_fantasia",
        "nome",
        "sigla",
        "email",
        "telefone",
        "celular",
        "site",
        "codigo_externo",
        "observacoes",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def validate_partial_domain(self):
        validate_documento_for_tipo(self.documento, self.tipo_pessoa)
        if self.tipo_pessoa == ClienteTipoPessoa.FISICA and self.nome is not None and not self.nome:
            raise ValueError("nome é obrigatório para pessoa física")
        if (
            self.tipo_pessoa == ClienteTipoPessoa.JURIDICA
            and self.razao_social is not None
            and self.nome_fantasia is not None
            and not (self.razao_social or self.nome_fantasia)
        ):
            raise ValueError("razão social ou nome fantasia é obrigatório para pessoa jurídica")
        return self


class ClienteResponse(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    agencia_id: UUID | None = Field(default=None, alias="agenciaId")
    codigo_interno: str = Field(alias="codigoInterno")
    tipo_pessoa: ClienteTipoPessoa = Field(alias="tipoPessoa")
    documento: str | None = None
    razao_social: str | None = Field(default=None, alias="razaoSocial")
    nome_fantasia: str | None = Field(default=None, alias="nomeFantasia")
    nome: str | None = None
    sigla: str | None = None
    email: str | None = None
    telefone: str | None = None
    celular: str | None = None
    site: str | None = None
    codigo_externo: str | None = Field(default=None, alias="codigoExterno")
    observacoes: str | None = None
    status: ClienteStatus
    status_alterado_at: datetime | None = Field(default=None, alias="statusAlteradoAt")
    status_alterado_por_usuario_id: UUID | None = Field(default=None, alias="statusAlteradoPorUsuarioId")
    motivo_status: str | None = Field(default=None, alias="motivoStatus")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("status_alterado_at", "created_at", "updated_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)
