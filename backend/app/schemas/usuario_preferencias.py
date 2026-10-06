from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TemaPreferencia = Literal["claro", "escuro", "sistema"]


class UsuarioPreferenciasUpdate(BaseModel):
    """Preferências do PRÓPRIO usuário (a identidade vem do token — nenhum usuarioId é aceito).
    `tema` é obrigatório no corpo, mas aceita `null`: "usar o padrão da empresa"."""

    tema: TemaPreferencia | None = Field()

    model_config = ConfigDict(extra="forbid")


class UsuarioPreferenciasRead(BaseModel):
    tema_preferencia: TemaPreferencia | None = Field(alias="temaPreferencia")

    model_config = ConfigDict(populate_by_name=True)
