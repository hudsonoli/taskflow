from datetime import date, datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

UsuarioPerfilBase = Literal["admin", "gestor", "operador"]
UsuarioStatus = Literal["ativo", "inativo", "bloqueado", "arquivado"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class UsuarioContato(BaseModel):
    id: str
    nome: str
    email: str = ""
    telefone: str = ""
    relacao: str = ""


# Campos de perfil rico compartilhados por Create/Update — nenhum deles inclui
# "is_system_account": essa flag nunca é aceita via API pública, só setada diretamente
# pelo script de seed (ver app/cli/seed_bootstrap.py).
class UsuarioPerfilFields(BaseModel):
    telefone: str | None = Field(default=None, max_length=32)
    cpf: str | None = Field(default=None, max_length=14)
    data_nascimento: date | None = Field(default=None, alias="dataNascimento")
    cep: str | None = Field(default=None, max_length=9)
    bairro: str | None = Field(default=None, max_length=255)
    endereco_completo: str | None = Field(default=None, alias="enderecoCompleto", max_length=500)
    cidade: str | None = Field(default=None, max_length=255)
    uf: str | None = Field(default=None, max_length=2)
    contatos: list[UsuarioContato] | None = None
    # D3-A: `departamentoId` continua sendo o nome no contrato público, mas agora significa
    # o UUID técnico de Departamento — não mais o nome em texto livre. Pydantic rejeita
    # qualquer coisa que não seja UUID, então nome textual vira 422.
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    cargo: str | None = Field(default=None, max_length=255)
    foto_url: str | None = Field(default=None, alias="fotoUrl", max_length=500)
    lider_departamento: bool = Field(default=False, alias="liderDepartamento")
    valor_recebido_mensal_centavos: int | None = Field(default=None, alias="valorRecebidoMensalCentavos")
    horas_trabalho_aproximadas: float | None = Field(default=None, alias="horasTrabalhoAproximadas")
    observacoes: str | None = None
    cor_identificacao: str | None = Field(default=None, alias="corIdentificacao", max_length=32)

    model_config = ConfigDict(populate_by_name=True)


class UsuarioCreate(UsuarioPerfilFields):
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno", min_length=1, max_length=64)
    nome: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    perfil_base: UsuarioPerfilBase = Field(alias="perfilBase")
    acesso_sistema: bool = Field(default=True, alias="acessoSistema")

    model_config = ConfigDict(populate_by_name=True)


class UsuarioUpdate(UsuarioPerfilFields):
    codigo_interno: str | None = Field(default=None, alias="codigoInterno", min_length=1, max_length=64)
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=1, max_length=255)
    perfil_base: UsuarioPerfilBase | None = Field(default=None, alias="perfilBase")
    acesso_sistema: bool | None = Field(default=None, alias="acessoSistema")

    model_config = ConfigDict(populate_by_name=True)


class UsuarioInativar(BaseModel):
    motivo_inativacao: str | None = Field(default=None, alias="motivoInativacao", max_length=500)
    actor_usuario_id: str | None = Field(default=None, alias="actorUsuarioId", max_length=36)

    model_config = ConfigDict(populate_by_name=True)


class UsuarioExcluir(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True)


class UsuarioRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_interno: str = Field(alias="codigoInterno")
    nome: str
    email: str
    perfil_base: UsuarioPerfilBase = Field(alias="perfilBase")
    acesso_sistema: bool = Field(alias="acessoSistema")
    status: UsuarioStatus
    telefone: str | None = None
    cpf: str | None = None
    data_nascimento: date | None = Field(default=None, alias="dataNascimento")
    cep: str | None = None
    bairro: str | None = None
    endereco_completo: str | None = Field(default=None, alias="enderecoCompleto")
    cidade: str | None = None
    uf: str | None = None
    contatos: list[dict[str, Any]] | None = None
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    cargo: str | None = None
    foto_url: str | None = Field(default=None, alias="fotoUrl")
    lider_departamento: bool = Field(default=False, alias="liderDepartamento")
    valor_recebido_mensal_centavos: int | None = Field(default=None, alias="valorRecebidoMensalCentavos")
    horas_trabalho_aproximadas: float | None = Field(default=None, alias="horasTrabalhoAproximadas")
    observacoes: str | None = None
    cor_identificacao: str | None = Field(default=None, alias="corIdentificacao")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    inativado_at: datetime | None = Field(default=None, alias="inativadoAt")
    inativado_por_usuario_id: str | None = Field(default=None, alias="inativadoPorUsuarioId")
    motivo_inativacao: str | None = Field(default=None, alias="motivoInativacao")
    # Arquivamento — ver docs/padrao-arquivamento.md. Guardado como String(36) no banco (ver
    # app/models/usuario.py), tipado UUID aqui só pra validar o formato na borda da API.
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: UsuarioStatus | None = Field(default=None, alias="statusAnteriorArquivamento")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", "inativado_at", "arquivado_at", "restaurado_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


# Projeção mínima para seletores de responsável/membro (GET /usuarios/diretorio) — nunca
# inclui cpf, endereço, data de nascimento, valores financeiros, contatos, observações ou
# email. Exclui sempre a conta de sistema (ver UsuarioRepository.list_diretorio).
class UsuarioDiretorioRead(BaseModel):
    id: UUID
    codigo_interno: str = Field(alias="codigoInterno")
    nome: str
    status: UsuarioStatus
    cargo: str | None = None
    departamento_id: UUID | None = Field(default=None, alias="departamentoId")
    foto_url: str | None = Field(default=None, alias="fotoUrl")
    cor_identificacao: str | None = Field(default=None, alias="corIdentificacao")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
