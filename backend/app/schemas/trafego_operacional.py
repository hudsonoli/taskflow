"""Tráfego V2 — Fase 2: contratos da camada de MÉTRICAS OPERACIONAIS (somente leitura).

TEMPO OPERACIONAL ≠ TEMPO PESSOAL. Tudo aqui descreve o tempo DECORRIDO de Demandas/etapas num estado (`demanda_status_intervalos`), nunca horas trabalhadas por alguém.
Por isso nenhum campo se chama `horasTrabalhadas*`, nenhum é por usuário-como-executor e nenhuma métrica lê `sessoes_trabalho`. "Em execução há 2 h" = a Demanda está nesse
estado há 2 h — não que alguém tenha trabalhado nela durante 2 h.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class _Read(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class RefNomeRead(_Read):
    id: str
    nome: str


class EtapaAtualRead(_Read):
    """Etapa atual do workflow (menor `ordem` não concluída — a MESMA autoridade de `DemandaService._derivar_etapa_atual_id`). `departamentos` = departamentos responsáveis da etapa."""

    id: str
    nome: str
    tipo: str
    departamentos: list[RefNomeRead]


class ResponsavelRead(_Read):
    """Responsável ATUAL (atribuição) — não é executor: nenhuma sessão pessoal entra aqui. Só id e nome (sem e-mail, perfil ou credencial)."""

    usuario_id: str = Field(alias="usuarioId")
    nome: str


class AgoraKpisRead(_Read):
    """Contadores do ESCOPO de triagem (planejada, em_execucao, pausada, bloqueada, aguardando_cliente). Rascunho e estados terminais ficam de fora."""

    em_execucao: int = Field(alias="emExecucao")
    atrasadas: int
    vencem_hoje: int = Field(alias="vencemHoje")
    sem_responsavel: int = Field(alias="semResponsavel")
    sem_prazo: int = Field(alias="semPrazo")
    # Workflow CONHECIDO: a última etapa foi concluída e a Demanda segue aberta (a conclusão automática ainda é uma pendência separada). Não é erro de consulta.
    sem_etapa_atual: int = Field(alias="semEtapaAtual")


class AgoraDemandaRead(_Read):
    demanda_id: str = Field(alias="demandaId")
    codigo_referencia: str = Field(alias="codigoReferencia")
    numero_operacional: int = Field(alias="numeroOperacional")
    identificador: str
    titulo: str
    projeto: RefNomeRead | None
    cliente: RefNomeRead | None
    etapa_atual: EtapaAtualRead | None = Field(alias="etapaAtual")
    # ATRIBUIÇÃO atual: da etapa atual quando há workflow com etapa aberta; da Demanda nos demais casos (`origemResponsaveis`). NUNCA o executor.
    responsaveis: list[ResponsavelRead]
    origem_responsaveis: str = Field(alias="origemResponsaveis")  # "etapa_atual" | "demanda"
    status: str
    # Início do intervalo ABERTO (quando a Demanda entrou neste estado) e há quanto tempo. `null` só se a Demanda não tiver intervalo aberto (dado anterior à medição, nunca inventado).
    inicio_estado_atual: datetime | None = Field(alias="inicioEstadoAtual")
    idade_estado_segundos: int | None = Field(alias="idadeEstadoSegundos")
    prazo: datetime | None
    atrasada: bool


class TrafegoOperacionalAgoraRead(_Read):
    agora_servidor: datetime = Field(alias="agoraServidor")
    fuso_empresa: str = Field(alias="fusoEmpresa")
    # Dia LOCAL da empresa usado em "vencem hoje" (intervalo [hojeInicio, hojeFim) em UTC).
    dia_local: date = Field(alias="diaLocal")
    hoje_inicio: datetime = Field(alias="hojeInicio")
    hoje_fim: datetime = Field(alias="hojeFim")
    escopo_status: list[str] = Field(alias="escopoStatus")
    kpis: AgoraKpisRead
    em_execucao: list[AgoraDemandaRead] = Field(alias="emExecucao")
    em_execucao_total: int = Field(alias="emExecucaoTotal")
    limite: int
    truncado: bool


class PeriodoRead(_Read):
    inicio: datetime
    fim: datetime
    # min(fim, agora): o tempo nunca é contado além do "agora" do servidor.
    fim_efetivo: datetime = Field(alias="fimEfetivo")


class FiltrosGargalosRead(_Read):
    departamento_id: str | None = Field(alias="departamentoId")
    cliente_id: str | None = Field(alias="clienteId")
    projeto_id: str | None = Field(alias="projetoId")
    workflow_etapa_id: str | None = Field(alias="workflowEtapaId")


class DefinicaoEtapaRead(_Read):
    """DEFINIÇÃO de etapa — a identidade usada para agregar. Métricas "por definição" agregam MUITAS etapas materializadas (uma por Demanda); por isso nenhum id de etapa materializada é
    devolvido aqui como se fosse a identidade global.

    A definição é: nome normalizado (minúsculas, sem espaços nas pontas) + `tipo` + CONJUNTO CANÔNICO de departamentos responsáveis (ids ordenados). Mesmo nome e tipo com departamentos
    diferentes são definições diferentes; a ordem em que os departamentos foram gravados não importa. O workflow (modelo) de origem NÃO faz parte da identidade.
    `chave` = identificador opaco e determinístico (hash) dessa tripla — serve de chave de lista na UI; `nome` é só apresentação (nome com espaços aparados, como gravado)."""

    chave: str
    nome: str
    tipo: str
    departamentos: list[RefNomeRead]


class GargaloEtapaRead(_Read):
    """Métricas de UMA definição de etapa (ver `DefinicaoEtapaRead`) agregadas sobre todas as Demandas do período — NÃO de uma etapa materializada.

    `n` = ocorrências de etapa (par Demanda × etapa materializada) com algum tempo medido no período. Cada média usa como denominador SÓ as ocorrências com tempo > 0 naquele estado
    (`nExecucao`, `nPausado`...). Todos os tempos são OPERACIONAIS, recortados ao período."""

    definicao_etapa: DefinicaoEtapaRead = Field(alias="definicaoEtapa")
    n: int

    n_execucao: int = Field(alias="nExecucao")
    tempo_execucao_total_segundos: int = Field(alias="tempoExecucaoTotalSegundos")
    tempo_execucao_medio_segundos: int | None = Field(alias="tempoExecucaoMedioSegundos")
    tempo_execucao_maior_segundos: int | None = Field(alias="tempoExecucaoMaiorSegundos")

    n_pausado: int = Field(alias="nPausado")
    tempo_pausado_total_segundos: int = Field(alias="tempoPausadoTotalSegundos")
    tempo_pausado_medio_segundos: int | None = Field(alias="tempoPausadoMedioSegundos")
    tempo_pausado_maior_segundos: int | None = Field(alias="tempoPausadoMaiorSegundos")

    n_bloqueado: int = Field(alias="nBloqueado")
    tempo_bloqueado_total_segundos: int = Field(alias="tempoBloqueadoTotalSegundos")
    tempo_bloqueado_medio_segundos: int | None = Field(alias="tempoBloqueadoMedioSegundos")
    tempo_bloqueado_maior_segundos: int | None = Field(alias="tempoBloqueadoMaiorSegundos")

    n_aguardando_cliente: int = Field(alias="nAguardandoCliente")
    tempo_aguardando_cliente_total_segundos: int = Field(alias="tempoAguardandoClienteTotalSegundos")
    tempo_aguardando_cliente_medio_segundos: int | None = Field(alias="tempoAguardandoClienteMedioSegundos")
    tempo_aguardando_cliente_maior_segundos: int | None = Field(alias="tempoAguardandoClienteMaiorSegundos")


class TempoSemEtapaRead(_Read):
    """Tempo operacional dos intervalos SEM etapa de workflow (Demanda sem workflow, ou workflow já concluído). Mesma definição de `n`/média das etapas: ocorrência = Demanda."""

    n: int
    n_execucao: int = Field(alias="nExecucao")
    tempo_execucao_total_segundos: int = Field(alias="tempoExecucaoTotalSegundos")
    tempo_execucao_medio_segundos: int | None = Field(alias="tempoExecucaoMedioSegundos")
    tempo_execucao_maior_segundos: int | None = Field(alias="tempoExecucaoMaiorSegundos")
    n_pausado: int = Field(alias="nPausado")
    tempo_pausado_total_segundos: int = Field(alias="tempoPausadoTotalSegundos")
    n_bloqueado: int = Field(alias="nBloqueado")
    tempo_bloqueado_total_segundos: int = Field(alias="tempoBloqueadoTotalSegundos")
    n_aguardando_cliente: int = Field(alias="nAguardandoCliente")
    tempo_aguardando_cliente_total_segundos: int = Field(alias="tempoAguardandoClienteTotalSegundos")


class FilaEtapaRead(_Read):
    """WIP ATUAL (não depende do período) por definição de etapa: Demandas ABERTAS (escopo de triagem) cuja etapa atual é esta.

    `maisAntigaDesde`/`maisAntigaSegundos` = idade NA ETAPA do item mais antigo: início da sequência contínua de intervalos da MESMA etapa (qualquer status) que termina no intervalo
    aberto — uma devolução à etapa anterior recomeça a contagem. `idadeEstadoMaisAntigoSegundos` = idade no ESTADO atual do item de estado mais antigo (outra pergunta).
    `maisAntigaTruncadaPelaMedicao`: a sequência começa no intervalo inicial da migração (a idade real pode ser maior que a medida)."""

    definicao_etapa: DefinicaoEtapaRead = Field(alias="definicaoEtapa")
    wip: int
    planejadas: int
    em_execucao: int = Field(alias="emExecucao")
    pausadas: int
    bloqueadas: int
    aguardando_cliente: int = Field(alias="aguardandoCliente")
    mais_antiga_desde: datetime = Field(alias="maisAntigaDesde")
    mais_antiga_segundos: int = Field(alias="maisAntigaSegundos")
    mais_antiga_truncada_pela_medicao: bool = Field(alias="maisAntigaTruncadaPelaMedicao")
    idade_estado_mais_antigo_segundos: int = Field(alias="idadeEstadoMaisAntigoSegundos")


class FilaSemEtapaRead(_Read):
    """Demandas abertas SEM etapa atual, separadas em dois casos que NÃO são a mesma coisa."""

    # Workflow concluído e Demanda ainda aberta (pendência conhecida — conclusão automática do workflow).
    workflow_concluido: int = Field(alias="workflowConcluido")
    # Demanda que nunca teve workflow.
    sem_workflow: int = Field(alias="semWorkflow")


class AtualRead(_Read):
    """Contagem ATUAL do escopo de triagem por estado (inclui bloqueadas e aguardando cliente)."""

    wip: int
    planejadas: int
    em_execucao: int = Field(alias="emExecucao")
    pausadas: int
    bloqueadas: int
    aguardando_cliente: int = Field(alias="aguardandoCliente")


class TrafegoOperacionalGargalosRead(_Read):
    agora_servidor: datetime = Field(alias="agoraServidor")
    periodo: PeriodoRead
    filtros: FiltrosGargalosRead
    # Quando a medição começou (menor `inicio_em` da empresa; marca da migration). `null` = nada medido ainda.
    medicao_desde: datetime | None = Field(alias="medicaoDesde")
    # `true` quando o período começa ANTES da medição (ou não há medição): o histórico anterior não existe e não é estimado.
    cobertura_parcial: bool = Field(alias="coberturaParcial")
    etapas: list[GargaloEtapaRead]
    etapas_total: int = Field(alias="etapasTotal")
    sem_etapa: TempoSemEtapaRead = Field(alias="semEtapa")
    atual: AtualRead
    fila: list[FilaEtapaRead]
    fila_total: int = Field(alias="filaTotal")
    fila_sem_etapa: FilaSemEtapaRead = Field(alias="filaSemEtapa")
    limite: int
