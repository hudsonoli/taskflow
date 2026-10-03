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

/**
 * Uma linha de "Quem está trabalhando agora" (D2-D3C3) — `GET /sessoes-trabalho/trafego/agora`.
 * Autossuficiente: usuário, departamento e Demanda já resolvidos pelo servidor (nunca dependem de
 * diretório do cliente). `decorridoSegundos` é "as of" a resposta.
 */
export type TrafegoAgoraItem = {
  sessaoId: string;
  inicioEm: string;
  decorridoSegundos: number;
  demandaId: string;
  demandaNumero: number | null;
  demandaNome: string | null;
  usuarioId: string | null;
  usuarioNome: string | null;
  departamentoId: string | null;
  departamentoNome: string | null;
};

export type TrafegoAgoraPagina = {
  items: TrafegoAgoraItem[];
  total: number;
  limit: number;
  offset: number;
};

/** Linha na tela: cada página tem o seu `recebidoEm`, âncora do relógio da própria linha. */
export type TrafegoAgoraLinha = TrafegoAgoraItem & { recebidoEm: number };
