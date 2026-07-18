"use client";

import { PageShell } from "@/components/layout/PageShell";
import { DashboardAgenda } from "./DashboardAgenda";
import { DashboardHeader } from "./DashboardHeader";
import { DashboardKPIs } from "./DashboardKPIs";
import { DashboardRecentActivity } from "./DashboardRecentActivity";
import { DashboardStatusIndicators } from "./DashboardStatusIndicators";
import { DashboardTaskTrendChart } from "./DashboardTaskTrendChart";
import { useDashboardData } from "./useDashboardData";

// Só monta o layout a partir do hook — nenhuma regra de negócio, nenhum
// array de dado, nenhum cálculo aqui. Cada bloco é um componente
// independente (ver useDashboardData.ts e types/dashboard.ts).
export function DashboardView() {
  const data = useDashboardData();

  return (
    <PageShell density="compact">
      <DashboardHeader nome={data.currentUserNome} />

      <DashboardKPIs kpis={data.kpis} />

      <DashboardStatusIndicators statusIndicators={data.statusIndicators} />

      <DashboardTaskTrendChart data={data.taskTrend} />

      <div className="grid gap-3 lg:grid-cols-2">
        <DashboardAgenda agenda={data.agenda} />
        <DashboardRecentActivity atividades={data.atividades} />
      </div>
    </PageShell>
  );
}
