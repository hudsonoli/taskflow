export type TrafegoSessaoStatus =
  | "ativa"
  | "pausada"
  | "bloqueada"
  | "aguardando_cliente";

export type TrafegoAgrupamentoTipo = "usuario" | "departamento";

export type TrafegoPeriodoFiltro = "hoje" | "24h" | "7d" | "30d";

export type TrafegoAgoraItem = {
  sessaoId: string;
  empresaId: string;
  agenciaId: string | null;
  demandaId: string;
  workflowEtapaId: string | null;
  usuarioId: string | null;
  departamentoId: string | null;
  inicioEm: string;
  tempoDecorridoSegundos: number;
  status: TrafegoSessaoStatus;
  eventoInicioId: string;
};

export type TrafegoCargaItem = {
  agrupamentoId: string;
  tipoAgrupamento: TrafegoAgrupamentoTipo;
  sessoesAtivas: number;
  demandasDistintas: number;
  tempoAtivoTotalSegundos: number;
  inicioMaisAntigo: string;
  ultimaAtualizacao: string;
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
  inicioPeriodo: string;
  fimPeriodo: string;
};

export type TrafegoFiltersState = {
  empresaId: string;
  usuarioIds: string[];
  departamentoIds: string[];
  demandaQuery: string;
  status: "todos" | TrafegoSessaoStatus;
  periodo: TrafegoPeriodoFiltro;
};
