"use client";

import { AnimatePresence } from "framer-motion";
import { useDroppable } from "@dnd-kit/core";
import type { BadgeTone } from "@/components/ui/Badge";
import { rotuloDaColunaRecolhida } from "@/lib/kanban-colunas";
import type { Demanda } from "@/types/demanda";
import { DemandaKanbanCard } from "./DemandaKanbanCard";

/** Ponto de identidade da coluna (o NOME da coluna continua sendo o rótulo): reaproveita os tons de status já usados no quadro. */
const PONTO_DA_COLUNA: Record<BadgeTone, string> = {
  neutral: "bg-zinc-400",
  blue: "bg-indigo-500",
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
};

export function DemandaKanbanColumn({
  id,
  title,
  description,
  demandas,
  tone,
  onOpenDetails,
  arrastavel,
  motivoBloqueio,
  onIniciarTrabalho,
  podeIniciar,
  recolhida = false,
  onExpandir,
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
  onIniciarTrabalho?: (demandaId: string) => void;
  podeIniciar?: boolean;
  /** Sem cards visíveis e com o recolhimento automático ligado: a coluna continua no DOM e continua sendo destino de soltura, só estreita. */
  recolhida?: boolean;
  onExpandir?: () => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });

  if (recolhida) {
    const rotulo = rotuloDaColunaRecolhida(title, demandas.length);
    return (
      <section
        ref={setNodeRef}
        data-kanban-coluna={id}
        data-recolhida="true"
        aria-label={title}
        className={`flex min-h-[300px] w-14 shrink-0 flex-col rounded-[16px] p-1.5 transition-[width,padding,background-color] duration-200 ease-out [corner-shape:squircle] motion-reduce:transition-none ${
          isOver ? "bg-indigo-50/80 ring-2 ring-indigo-300/60 dark:bg-indigo-500/10 dark:ring-indigo-500/30" : "bg-zinc-100/70 dark:bg-white/[0.04]"
        }`}
      >
        <button
          type="button"
          onClick={onExpandir}
          aria-label={rotulo}
          title={`${rotulo} ${description}`}
          className="flex h-full min-h-[280px] w-full flex-col items-center gap-2.5 rounded-[12px] px-1 py-2.5 text-fg-muted transition hover:bg-black/[0.04] hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40 dark:hover:bg-white/[0.06]"
        >
          <span aria-hidden className={`h-2 w-2 shrink-0 rounded-full ${PONTO_DA_COLUNA[tone]}`} />
          <span className="grid h-[18px] min-w-[18px] place-items-center rounded-[6px] bg-black/[0.06] px-1 text-[11px] font-medium tabular-nums [corner-shape:squircle] dark:bg-white/[0.09]">
            {demandas.length}
          </span>
          <span className="max-h-[170px] overflow-hidden text-[12px] font-semibold tracking-[-0.005em] [writing-mode:vertical-rl] rotate-180">{title}</span>
        </button>
      </section>
    );
  }

  return (
    <section
      ref={setNodeRef}
      data-kanban-coluna={id}
      aria-label={title}
      className={`flex min-h-[300px] w-[280px] shrink-0 flex-col rounded-[16px] p-3 transition-[width,padding,background-color] duration-200 [corner-shape:squircle] motion-reduce:transition-none sm:w-[300px] ${
        isOver ? "bg-indigo-50/80 ring-2 ring-indigo-300/60 dark:bg-indigo-500/10 dark:ring-indigo-500/30" : "bg-zinc-100/70 dark:bg-white/[0.04]"
      }`}
    >
      <div className="mb-3 flex items-center gap-2 px-1" title={description}>
        <span aria-hidden className={`h-2 w-2 shrink-0 rounded-full ${PONTO_DA_COLUNA[tone]}`} />
        <h2 className="truncate text-[13px] font-semibold tracking-[-0.005em] text-fg">{title}</h2>
        <span className="grid h-[18px] min-w-[18px] place-items-center rounded-[6px] bg-black/[0.06] px-1 text-[11px] font-medium tabular-nums text-fg-muted [corner-shape:squircle] dark:bg-white/[0.09]">
          {demandas.length}
        </span>
      </div>

      {demandas.length === 0 ? (
        <div className="flex flex-1 items-start">
          <p className="w-full rounded-[12px] border border-dashed border-zinc-300 px-3 py-6 text-center text-xs text-fg-subtle dark:border-white/15">
            {arrastavel ? "Sem tarefas. Arraste um card para cá." : "Nenhuma tarefa nesta coluna."}
          </p>
        </div>
      ) : (
        <div className="space-y-2 overflow-y-auto pr-0.5">
          <AnimatePresence>
            {demandas.map((demanda) => (
              <DemandaKanbanCard
                key={demanda.id}
                demanda={demanda}
                onOpenDetails={onOpenDetails}
                arrastavel={arrastavel}
                motivoBloqueio={motivoBloqueio}
                onIniciarTrabalho={onIniciarTrabalho}
                podeIniciar={podeIniciar}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </section>
  );
}
