"""Contratos da capacidade individual (11B.2D-A): jornada semanal própria e ausências por data. Datas de ausência são DATE no calendário da empresa — nunca o fuso do navegador."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.regra_expediente import PeriodoRead, PeriodoWrite, normalizar_periodos

TipoAusencia = Literal["ferias", "afastamento", "folga", "outro"]
MAX_OBSERVACAO = 500


class JornadaDiaWrite(BaseModel):
    dia_semana: int = Field(alias="diaSemana", ge=0, le=6)
    periodos: list[PeriodoWrite] = Field(default_factory=list)  # lista vazia = dia FECHADO para esta pessoa

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def normalizar(self) -> "JornadaDiaWrite":
        self.periodos = normalizar_periodos(self.periodos, f"dia {self.dia_semana}")
        return self


class JornadaWrite(BaseModel):
    """Grade inteira da jornada personalizada (PUT substitui tudo). Dia não enviado = FECHADO — nunca cai no expediente da empresa; para voltar ao padrão use `DELETE`."""

    dias: list[JornadaDiaWrite] = Field(max_length=7)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def dias_unicos(self) -> "JornadaWrite":
        vistos = [dia.dia_semana for dia in self.dias]
        if len(set(vistos)) != len(vistos):
            raise ValueError("diaSemana repetido na jornada")
        return self


class JornadaDiaRead(BaseModel):
    dia_semana: int = Field(alias="diaSemana")
    periodos: list[PeriodoRead] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class JornadaRead(BaseModel):
    """`personalizada=false`: a pessoa usa o expediente da EMPRESA e `dias` é só a semana recorrente dela (consulta do fallback — nada foi copiado). `personalizada=true`: `dias` é a jornada própria."""

    usuario_id: str = Field(alias="usuarioId")
    personalizada: bool
    dias: list[JornadaDiaRead]
    updated_at: datetime | None = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class AusenciaWrite(BaseModel):
    tipo: TipoAusencia
    inicio: date
    fim: date
    observacao: str | None = Field(default=None, max_length=MAX_OBSERVACAO)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("observacao")
    @classmethod
    def limpar(cls, valor: str | None) -> str | None:
        limpo = valor.strip() if valor else None
        return limpo or None

    @model_validator(mode="after")
    def intervalo(self) -> "AusenciaWrite":
        if self.fim < self.inicio:
            raise ValueError("fim não pode ser anterior ao início")
        return self


class AusenciaUpdate(BaseModel):
    """Edição parcial: só o que for enviado muda (`observacao: null` limpa)."""

    tipo: TipoAusencia | None = None
    inicio: date | None = None
    fim: date | None = None
    observacao: str | None = Field(default=None, max_length=MAX_OBSERVACAO)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("observacao")
    @classmethod
    def limpar(cls, valor: str | None) -> str | None:
        limpo = valor.strip() if valor else None
        return limpo or None


class AusenciaRead(BaseModel):
    id: str
    usuario_id: str = Field(alias="usuarioId")
    tipo: str
    inicio: date
    fim: date
    observacao: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
