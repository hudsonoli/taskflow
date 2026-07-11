import { WorkspaceStats } from "@/components/workspace/WorkspaceStats";
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
    <WorkspaceStats
      stats={[
        { label: "Total", value: demandas.length, description: "Demandas no mock local." },
        { label: "Em execução", value: emExecucao, description: "Demandas em andamento." },
        { label: "Pausadas/Bloqueadas", value: pausadasOuBloqueadas, description: "Fluxos suspensos temporariamente." },
        { label: "Aguardando cliente", value: aguardandoCliente, description: "Retorno externo pendente." },
        { label: "Concluídas", value: concluidas, description: "Demandas finalizadas." },
      ]}
    />
  );
}
