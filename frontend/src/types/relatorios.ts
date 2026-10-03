/**
 * D4A — "Análise de projeto" e "Análise de peças", calculadas no servidor
 * (`GET /relatorios/projetos/analise` e `/pecas`) sobre TODAS as Demandas do Projeto. O formato é
 * o do schema Pydantic (camelCase via alias) — sem mapeamento no cliente.
 */

export type RelatorioAnaliseProjeto = {
  projetoId: string;
  projetoNome: string;
  /** Todas as Demandas não arquivadas do Projeto (qualquer status), no escopo de quem pede. */
  totalDemandas: number;
  prioridade: { baixa: number; media: number; alta: number };
  /** Em dias. `null` quando nenhuma Demanda do Projeto tem `dataInicio`. */
  tempoMedioAberturaAteInicioDias: number | null;
  /** Em dias. `null` quando nenhuma Demanda tem envio E retorno do cliente. */
  tempoMedioRetornoClienteDias: number | null;
  /** Já em ordem alfabética, só quem tem ao menos uma Demanda no Projeto. */
  colaboradores: { id: string; nome: string; demandas: number }[];
};

/** Uma "peça" é a própria Demanda do Projeto. */
export type RelatorioPeca = {
  demandaId: string;
  nome: string;
  numeroOperacional: number;
  /** Primeiro responsável (por id); `null` = "Sem responsável". */
  redatorNome: string | null;
  /** Só existe para Demanda concluída/cancelada. */
  tempoEmPautaDias: number | null;
  emAndamento: boolean;
};

export type RelatorioPecasPagina = {
  items: RelatorioPeca[];
  total: number;
  limit: number;
  offset: number;
};

// ---------------------------------------------------------------------------------------
// D4B — Performance de colaborador e gráficos (GET /relatorios/colaboradores/**, /graficos/**)
// ---------------------------------------------------------------------------------------

/** Fatia de pizza/donut: usada pelos gráficos e pela participação por etapa. */
export interface FatiaPizza {
  id: string;
  label: string;
  value: number;
}

export interface SerieBarraEmpilhada {
  categoria: string;
  categoriaId: string;
  segmentos: { seriesId: string; label: string; value: number }[];
}

export interface PontoLinha {
  semanaLabel: string;
  inicioSemana: string;
  value: number;
}

/** Opção do seletor de colaborador — todos os status, sem conta de sistema, sem o `limit=200`. */
export type RelatorioColaboradorOpcao = { id: string; nome: string };

export type RelatorioPerformanceColaborador = {
  colaboradorId: string;
  colaboradorNome: string;
  /** Demandas `concluida` em que ele é responsável (a Demanda conta para CADA responsável). */
  demandasEntregues: number;
  entreguesNoPrazo: number;
  entreguesEmAtraso: number;
  /** Já na ordem de primeira aparição. */
  participacaoPorEtapa: FatiaPizza[];
};

/** Semana de `volume-semanal`: `inicioSemana` é a segunda-feira ("YYYY-MM-DD", fuso da aplicação). */
export type RelatorioPontoSemanal = { inicioSemana: string; value: number };
