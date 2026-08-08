import { CheckCircle2, Clock3, Hourglass, ListChecks, PauseCircle } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { Demanda } from "@/types/demanda";

export function DemandasStats({ demandas }: { demandas: Demanda[] }) {
  const emExecucao = demandas.filter((demanda) => demanda.status === "em_execucao").length;
  const pausadasOuBloqueadas = demandas.filter(
    (demanda) => demanda.status === "pausada" || demanda.status === "bloqueada",
  ).length;
  const aguardandoCliente = demandas.filter((demanda) => demanda.status === "aguardando_cliente").length;
  const concluidas = demandas.filter((demanda) => demanda.status === "concluida").length;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
      <MetricCard index={0} title="Total" value={demandas.length} description="Tarefas cadastradas." icon={<ListChecks size={16} />} tone="blue" />
      <MetricCard index={1} title="Em execução" value={emExecucao} description="Em andamento." icon={<Clock3 size={16} />} tone="green" />
      <MetricCard index={2} title="Pausadas/Bloqueadas" value={pausadasOuBloqueadas} description="Fluxos suspensos." icon={<PauseCircle size={16} />} tone="amber" />
      <MetricCard index={3} title="Aguardando cliente" value={aguardandoCliente} description="Retorno externo pendente." icon={<Hourglass size={16} />} tone="amber" />
      <MetricCard index={4} title="Concluídas" value={concluidas} description="Tarefas finalizadas." icon={<CheckCircle2 size={16} />} tone="neutral" />
    </div>
  );
}
