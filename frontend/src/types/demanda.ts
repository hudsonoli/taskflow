export type DemandaStatus =
  | "rascunho"
  | "planejada"
  | "em_execucao"
  | "pausada"
  | "bloqueada"
  | "aguardando_cliente"
  | "concluida"
  | "cancelada";

export type DemandaPrioridade = "baixa" | "media" | "alta";

export type DemandaWorkflowEtapaStatus =
  | "pendente"
  | "em_execucao"
  | "pausada"
  | "concluida";

export type DemandaWorkflowEtapa = {
  id: string;
  nome: string;
  ordem: number;
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
  prazoHoras: number;
  status: DemandaWorkflowEtapaStatus;
};

export type DemandaHistoricoEvento = {
  id: string;
  usuarioId: string;
  usuario: string;
  acao: string;
  dataHora: string;
  ip: string;
  dispositivo: string;
};

// Estrutura conceitual para Central de Tráfego futura. Não há cronômetro ou lógica real nesta fase.
export type DemandaSessaoTrabalhoConceitual = {
  id: string;
  demandaId: string;
  usuarioId: string;
  etapaId: string;
  inicioEm: string;
  pausaEm?: string;
  encerradaEm?: string;
  statusOrigem: DemandaStatus;
};

export type DemandaVisibilidadeConceitual = {
  colaboradorVeSomenteEtapaAtual: boolean;
  gestorPodeTerVisaoAmpliada: boolean;
  ocultarItensSemPermissao: boolean;
};

export type Demanda = {
  id: string;
  empresaId: string;
  agenciaId: string;
  projetoId: string;
  clienteId: string;
  codigoInterno: string;
  nome: string;
  briefing: string;
  status: DemandaStatus;
  prioridade: DemandaPrioridade;
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
  workflowEtapas: DemandaWorkflowEtapa[];
  etapaAtualId: string;
  prazoEtapaAtual: string;
  dataCriacao: string;
  dataInicio: string;
  dataFimPrevista: string;
  createdAt: string;
  updatedAt: string;
  historico: DemandaHistoricoEvento[];
};

export type DemandaFormDraft = Pick<
  Demanda,
  | "nome"
  | "projetoId"
  | "clienteId"
  | "briefing"
  | "prioridade"
  | "status"
  | "usuarioResponsavelIds"
  | "departamentoResponsavelIds"
  | "dataFimPrevista"
>;
