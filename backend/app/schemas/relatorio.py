from datetime import date

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


class ContagemPrioridadeRead(BaseModel):
    baixa: int
    media: int
    alta: int


class ColaboradorContagemRead(BaseModel):
    id: str
    nome: str
    demandas: int


class RelatorioAnaliseProjetoRead(BaseModel):
    """D4A — "Análise de projeto", agregada no servidor sobre TODAS as Demandas do Projeto
    (não arquivadas, no escopo de quem pede) — nunca as 200 mais recentes da empresa."""

    projeto_id: str = Field(alias="projetoId")
    projeto_nome: str = Field(alias="projetoNome")
    total_demandas: int = Field(alias="totalDemandas")
    prioridade: ContagemPrioridadeRead
    tempo_medio_abertura_ate_inicio_dias: float | None = Field(alias="tempoMedioAberturaAteInicioDias")
    tempo_medio_retorno_cliente_dias: float | None = Field(alias="tempoMedioRetornoClienteDias")
    colaboradores: list[ColaboradorContagemRead]

    model_config = ConfigDict(populate_by_name=True)


class RelatorioPecaRead(BaseModel):
    """Uma linha de "Análise de peças": a "peça" é a própria Demanda do Projeto."""

    demanda_id: str = Field(alias="demandaId")
    nome: str
    numero_operacional: int = Field(alias="numeroOperacional")
    redator_nome: str | None = Field(alias="redatorNome")
    tempo_em_pauta_dias: float | None = Field(alias="tempoEmPautaDias")
    em_andamento: bool = Field(alias="emAndamento")

    model_config = ConfigDict(populate_by_name=True)


class RelatorioPecasProjetoRead(BaseModel):
    items: list[RelatorioPecaRead]
    total: int
    limit: int
    offset: int


# --- D4B ------------------------------------------------------------------------------


class RelatorioColaboradorOpcaoRead(BaseModel):
    """Opção do seletor de "Performance de colaborador" — sem o `limit=200` do diretório."""

    id: str
    nome: str


class RelatorioFatiaRead(BaseModel):
    id: str
    label: str
    value: int


class RelatorioPerformanceColaboradorRead(BaseModel):
    colaborador_id: str = Field(alias="colaboradorId")
    colaborador_nome: str = Field(alias="colaboradorNome")
    demandas_entregues: int = Field(alias="demandasEntregues")
    entregues_no_prazo: int = Field(alias="entreguesNoPrazo")
    entregues_em_atraso: int = Field(alias="entreguesEmAtraso")
    participacao_por_etapa: list[RelatorioFatiaRead] = Field(alias="participacaoPorEtapa")

    model_config = ConfigDict(populate_by_name=True)


class RelatorioSegmentoRead(BaseModel):
    series_id: str = Field(alias="seriesId")
    label: str
    value: int

    model_config = ConfigDict(populate_by_name=True)


class RelatorioSerieBarraRead(BaseModel):
    categoria: str
    categoria_id: str = Field(alias="categoriaId")
    segmentos: list[RelatorioSegmentoRead]

    model_config = ConfigDict(populate_by_name=True)


class RelatorioPontoSemanalRead(BaseModel):
    """Segunda-feira (data de calendário no fuso da aplicação) da semana e quantas Demandas
    foram criadas nela."""

    inicio_semana: date = Field(alias="inicioSemana")
    value: int

    model_config = ConfigDict(populate_by_name=True)
