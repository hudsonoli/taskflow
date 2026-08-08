import { EMPRESA_PADRAO_ID, generateId } from "@/lib/ids";
import type { DemandaWorkflowEtapa } from "@/types/demanda";
import type { WorkflowModelo, WorkflowUnidadePrazo } from "@/types/workflow-modelo";

export { EMPRESA_PADRAO_ID, generateId };

function etapa(nome: string, tipo: "execucao" | "aprovacao", responsavelIds: string[] = []) {
  return {
    id: generateId("etapa-modelo"),
    nome,
    tipo,
    quantidadeAntesDeadline: 1,
    unidadePrazo: "dias_corridos" as WorkflowUnidadePrazo,
    usuarioResponsavelIds: responsavelIds,
  };
}

export const workflowModelosMock: WorkflowModelo[] = [
  {
    id: "workflow-modelo-1",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "MÍDIA",
    ativo: true,
    etapas: [
      etapa("Elaboração Plano de Mídia", "execucao"),
      etapa("Aprovação Interna", "aprovacao"),
      etapa("Atendimento", "aprovacao"),
      etapa("Cliente", "aprovacao"),
      etapa("Compra da Mídia", "execucao"),
    ],
    createdAt: "2026-07-01T09:00:00-03:00",
    updatedAt: "2026-07-01T09:00:00-03:00",
  },
  {
    id: "workflow-modelo-2",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "CONTEÚDO",
    ativo: true,
    etapas: [
      etapa("Redação", "execucao", ["usuario-imp-008"]),
      etapa("Direção de Arte", "execucao"),
      etapa("Aprovação Interna", "aprovacao"),
      etapa("Atendimento", "aprovacao"),
      etapa("Aprovação Cliente", "aprovacao"),
      etapa("Agendamento/Postagem", "execucao"),
    ],
    createdAt: "2026-07-01T09:00:00-03:00",
    updatedAt: "2026-07-01T09:00:00-03:00",
  },
  {
    id: "workflow-modelo-3",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "CRIAÇÃO",
    ativo: true,
    etapas: [
      etapa("Redação", "execucao"),
      etapa("Aprovação Interna", "aprovacao"),
      etapa("Layout", "execucao"),
      etapa("Aprovação Interna", "aprovacao"),
      etapa("Aprovação Atendimento", "aprovacao"),
    ],
    createdAt: "2026-07-01T09:00:00-03:00",
    updatedAt: "2026-07-01T09:00:00-03:00",
  },
];

// Aproximação: sem calendário de dias úteis no modelo mock, "dias úteis" é tratado como corridos.
export function converterQuantidadeEmHoras(quantidade: number, unidade: WorkflowUnidadePrazo): number {
  if (unidade === "horas") return quantidade;
  return quantidade * 24;
}

// Aplica um modelo de workflow a uma tarefa: cada etapa do modelo informa "X [unidade] antes do
// deadline" — nesta conversão usamos esse valor diretamente como duração (prazoHoras) da etapa
// no fluxo sequencial já existente, preservando a ordem de cadastro do modelo.
export function aplicarModeloWorkflow(modelo: WorkflowModelo): DemandaWorkflowEtapa[] {
  return modelo.etapas.map((modeloEtapa, index) => ({
    id: generateId("etapa-demanda"),
    nome: modeloEtapa.nome,
    ordem: index + 1,
    tipo: modeloEtapa.tipo,
    usuarioResponsavelIds: modeloEtapa.usuarioResponsavelIds,
    departamentoResponsavelIds: [],
    prazoHoras: converterQuantidadeEmHoras(modeloEtapa.quantidadeAntesDeadline, modeloEtapa.unidadePrazo),
    status: "pendente",
  }));
}

export function contarEtapasPorTipo(modelo: WorkflowModelo) {
  const execucao = modelo.etapas.filter((item) => item.tipo === "execucao").length;
  const aprovacao = modelo.etapas.filter((item) => item.tipo === "aprovacao").length;
  return { execucao, aprovacao };
}
