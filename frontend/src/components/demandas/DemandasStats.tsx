import {
  CheckCircle2,
  Clock3,
  Hourglass,
  ListChecks,
  PauseCircle,
} from "lucide-react";
import { DashboardGrid } from "@/components/ui/DashboardGrid";
import { MetricCard } from "@/components/ui/MetricCard";
import type { Demanda } from "@/types/demanda";

type DemandasStatsProps = {
  demandas: Demanda[];
};

export function DemandasStats({ demandas }: DemandasStatsProps) {
  const emExecucao = demandas.filter(
    (demanda) => demanda.status === "em_execucao"
  ).length;
  const pausadasOuBloqueadas = demandas.filter(
    (demanda) => demanda.status === "pausada" || demanda.status === "bloqueada"
  ).length;
  const aguardandoCliente = demandas.filter(
    (demanda) => demanda.status === "aguardando_cliente"
  ).length;
  const concluidas = demandas.filter(
    (demanda) => demanda.status === "concluida"
  ).length;

  return (
    <DashboardGrid columns="five">
      <MetricCard
        title="Total"
        value={demandas.length}
        description="Demandas no mock local."
        icon={<ListChecks className="h-5 w-5" />}
        tone="blue"
      />
      <MetricCard
        title="Em execução"
        value={emExecucao}
        description="Demandas em andamento."
        icon={<Clock3 className="h-5 w-5" />}
        tone="green"
      />
      <MetricCard
        title="Pausadas/Bloqueadas"
        value={pausadasOuBloqueadas}
        description="Fluxos suspensos temporariamente."
        icon={<PauseCircle className="h-5 w-5" />}
        tone="amber"
      />
      <MetricCard
        title="Aguardando cliente"
        value={aguardandoCliente}
        description="Retorno externo pendente."
        icon={<Hourglass className="h-5 w-5" />}
        tone="amber"
      />
      <MetricCard
        title="Concluídas"
        value={concluidas}
        description="Demandas finalizadas."
        icon={<CheckCircle2 className="h-5 w-5" />}
        tone="neutral"
      />
    </DashboardGrid>
  );
}
