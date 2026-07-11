export type WorkflowEtapaStatus =
  | "pendente"
  | "atual"
  | "concluida"
  | "bloqueada";

export type WorkflowEtapa = {
  id: string;
  nome: string;
  ordem: number;
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
  prazoHoras: number;
  status: WorkflowEtapaStatus;
};

export type WorkflowTemplate = {
  id: string;
  empresaId: string;
  agenciaId: string;
  nome: string;
  descricao: string;
  ativo: boolean;
  etapas: WorkflowEtapa[];
  createdAt: string;
  updatedAt: string;
};

export type WorkflowInstancia = {
  id: string;
  templateId?: string;
  demandaId: string;
  etapas: WorkflowEtapa[];
  etapaAtualId: string;
  createdAt: string;
  updatedAt: string;
};

export type WorkflowTransicaoHistorico = {
  id: string;
  demandaId: string;
  etapaOrigemId: string;
  etapaDestinoId: string;
  usuarioId: string;
  dataHora: string;
  observacao?: string;
};

export type WorkflowVisibilidadeConceitual = {
  colaboradorVeDemandaSeAssociadoEtapaAtual: boolean;
  gestorPodeVisualizarTodasConformePermissao: boolean;
  ocultarItensSemAcesso: boolean;
};

// Preparação conceitual para Central de Tráfego futura. Não há SessaoTrabalho real nesta fase.
export type WorkflowSessaoTrabalhoConceitual = {
  entradaEmEtapaAtualPodeIniciarSessao: boolean;
  pausaOuBloqueioPodeSuspenderSessao: boolean;
  saidaDaEtapaPodeEncerrarSessao: boolean;
};
