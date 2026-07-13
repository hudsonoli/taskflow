import { useMemo } from "react";
import { Columns3 } from "lucide-react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import type { Demanda, DemandaStatus } from "@/types/demanda";
import { DemandaKanbanColumn } from "./DemandaKanbanColumn";

type DemandasKanbanProps = {
  demandas: Demanda[];
  onOpenDetails: (demandaId: string) => void;
};

type KanbanColumnConfig = {
  id: string;
  title: string;
  description: string;
  statuses: DemandaStatus[];
  tone: "neutral" | "blue" | "green" | "amber" | "red";
};

const kanbanColumns: KanbanColumnConfig[] = [
  {
    id: "rascunho-planejada",
    title: "Rascunho/Planejada",
    description: "Demandas em preparação ou ainda programadas.",
    statuses: ["rascunho", "planejada"],
    tone: "blue",
  },
  {
    id: "em-execucao",
    title: "Em execução",
    description: "Demandas em andamento na operação.",
    statuses: ["em_execucao"],
    tone: "green",
  },
  {
    id: "pausada-bloqueada",
    title: "Pausada/Bloqueada",
    description: "Fluxos suspensos ou com impedimento.",
    statuses: ["pausada", "bloqueada"],
    tone: "amber",
  },
  {
    id: "aguardando-cliente",
    title: "Aguardando cliente",
    description: "Demandas aguardando retorno externo.",
    statuses: ["aguardando_cliente"],
    tone: "amber",
  },
  {
    id: "concluida",
    title: "Concluída",
    description: "Demandas finalizadas no mock local.",
    statuses: ["concluida"],
    tone: "green",
  },
  {
    id: "cancelada",
    title: "Cancelada",
    description: "Demandas canceladas no fluxo.",
    statuses: ["cancelada"],
    tone: "neutral",
  },
];

export function DemandasKanban({
  demandas,
  onOpenDetails,
}: DemandasKanbanProps) {
  const groupedDemands = useMemo(
    () =>
      kanbanColumns.map((column) => ({
        ...column,
        demandas: demandas.filter((demanda) =>
          column.statuses.includes(demanda.status)
        ),
      })),
    [demandas]
  );

  return (
    <div className="rounded-3xl border border-zinc-100 bg-white p-4 shadow-sm sm:p-5">
      <SectionHeader
        eyebrow="Kanban de demandas"
        title="Fluxo por status"
        description="Projeção local das mesmas demandas filtradas na lista. A visão por pauta e departamento será conectada quando houver usuário autenticado e permissões reais."
        action={
          <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-100">
            <Columns3 className="h-3.5 w-3.5" />
            Somente leitura
          </span>
        }
      />

      <div className="mt-5 overflow-x-auto pb-2">
        <div className="flex gap-4">
          {groupedDemands.map((column) => (
            <DemandaKanbanColumn
              key={column.id}
              title={column.title}
              description={column.description}
              demandas={column.demandas}
              tone={column.tone}
              onOpenDetails={onOpenDetails}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
