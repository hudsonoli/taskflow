import {
  AGENCIA_PADRAO_ID,
  EMPRESA_PADRAO_ID,
  departamentosProjetoDisponiveis,
  generateId,
  responsaveisProjetoDisponiveis,
} from "@/lib/projetos-mock";
import type {
  WorkflowEtapa,
  WorkflowEtapaStatus,
  WorkflowInstancia,
  WorkflowTemplate,
  WorkflowTransicaoHistorico,
} from "@/types/workflow";

export const workflowEtapaStatusLabels: Record<WorkflowEtapaStatus, string> = {
  pendente: "Pendente",
  atual: "Atual",
  concluida: "Concluída",
  bloqueada: "Bloqueada",
};

function createTemplateStep(
  nome: string,
  ordem: number,
  prazoHoras: number,
  usuarioResponsavelIds: string[] = [],
  departamentoResponsavelIds: string[] = []
): WorkflowEtapa {
  return {
    id: generateId("workflow-etapa"),
    nome,
    ordem,
    usuarioResponsavelIds,
    departamentoResponsavelIds,
    prazoHoras,
    status: ordem === 1 ? "atual" : "pendente",
  };
}

export const workflowTemplatesMock: WorkflowTemplate[] = [
  {
    id: "workflow-template-criacao-padrao",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    nome: "Criação padrão",
    descricao: "Fluxo para demandas de criação com aprovação do cliente.",
    ativo: true,
    etapas: [
      createTemplateStep("Atendimento", 1, 8, ["user-2"], ["dep-atendimento"]),
      createTemplateStep("Redação", 2, 16, ["user-5"], ["dep-conteudo"]),
      createTemplateStep("Direção de arte", 3, 24, ["user-3"], ["dep-criacao"]),
      createTemplateStep("Revisão", 4, 8, ["user-2"], ["dep-atendimento"]),
      createTemplateStep("Aprovação cliente", 5, 24, [], ["dep-atendimento"]),
      createTemplateStep("Finalização", 6, 8, ["user-3"], ["dep-criacao"]),
    ],
    createdAt: "2026-07-11T08:00:00-03:00",
    updatedAt: "2026-07-11T08:00:00-03:00",
  },
  {
    id: "workflow-template-midia-paga",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    nome: "Mídia paga",
    descricao: "Fluxo para planejamento, configuração e relatório de mídia.",
    ativo: true,
    etapas: [
      createTemplateStep("Briefing", 1, 8, ["user-2"], ["dep-atendimento"]),
      createTemplateStep("Planejamento", 2, 16, ["user-5"], ["dep-midia"]),
      createTemplateStep("Configuração", 3, 12, ["user-5"], ["dep-midia"]),
      createTemplateStep("Aprovação", 4, 12, [], ["dep-atendimento"]),
      createTemplateStep("Monitoramento", 5, 48, ["user-5"], ["dep-midia"]),
      createTemplateStep("Relatório", 6, 12, ["user-5"], ["dep-midia"]),
    ],
    createdAt: "2026-07-11T08:00:00-03:00",
    updatedAt: "2026-07-11T08:00:00-03:00",
  },
  {
    id: "workflow-template-conteudo",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    nome: "Conteúdo",
    descricao: "Fluxo enxuto para demandas de conteúdo e publicação.",
    ativo: true,
    etapas: [
      createTemplateStep("Briefing", 1, 6, ["user-2"], ["dep-atendimento"]),
      createTemplateStep("Redação", 2, 16, ["user-5"], ["dep-conteudo"]),
      createTemplateStep("Revisão", 3, 8, ["user-2"], ["dep-conteudo"]),
      createTemplateStep("Publicação", 4, 4, ["user-5"], ["dep-conteudo"]),
    ],
    createdAt: "2026-07-11T08:00:00-03:00",
    updatedAt: "2026-07-11T08:00:00-03:00",
  },
];

export function cloneWorkflowEtapas(etapas: WorkflowEtapa[]): WorkflowEtapa[] {
  return etapas.map((etapa, index) => ({
    ...etapa,
    id: generateId("workflow-etapa-instancia"),
    ordem: index + 1,
    status: index === 0 ? "atual" : "pendente",
    usuarioResponsavelIds: [...etapa.usuarioResponsavelIds],
    departamentoResponsavelIds: [...etapa.departamentoResponsavelIds],
  }));
}

export function createWorkflowInstanceFromTemplate(
  template: WorkflowTemplate,
  demandaId: string
): WorkflowInstancia {
  const etapas = cloneWorkflowEtapas(template.etapas);
  const now = new Date().toISOString();

  return {
    id: generateId("workflow-instancia"),
    templateId: template.id,
    demandaId,
    etapas,
    etapaAtualId: etapas[0]?.id ?? "",
    createdAt: now,
    updatedAt: now,
  };
}

export function createWorkflowInstanceFromSteps(
  etapas: WorkflowEtapa[],
  demandaId: string,
  templateId?: string
): WorkflowInstancia {
  const normalizedEtapas = cloneWorkflowEtapas(etapas);
  const now = new Date().toISOString();

  return {
    id: generateId("workflow-instancia"),
    templateId,
    demandaId,
    etapas: normalizedEtapas,
    etapaAtualId: normalizedEtapas[0]?.id ?? "",
    createdAt: now,
    updatedAt: now,
  };
}

export function createWorkflowTransitionHistory(
  demandaId: string,
  etapaOrigemId: string,
  etapaDestinoId: string,
  observacao?: string
): WorkflowTransicaoHistorico {
  return {
    id: generateId("workflow-transicao"),
    demandaId,
    etapaOrigemId,
    etapaDestinoId,
    usuarioId: "user-1",
    dataHora: new Date().toLocaleString("pt-BR"),
    observacao,
  };
}

export {
  departamentosProjetoDisponiveis,
  generateId,
  responsaveisProjetoDisponiveis,
};
