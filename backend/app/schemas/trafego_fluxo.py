"""Tráfego V2 — `GET /trafego/operacional/fluxo`: FLUXO POR ETAPA (somente leitura). Contrato de resposta.

O backend é o ÚNICO responsável pela identidade da definição de etapa (`definicaoEtapa.chave`, a MESMA de Gargalos), pelo agrupamento das Demandas atuais nessa definição, pelas métricas e pelos totais. O cliente
nunca calcula chave, nunca normaliza nome e nunca junta Gargalos com Agora. TEMPO OPERACIONAL ≠ TEMPO PESSOAL: nada aqui lê `sessoes_trabalho`; "média em execução" é o tempo que a TAREFA passa nesse estado.

Totais declarados são REAIS (`itensTotal`, `definicoesTotal`, `atual`): os limites afetam só quantos itens/definições são devolvidos, nunca os números.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.trafego_operacional import AtualRead, DefinicaoEtapaRead, EtapaAtualRead, FilaSemEtapaRead, PeriodoRead, RefNomeRead, ResponsavelRead


class _Read(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class FluxoFiltrosRead(_Read):
    departamento_id: str | None = Field(alias="departamentoId")


class FluxoMetricasRead(_Read):
    """WIP ATUAL da definição (mesmo universo e mesma contagem de `fila[]` em Gargalos) + tempo operacional médio em execução no período (mesma conta de `etapas[]` em Gargalos).
    Definição sem WIP agora (só histórico no período): contagens 0 e `maisAntiga*` nulos. `tempoExecucaoMedioSegundos` nulo = SEM amostra (nunca zero inventado)."""

    wip: int
    planejadas: int
    em_execucao: int = Field(alias="emExecucao")
    pausadas: int
    bloqueadas: int
    aguardando_cliente: int = Field(alias="aguardandoCliente")
    # Idade NA ETAPA do item mais antigo (mesma semântica de `FilaEtapaRead.maisAntigaSegundos`); nulo quando não há item atual.
    mais_antiga_segundos: int | None = Field(alias="maisAntigaSegundos")
    mais_antiga_truncada_pela_medicao: bool | None = Field(alias="maisAntigaTruncadaPelaMedicao")
    tempo_execucao_medio_segundos: int | None = Field(alias="tempoExecucaoMedioSegundos")
    n_execucao: int = Field(alias="nExecucao")


class FluxoItemRead(_Read):
    """Uma Demanda ABERTA na etapa atual. Aparece no máximo UMA vez em todo o Fluxo. `definicaoChave` é gerada pelo servidor e é IGUAL a `definicaoEtapa.chave` da definição que contém o item."""

    demanda_id: str = Field(alias="demandaId")
    codigo_referencia: str = Field(alias="codigoReferencia")
    numero_operacional: int = Field(alias="numeroOperacional")
    identificador: str
    titulo: str
    status: str
    projeto: RefNomeRead | None
    cliente: RefNomeRead | None
    etapa_atual: EtapaAtualRead = Field(alias="etapaAtual")
    definicao_chave: str = Field(alias="definicaoChave")
    # ATRIBUIÇÃO atual da etapa (não é executor).
    responsaveis: list[ResponsavelRead]
    inicio_estado_atual: datetime | None = Field(alias="inicioEstadoAtual")
    idade_estado_segundos: int | None = Field(alias="idadeEstadoSegundos")
    prazo: datetime | None
    atrasada: bool


class FluxoDefinicaoRead(_Read):
    definicao_etapa: DefinicaoEtapaRead = Field(alias="definicaoEtapa")
    metricas: FluxoMetricasRead
    # Total REAL de itens elegíveis da definição (== `metricas.wip`); `itensRetornados` ≤ limite por definição.
    itens_total: int = Field(alias="itensTotal")
    itens_retornados: int = Field(alias="itensRetornados")
    truncado: bool
    itens: list[FluxoItemRead]


class TrafegoOperacionalFluxoRead(_Read):
    agora_servidor: datetime = Field(alias="agoraServidor")
    fuso_empresa: str = Field(alias="fusoEmpresa")
    # Período das métricas de TEMPO (padrão 30 dias; máximo 90). WIP e itens são sempre o estado ATUAL.
    periodo: PeriodoRead
    medicao_desde: datetime | None = Field(alias="medicaoDesde")
    cobertura_parcial: bool = Field(alias="coberturaParcial")
    filtros: FluxoFiltrosRead
    # Contagem ATUAL do escopo (inclui Demandas sem etapa atual) — a mesma de `atual` em Gargalos, sobre o mesmo filtro.
    atual: AtualRead
    # Demandas abertas SEM etapa atual: workflow concluído com Demanda aberta (pendência conhecida) e Demanda que nunca teve workflow. Só contagens — não formam coluna.
    sem_etapa: FilaSemEtapaRead = Field(alias="semEtapa")
    definicoes: list[FluxoDefinicaoRead]
    definicoes_total: int = Field(alias="definicoesTotal")
    definicoes_retornadas: int = Field(alias="definicoesRetornadas")
    truncado: bool
    limite_definicoes: int = Field(alias="limiteDefinicoes")
    limite_itens_por_definicao: int = Field(alias="limiteItensPorDefinicao")
