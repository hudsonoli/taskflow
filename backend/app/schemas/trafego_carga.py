"""Tráfego V2 — 11B.2B-B: contrato da CARGA semanal (somente leitura). Autoridade: docs/carga-semanal.md e docs/planejamento-etapa.md.

Capacidade vem do expediente da empresa; carga vem da estimativa + janela planejada da etapa. NADA aqui é tempo pessoal nem tempo operacional: não há `horasTrabalhadas*`, ranking nem produtividade.
`ocupacaoPercentual` pode passar de 100 (sobrecarga) e é `null` quando não há denominador confiável. Campos de minutos que dependem do calendário são `null` quando `capacidadeIndisponivel` está preenchido.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class _Read(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class RefRead(_Read):
    id: str
    nome: str


class MetaRead(_Read):
    agora_servidor: datetime = Field(alias="agoraServidor")
    fuso_empresa: str = Field(alias="fusoEmpresa")


class DiaSemanaRead(_Read):
    data: date
    # Minutos NOMINAIS do dia no calendário da empresa (feriado/dia fechado = 0). `null` quando o expediente está desligado.
    minutos_nominais: int | None = Field(alias="minutosNominais")
    # Na semana ATUAL só conta de hoje em diante (`considerado=false` nos dias anteriores). Semana futura: todos os dias.
    considerado: bool


class SemanaRead(_Read):
    inicio: date  # segunda-feira (fuso da empresa)
    fim: date  # domingo
    recorte_hoje: bool = Field(alias="recorteHoje")
    dias: list[DiaSemanaRead]


class CapacidadeRead(_Read):
    # `expediente_desligado`: controle de expediente desligado ou ausente — não existe calendário confiável, então não se inventa capacidade nem distribuição semanal.
    capacidade_indisponivel: str | None = Field(alias="capacidadeIndisponivel")
    fator_alocavel_percentual: int = Field(alias="fatorAlocavelPercentual")


class JanelaRead(_Read):
    planejado_inicio: date | None = Field(alias="planejadoInicio")
    planejado_fim: date | None = Field(alias="planejadoFim")
    estado: str  # nao_planejado | incompleto | planejado


class ItemEtapaRead(_Read):
    """Uma etapa que compõe um número: permite EXPLICAR a carga (drill-down e pendências). Sem dados financeiros."""

    demanda_id: str = Field(alias="demandaId")
    identificador: str
    titulo: str
    status_demanda: str = Field(alias="statusDemanda")
    cliente: RefRead | None
    projeto: RefRead | None
    etapa_id: str = Field(alias="etapaId")
    etapa_nome: str = Field(alias="etapaNome")
    etapa_tipo: str = Field(alias="etapaTipo")
    estimativa_min: int | None = Field(alias="estimativaMin")
    restante_min: int | None = Field(alias="restanteMin")
    # Valor da ETAPA inteira na semana (antes de dividir entre responsáveis) e a PARTE do alvo consultado (pessoa/departamento). `null` quando não há distribuição.
    planejado_na_semana_min: int | None = Field(alias="planejadoNaSemanaMin")
    parte_min: int | None = Field(alias="parteMin")
    janela: JanelaRead
    # alocada | janela_vencida | sem_dia_util | null (sem janela completa, sem estimativa ou capacidade indisponível)
    alocacao_estado: str | None = Field(alias="alocacaoEstado")
    motivo_nao_planejado: str | None = Field(alias="motivoNaoPlanejado")  # sem_janela | janela_incompleta
    origem: str  # responsavel | pool_departamento | pool_sem_departamento
    dividido_entre: int = Field(alias="divididoEntre")


class PessoaCargaRead(_Read):
    usuario_id: str = Field(alias="usuarioId")
    nome: str
    departamento_id: str | None = Field(alias="departamentoId")
    capacidade_nominal_min: int | None = Field(alias="capacidadeNominalMin")
    capacidade_alocavel_min: int | None = Field(alias="capacidadeAlocavelMin")
    planejado_min: int | None = Field(alias="planejadoMin")
    saldo_min: int | None = Field(alias="saldoMin")
    ocupacao_percentual: float | None = Field(alias="ocupacaoPercentual")
    # 11B.2D-A (ADITIVOS): de onde vem a capacidade da pessoa e quantos dias CONSIDERADOS da semana estão cobertos por ausência. `null` quando a capacidade está indisponível (expediente desligado).
    capacidade_origem: str | None = Field(default=None, alias="capacidadeOrigem")  # empresa | individual
    dias_ausentes: int | None = Field(default=None, alias="diasAusentes")
    nao_planejado_min: int = Field(alias="naoPlanejadoMin")
    pendencias_planejamento_min: int = Field(alias="pendenciasPlanejamentoMin")
    sem_estimativa_count: int = Field(alias="semEstimativaCount")


class DepartamentoCargaRead(_Read):
    departamento_id: str = Field(alias="departamentoId")
    nome: str
    pessoas_count: int = Field(alias="pessoasCount")
    capacidade_nominal_min: int | None = Field(alias="capacidadeNominalMin")
    capacidade_alocavel_min: int | None = Field(alias="capacidadeAlocavelMin")
    planejado_min: int | None = Field(alias="planejadoMin")
    # SUBCONJUNTO de `planejadoMin`: carga de etapas sem usuário responsável atribuídas a este departamento. Não é somada de novo.
    planejado_pool_min: int | None = Field(alias="planejadoPoolMin")
    saldo_min: int | None = Field(alias="saldoMin")
    ocupacao_percentual: float | None = Field(alias="ocupacaoPercentual")
    nao_planejado_min: int = Field(alias="naoPlanejadoMin")
    pendencias_planejamento_min: int = Field(alias="pendenciasPlanejamentoMin")
    sem_estimativa_count: int = Field(alias="semEstimativaCount")


class PoolSemDepartamentoRead(_Read):
    etapas_count: int = Field(alias="etapasCount")
    planejado_min: int | None = Field(alias="planejadoMin")
    nao_planejado_min: int = Field(alias="naoPlanejadoMin")
    pendencias_planejamento_min: int = Field(alias="pendenciasPlanejamentoMin")
    sem_estimativa_count: int = Field(alias="semEstimativaCount")


class BucketRead(_Read):
    etapas_count: int = Field(alias="etapasCount")
    # Soma da estimativa CONHECIDA das etapas do balde (etapa sem estimativa não soma zero: entra em `semEstimativaCount`).
    minutos_conhecidos: int = Field(alias="minutosConhecidos")
    sem_estimativa_count: int = Field(alias="semEstimativaCount")


class NaoPlanejadoRead(_Read):
    """Carga que NÃO entra na ocupação, separada por motivo. Independe da semana consultada: é o que ainda falta planejar."""

    sem_janela: BucketRead = Field(alias="semJanela")
    janela_incompleta: BucketRead = Field(alias="janelaIncompleta")


class PendenciaRead(BucketRead):
    itens: list[ItemEtapaRead]
    truncado: bool


class PendenciasPlanejamentoRead(_Read):
    """Conflitos de planejamento que pedem ação do gestor. Nada é movido de semana automaticamente."""

    janela_vencida: PendenciaRead = Field(alias="janelaVencida")  # janela completa terminou e a etapa segue aberta: replanejar
    sem_dia_util: PendenciaRead = Field(alias="semDiaUtil")  # janela completa válida cujos dias restantes não têm capacidade nominal


class DetalheRead(_Read):
    tipo: str  # usuario | departamento
    id: str
    etapas: list[ItemEtapaRead]
    etapas_total: int = Field(alias="etapasTotal")
    truncado: bool


class TrafegoCargaRead(_Read):
    meta: MetaRead
    semana: SemanaRead
    capacidade: CapacidadeRead
    pessoas: list[PessoaCargaRead]
    departamentos: list[DepartamentoCargaRead]
    pool_sem_departamento: PoolSemDepartamentoRead | None = Field(alias="poolSemDepartamento")
    nao_planejado: NaoPlanejadoRead = Field(alias="naoPlanejado")
    pendencias_planejamento: PendenciasPlanejamentoRead = Field(alias="pendenciasPlanejamento")
    detalhe: DetalheRead | None = None
