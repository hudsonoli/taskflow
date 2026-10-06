import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Tema = Literal["claro", "escuro"]
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _normalizar_hex(value: str | None) -> str | None:
    if value is None:
        return None
    if not _HEX.match(value):
        raise ValueError("Cor inválida: use o formato #RRGGBB")
    return value.lower()


class PersonalizacaoRead(BaseModel):
    """Identidade visual da empresa. Mesmo shape para a leitura administrativa e para a pública
    (usada antes do login): nada além do necessário para renderizar — sem ids, sem paths do
    servidor, sem timestamps internos."""

    cor_primaria: str = Field(alias="corPrimaria")
    cor_secundaria: str = Field(alias="corSecundaria")
    tema: Tema
    logo_disponivel: bool = Field(alias="logoDisponivel")
    # Muda a cada troca de logo (derivada do nome físico gerado pelo sistema) — quebra o cache do
    # navegador sem expor o caminho. `None` sem logo personalizado.
    logo_versao: str | None = Field(default=None, alias="logoVersao")
    # `True` quando nada foi personalizado (aparência original do TaskFloww).
    padrao: bool

    model_config = ConfigDict(populate_by_name=True)


class PersonalizacaoUpdate(BaseModel):
    """Alteração parcial: só os campos enviados mudam. Só duas cores são configuráveis — fundo,
    superfície, texto, borda e estados derivam do design system (contraste garantido)."""

    cor_primaria: str | None = Field(default=None, alias="corPrimaria")
    cor_secundaria: str | None = Field(default=None, alias="corSecundaria")
    tema: Tema | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("cor_primaria", "cor_secundaria")
    @classmethod
    def validar_hex(cls, value: str | None) -> str | None:
        return _normalizar_hex(value)
