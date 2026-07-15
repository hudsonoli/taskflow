import { CadastroIndicators } from "@/components/cadastros";
import type { DashboardKpi } from "@/types/dashboard";

type DashboardKPIsProps = {
  kpis: DashboardKpi[];
};

// Três indicadores principais (Tarefas/Projetos/SLA) — sem badge de
// variação: não há cálculo real de tendência nesta fase, então nenhum
// percentual falso é exibido.
export function DashboardKPIs({ kpis }: DashboardKPIsProps) {
  return (
    <CadastroIndicators
      density="compact"
      columnsClassName="grid gap-3 grid-cols-1 sm:grid-cols-3"
      items={kpis.map((kpi) => ({ label: kpi.label, value: kpi.value }))}
    />
  );
}
