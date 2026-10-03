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
