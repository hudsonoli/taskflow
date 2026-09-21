from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PermissaoEfeito = Literal["conceder", "negar"]


# extra="forbid": enviar um campo desconhecido (ex. "efetivo", que é calculado, nunca
# aceito do cliente) devolve 422 em vez de ser ignorado em silêncio — mesmo padrão de
# UsuarioCreate/UsuarioUpdate desde a Fase 2G.10C-B.
class UsuarioPermissaoOverrideWrite(BaseModel):
    efeito: PermissaoEfeito
    motivo: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")


class PermissaoAdminItem(BaseModel):
    """Uma linha da visão administrativa (GET /usuarios/{id}/permissoes) — uma por chave em
    TODAS_AS_PERMISSOES, não só as que têm override."""

    permissao: str
    modulo: str
    label: str
    herdado: bool
    override: PermissaoEfeito | None
    efetivo: bool

    model_config = ConfigDict(from_attributes=True)
