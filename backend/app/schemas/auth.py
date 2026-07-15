from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AccessTokenClaims(BaseModel):
    sub: UUID
    empresa_id: UUID
    perfil_base: Literal["admin", "gestor", "operador"]
    iat: datetime | int | float
    exp: datetime | int | float
    tipo: Literal["access"] = "access"

    model_config = ConfigDict(populate_by_name=True)


class AccessTokenResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    token_type: Literal["bearer"] = Field(default="bearer", alias="tokenType")

    model_config = ConfigDict(populate_by_name=True)
