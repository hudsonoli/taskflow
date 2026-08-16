import type { WorkflowModelo } from "@/types/workflow-modelo";

export function contarEtapasPorTipo(modelo: WorkflowModelo) {
  const execucao = modelo.etapas.filter((item) => item.tipo === "execucao").length;
  const aprovacao = modelo.etapas.filter((item) => item.tipo === "aprovacao").length;
  return { execucao, aprovacao };
}
