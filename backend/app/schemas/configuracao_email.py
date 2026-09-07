from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Sem biblioteca de validação de e-mail (`email-validator`/`EmailStr`) — o projeto não usa
# nenhuma hoje (Usuario.email/Cliente.email são `str` puro, ver app/schemas/usuario.py) e não
# há justificativa pra introduzir uma dependência nova só pra isto (Fase 2G.7A, item 11).
# Regex propositalmente simples: só recusa o obviamente inválido (sem "@", sem domínio com
# ponto) — não tenta validar RFC 5322 inteira.
_EMAIL_FORMATO_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalizar_texto_opcional(value: str | None) -> str | None:
    """Trim + `"" -> None` — mesmo padrão de `descricao`/`motivoArquivamento` em outros
    domínios (nunca grava string vazia; `CHECK` do banco também recusaria smtp_host/
    remetente_email vazios-não-nulos). Não se aplica a `smtp_senha` — ver validador dedicado
    abaixo, que REJEITA "" em vez de normalizar (semântica diferente e deliberada)."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class ConfiguracaoEmailUpdate(BaseModel):
    """PATCH do singleton — nunca aceita `id`/`empresaId`/`createdAt`/`updatedAt`/
    `smtpSenhaConfigurada`/`smtpSenhaCriptografada` (não são campos declarados aqui, e
    `extra="forbid"` rejeita qualquer um deles com 422 automaticamente).

    ## Semântica de `smtp_senha` — três estados, não dois

    - **Omitido** (chave ausente do JSON): preserva o ciphertext atual. Detectado via
      `model_dump(exclude_unset=True)` em `ConfiguracaoEmailService` — nunca por comparar
      contra `None`, que confundiria com o próximo caso.
    - **`null`**: remove o segredo armazenado (limpa `smtp_senha_criptografada`).
    - **string não vazia**: substitui por um novo segredo, criptografado antes de gravar.
    - **`""`** (string vazia): estado ambíguo — poderia significar "esqueci de preencher" ou
      "quero limpar" — REJEITADO com 422 em vez de adivinhar a intenção (ver validador
      abaixo). Quem quer limpar deve enviar `null` explicitamente.
    """

    smtp_host: str | None = Field(default=None, alias="smtpHost", max_length=255)
    smtp_port: int | None = Field(default=None, alias="smtpPort", ge=1, le=65535)
    smtp_usuario: str | None = Field(default=None, alias="smtpUsuario", max_length=255)
    smtp_senha: str | None = Field(default=None, alias="smtpSenha", max_length=1000)
    remetente_email: str | None = Field(default=None, alias="remetenteEmail", max_length=255)
    remetente_nome: str | None = Field(default=None, alias="remetenteNome", max_length=255)
    usar_tls: bool | None = Field(default=None, alias="usarTls")
    usar_ssl: bool | None = Field(default=None, alias="usarSsl")
    ativo: bool | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("smtp_senha")
    @classmethod
    def validar_smtp_senha_nao_vazia(cls, value: str | None) -> str | None:
        # `validate_default=False` (padrão do Pydantic v2) garante que isto só roda quando o
        # campo foi de fato enviado no payload — omitido nunca cai aqui.
        if value is not None and value.strip() == "":
            raise ValueError(
                'smtpSenha não pode ser uma string vazia — omita o campo para manter a senha '
                'atual, ou envie null para removê-la explicitamente.'
            )
        return value

    @field_validator("smtp_host", "smtp_usuario", "remetente_nome")
    @classmethod
    def normalizar_textos_opcionais(cls, value: str | None) -> str | None:
        return _normalizar_texto_opcional(value)

    @field_validator("remetente_email")
    @classmethod
    def normalizar_e_validar_remetente_email(cls, value: str | None) -> str | None:
        normalizado = _normalizar_texto_opcional(value)
        if normalizado is not None and not _EMAIL_FORMATO_REGEX.match(normalizado):
            raise ValueError("remetenteEmail não tem um formato de e-mail válido")
        return normalizado

    @model_validator(mode="after")
    def validar_tls_ssl_mutuamente_exclusivos(self) -> "ConfiguracaoEmailUpdate":
        # Só cobre o caso óbvio (os dois `True` NO MESMO payload) — o caso onde só um dos
        # dois é enviado e conflita com o valor já persistido do outro é responsabilidade de
        # ConfiguracaoEmailService, que valida o ESTADO FINAL após o merge (única fonte que
        # conhece o valor atual do campo não enviado).
        if self.usar_tls is True and self.usar_ssl is True:
            raise ValueError("usarTls e usarSsl não podem estar ativos ao mesmo tempo")
        return self


class ConfiguracaoEmailRead(BaseModel):
    """Nunca inclui `smtpSenha`/`smtpSenhaCriptografada`/ciphertext/chave — só o booleano
    `smtpSenhaConfigurada`. Sem `empresaId`: a configuração é implicitamente tenant-scoped
    (resolvida sempre por `current_user.empresa_id`, nunca por parâmetro), e nenhum outro
    consumidor precisa dele — decisão deliberada da Fase 2G.7B1, não uma omissão.

    `id`/`createdAt`/`updatedAt` são `None` quando ainda não existe registro físico (GET
    antes do primeiro PATCH) — ver docstring de `ConfiguracaoEmailService.get_ou_default`.
    """

    id: UUID | None = None
    smtp_host: str | None = Field(default=None, alias="smtpHost")
    smtp_port: int | None = Field(default=None, alias="smtpPort")
    smtp_usuario: str | None = Field(default=None, alias="smtpUsuario")
    smtp_senha_configurada: bool = Field(alias="smtpSenhaConfigurada")
    remetente_email: str | None = Field(default=None, alias="remetenteEmail")
    remetente_nome: str | None = Field(default=None, alias="remetenteNome")
    usar_tls: bool = Field(alias="usarTls")
    usar_ssl: bool = Field(alias="usarSsl")
    ativo: bool
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return _ensure_timezone_aware(value)


# Motivos finitos e seguros do teste de conexão (Fase 2G.7A, item 24) — nunca uma exceção
# crua, nunca o ciphertext/senha, nunca IP/hostname resolvido internamente.
ConfiguracaoEmailTesteMotivo = str  # documentado em ConfiguracaoEmailTesteResultado.motivo


class ConfiguracaoEmailTesteResultado(BaseModel):
    sucesso: bool
    motivo: str
    mensagem: str

    model_config = ConfigDict(populate_by_name=True)
