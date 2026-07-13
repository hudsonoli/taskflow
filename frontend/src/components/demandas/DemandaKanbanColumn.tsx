import { Inbox } from "lucide-react";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import { StatusPill } from "@/components/ui/StatusPill";
import type { Demanda } from "@/types/demanda";
import { DemandaKanbanCard } from "./DemandaKanbanCard";

type DemandaKanbanColumnProps = {
  title: string;
  description: string;
  demandas: Demanda[];
  tone: "neutral" | "blue" | "green" | "amber" | "red";
  onOpenDetails: (demandaId: string) => void;
};

export function DemandaKanbanColumn({
  title,
  description,
  demandas,
  tone,
  onOpenDetails,
}: DemandaKanbanColumnProps) {
  return (
    <section className="flex min-h-[300px] w-[280px] shrink-0 flex-col rounded-3xl border border-zinc-100 bg-zinc-50/80 p-3 shadow-sm sm:w-[300px]">
      <div className="mb-2.5 flex items-start justify-between gap-2 px-1">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-sm font-semibold text-zinc-950">
              {title}
            </h2>
            <StatusPill tone={tone}>{demandas.length}</StatusPill>
          </div>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-zinc-500">
            {description}
          </p>
        </div>
      </div>

      {demandas.length === 0 ? (
        <div className="flex flex-1 items-center">
          <EmptyStateIllustration
            title="Sem demandas"
            description="Nenhuma demanda dos filtros atuais está nesta coluna."
            icon={<Inbox className="h-4 w-4" />}
            size="compact"
          />
        </div>
      ) : (
        <div className="space-y-2.5 overflow-y-auto pr-1">
          {demandas.map((demanda) => (
            <DemandaKanbanCard
              key={demanda.id}
              demanda={demanda}
              onOpenDetails={onOpenDetails}
            />
          ))}
        </div>
      )}
    </section>
  );
}
