import { CheckCircle2, ListChecks, Workflow } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { WorkflowModelo } from "@/types/workflow-modelo";

export function WorkflowsStats({ workflowModelos }: { workflowModelos: WorkflowModelo[] }) {
  const ativos = workflowModelos.filter((modelo) => modelo.ativo).length;
  const totalEtapas = workflowModelos.reduce((total, modelo) => total + modelo.etapas.length, 0);
  const mediaEtapas = workflowModelos.length ? Math.round(totalEtapas / workflowModelos.length) : 0;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      <MetricCard index={0} title="Total de modelos" value={workflowModelos.length} description="Cadastrados na base." icon={<Workflow size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativos" value={ativos} description="Disponíveis no cadastro de tarefas." icon={<CheckCircle2 size={16} />} tone="green" />
      <MetricCard index={2} title="Média de etapas" value={mediaEtapas} description="Por modelo de workflow." icon={<ListChecks size={16} />} tone="neutral" />
    </div>
  );
}
