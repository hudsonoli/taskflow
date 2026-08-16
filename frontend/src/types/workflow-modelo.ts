export type WorkflowEtapaTipo = "execucao" | "aprovacao";

export const workflowEtapaTipoLabels: Record<WorkflowEtapaTipo, string> = {
  execucao: "Execução",
  aprovacao: "Aprovação",
};

export type WorkflowUnidadePrazo = "dias_corridos" | "dias_uteis" | "horas";

export const workflowUnidadePrazoLabels: Record<WorkflowUnidadePrazo, string> = {
  dias_corridos: "Dias corridos",
  dias_uteis: "Dias úteis",
  horas: "Horas",
};

export type WorkflowModeloStatus = "ativo" | "inativo" | "arquivado";

export type WorkflowModeloEtapa = {
  id: string;
  nome: string;
  tipo: WorkflowEtapaTipo;
  // Prazo de referência da etapa, informado como "X [unidade] antes do deadline" da tarefa.
  quantidadeAntesDeadline: number;
  unidadePrazo: WorkflowUnidadePrazo;
  usuarioResponsavelIds: string[];
};

export type WorkflowModelo = {
  /** UUID técnico — usado em relações e rotas. Nunca exibido na interface. */
  id: string;
  empresaId: string;
  /** Ponte transitória de importação — Workflow está na lista de domínios com XLSX
   * planejado (ver docs/pendencias-arquiteturais.md). Sai quando a importação existir. */
  codigoInterno: string;
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  nome: string;
  status: WorkflowModeloStatus;
  etapas: WorkflowModeloEtapa[];
  createdAt: string;
  updatedAt: string;
};

/** Campos que o formulário edita — os códigos e a empresa são responsabilidade do backend. */
export type WorkflowModeloFormDraft = {
  nome: string;
  status: Exclude<WorkflowModeloStatus, "arquivado">;
  etapas: WorkflowModeloEtapa[];
};
