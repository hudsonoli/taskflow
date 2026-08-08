"use client";

import { AnimatePresence } from "framer-motion";
import { Inbox } from "lucide-react";
import { useDroppable } from "@dnd-kit/core";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { Demanda } from "@/types/demanda";
import { DemandaKanbanCard } from "./DemandaKanbanCard";

export function DemandaKanbanColumn({
  id,
  title,
  description,
  demandas,
  tone,
  onOpenDetails,
  arrastavel,
  motivoBloqueio,
}: {
  id: string;
  title: string;
  description: string;
  demandas: Demanda[];
  tone: BadgeTone;
  onOpenDetails: (demandaId: string) => void;
  /** false fora do expediente — os cards viram só clicáveis, sem arraste. */
  arrastavel: boolean;
  motivoBloqueio?: string;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <section
      ref={setNodeRef}
      className={`flex min-h-[300px] w-[280px] shrink-0 flex-col rounded-2xl border p-3 backdrop-blur-sm transition-all duration-200 sm:w-[300px] ${
        isOver
          ? "border-indigo-300 bg-indigo-50/70 ring-2 ring-indigo-200 dark:border-indigo-500/50 dark:bg-indigo-500/10 dark:ring-indigo-500/20"
          : "border-zinc-200/70 bg-zinc-100/60 dark:border-zinc-800 dark:bg-zinc-900/40"
      }`}
    >
      <div className="sticky top-0 z-10 mb-2.5 flex items-start justify-between gap-2 rounded-xl bg-inherit px-1 pb-1 pt-0.5 backdrop-blur-sm">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-sm font-semibold text-zinc-950 dark:text-zinc-50">{title}</h2>
            <Badge tone={tone}>{demandas.length}</Badge>
          </div>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-zinc-500 dark:text-zinc-400">{description}</p>
        </div>
      </div>

      {demandas.length === 0 ? (
        <div className="flex flex-1 items-center">
          <EmptyState
            title="Sem tarefas"
            description={arrastavel ? "Arraste um card para cá." : "Nenhuma tarefa nesta coluna."}
            icon={<Inbox size={16} />}
          />
        </div>
      ) : (
        <div className="space-y-2.5 overflow-y-auto pr-1">
          <AnimatePresence>
            {demandas.map((demanda) => (
              <DemandaKanbanCard
                key={demanda.id}
                demanda={demanda}
                onOpenDetails={onOpenDetails}
                arrastavel={arrastavel}
                motivoBloqueio={motivoBloqueio}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </section>
  );
}
