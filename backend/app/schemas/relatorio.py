from pydantic import BaseModel, ConfigDict, Field


class ContagemAjustesRead(BaseModel):
    ajustes_internos: int = Field(alias="ajustesInternos")
    ajustes_cliente: int = Field(alias="ajustesCliente")
    refacoes: int = Field(alias="refacoes")

    model_config = ConfigDict(populate_by_name=True)


class RelatorioAjustesProjetoRead(BaseModel):
    total: ContagemAjustesRead
    por_demanda: dict[str, ContagemAjustesRead] = Field(alias="porDemanda")

    model_config = ConfigDict(populate_by_name=True)
