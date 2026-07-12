from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TrafegoAgrupamento = Literal["usuario", "departamento"]


class TrafegoAgoraItem(BaseModel):
    sessao_id: UUID = Field(alias="sessaoId")
    empresa_id: str = Field(alias="empresaId")
    agencia_id: str | None = Field(default=None, alias="agenciaId")
    demanda_id: str = Field(alias="demandaId")
    workflow_etapa_id: str | None = Field(default=None, alias="workflowEtapaId")
    usuario_id: str | None = Field(default=None, alias="usuarioId")
    departamento_id: str | None = Field(default=None, alias="departamentoId")
    inicio_em: datetime = Field(alias="inicioEm")
    tempo_decorrido_segundos: int = Field(alias="tempoDecorridoSegundos")
    status: str
    evento_inicio_id: UUID = Field(alias="eventoInicioId")

    model_config = ConfigDict(populate_by_name=True)


class TrafegoCargaItem(BaseModel):
    agrupamento_id: str = Field(alias="agrupamentoId")
    tipo_agrupamento: TrafegoAgrupamento = Field(alias="tipoAgrupamento")
    sessoes_ativas: int = Field(alias="sessoesAtivas")
    demandas_distintas: int = Field(alias="demandasDistintas")
    tempo_ativo_total_segundos: int = Field(alias="tempoAtivoTotalSegundos")
    inicio_mais_antigo: datetime = Field(alias="inicioMaisAntigo")
    ultima_atualizacao: datetime = Field(alias="ultimaAtualizacao")

    model_config = ConfigDict(populate_by_name=True)


class TrafegoResumo(BaseModel):
    sessoes_ativas: int = Field(alias="sessoesAtivas")
    sessoes_encerradas: int = Field(alias="sessoesEncerradas")
    demandas_distintas: int = Field(alias="demandasDistintas")
    usuarios_distintos: int = Field(alias="usuariosDistintos")
    departamentos_distintos: int = Field(alias="departamentosDistintos")
    tempo_operacional_estimado_segundos: int = Field(alias="tempoOperacionalEstimadoSegundos")
    tempo_medio_sessao_segundos: int = Field(alias="tempoMedioSessaoSegundos")
    maior_sessao_segundos: int = Field(alias="maiorSessaoSegundos")
    inicio_periodo: datetime = Field(alias="inicioPeriodo")
    fim_periodo: datetime = Field(alias="fimPeriodo")

    model_config = ConfigDict(populate_by_name=True)
