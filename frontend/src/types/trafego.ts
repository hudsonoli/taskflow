export type TrafegoPeriodoFiltro = "hoje" | "24h" | "7d" | "30d";

export type TrafegoStatusFiltro = "todos" | "ativa" | "encerrada";

export type TrafegoFiltersState = {
  usuarioIds: string[];
  departamentoIds: string[];
  demandaQuery: string;
  status: TrafegoStatusFiltro;
  periodo: TrafegoPeriodoFiltro;
};

export type TrafegoAgrupamentoTipo = "usuario" | "departamento" | "equipe";

export type TrafegoCargaItem = {
  agrupamentoId: string;
  tipoAgrupamento: TrafegoAgrupamentoTipo;
  sessoesAtivas: number;
  demandasDistintas: number;
  tempoAtivoTotalSegundos: number;
  inicioMaisAntigo: string;
};

export type TrafegoResumo = {
  sessoesAtivas: number;
  sessoesEncerradas: number;
  demandasDistintas: number;
  usuariosDistintos: number;
  departamentosDistintos: number;
  tempoOperacionalEstimadoSegundos: number;
  tempoMedioSessaoSegundos: number;
  maiorSessaoSegundos: number;
};

/**
 * `GET /sessoes-trabalho/trafego/indicadores` (D2-D3C1): o `TrafegoResumo` já agregado no
 * servidor, "as of" o instante da resposta. `maiorSessaoAtivaSegundos` existe só para o contador
 * das sessões ativas continuar andando a cada segundo sem novo fetch
 * (ver `resumoDeIndicadores` em lib/trafego.ts).
 */
export type TrafegoIndicadores = TrafegoResumo & {
  maiorSessaoAtivaSegundos: number;
};
