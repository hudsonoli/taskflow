import { Card } from "@/components/ui/Card";

export function DashboardChart() {
  return (
    <Card>
      <div>
        <h3 className="text-xl font-semibold text-zinc-900">Visão geral</h3>
        <p className="mt-1 text-sm text-zinc-500">
          Placeholder elegante para o gráfico futuro.
        </p>
      </div>

      <div className="mt-6 flex h-[280px] items-center justify-center rounded-3xl border border-dashed border-zinc-200 bg-[#faf8f4] text-sm text-zinc-500">
        {/* TODO: integrar Chart.js */}
        Área reservada para gráfico de desempenho
      </div>
    </Card>
  );
}
