import type { WorkflowModelo, WorkflowUnidadePrazo } from "@/types/workflow-modelo";

export function contarEtapasPorTipo(modelo: WorkflowModelo) {
  const execucao = modelo.etapas.filter((item) => item.tipo === "execucao").length;
  const aprovacao = modelo.etapas.filter((item) => item.tipo === "aprovacao").length;
  return { execucao, aprovacao };
}

// Aproximação: sem calendário de dias úteis, "dias úteis" é tratado como corridos — mesma
// simplificação que o mock já fazia antes da migração de Workflow para backend real.
export function converterQuantidadeEmHoras(quantidade: number, unidade: WorkflowUnidadePrazo): number {
  if (unidade === "horas") return quantidade;
  return quantidade * 24;
}
