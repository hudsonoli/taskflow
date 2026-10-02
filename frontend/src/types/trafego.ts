export type TrafegoPeriodoFiltro = "hoje" | "24h" | "7d" | "30d";

export type TrafegoStatusFiltro = "todos" | "ativa" | "encerrada";

export type TrafegoFiltersState = {
  usuarioIds: string[];
  departamentoIds: string[];
  demandaQuery: string;
  status: TrafegoStatusFiltro;
  periodo: TrafegoPeriodoFiltro;
};

/**
 * Um grupo do ranking de carga (usuário, departamento ou equipe) — D2-D3C2. Vem pronto do
 * servidor (`GET /sessoes-trabalho/trafego/carga`): nome já resolvido, lista já ordenada.
 * `tempoAtivoTotalSegundos` é "as of" a resposta (ver `cargaComRelogio` em lib/trafego.ts).
 */
export type TrafegoCargaAgregada = {
  id: string;
  nome: string;
  sessoesAtivas: number;
  demandasDistintas: number;
  tempoAtivoTotalSegundos: number;
};

export type TrafegoCarga = {
  usuarios: TrafegoCargaAgregada[];
  departamentos: TrafegoCargaAgregada[];
  equipes: TrafegoCargaAgregada[];
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
