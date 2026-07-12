import { BarChart3 } from "lucide-react";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusPill } from "@/components/ui/StatusPill";

export function DashboardChart() {
  return (
    <section className="rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm">
      <SectionHeader
        title="Visão geral"
        description="Placeholder elegante para o gráfico futuro."
        action={<StatusPill tone="neutral">mock visual</StatusPill>}
      />

      <div className="mt-5">
        <EmptyStateIllustration
          icon={<BarChart3 className="h-6 w-6" aria-hidden="true" />}
          title="Área reservada para gráfico de desempenho"
          description="Placeholder elegante para o gráfico futuro."
        />
      </div>
    </section>
  );
}
