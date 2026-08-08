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
  id: string;
  empresaId: string;
  nome: string;
  ativo: boolean;
  etapas: WorkflowModeloEtapa[];
  createdAt: string;
  updatedAt: string;
};

export type WorkflowModeloFormDraft = Pick<WorkflowModelo, "nome" | "ativo" | "etapas">;
