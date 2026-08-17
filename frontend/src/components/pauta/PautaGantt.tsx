"use client";

import { motion } from "framer-motion";
import clsx from "clsx";
import { EmptyState } from "@/components/ui/EmptyState";
import type { BadgeTone } from "@/components/ui/Badge";
import { compararPorAgenda, statusDemandaTone } from "@/lib/demandas";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { resolverProjetoNome } from "@/lib/referencias";
import type { Demanda } from "@/types/demanda";

const toneClassNames: Record<BadgeTone, string> = {
  neutral: "bg-zinc-400",
  blue: "bg-indigo-500",
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
};

const formatDiaCurto = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit" });

function inicioDoDia(data: Date): Date {
  const copia = new Date(data);
  copia.setHours(0, 0, 0, 0);
  return copia;
}

function listarDias(inicio: Date, fim: Date): Date[] {
  const dias: Date[] = [];
  const cursor = inicioDoDia(inicio);
  const limite = inicioDoDia(fim);
  while (cursor.getTime() <= limite.getTime()) {
    dias.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return dias.length > 0 ? dias : [inicioDoDia(inicio)];
}

/** Índice (0-based) do dia mais próximo dentro de `dias`, com clamp nas bordas do período. */
function indiceDoDia(data: Date, dias: Date[]): number {
  const alvo = inicioDoDia(data).getTime();
  const indice = dias.findIndex((dia) => dia.getTime() >= alvo);
  if (indice === -1) return dias.length - 1;
  return Math.max(0, indice);
}

export function PautaGantt({
  demandas,
  periodoInicio,
  periodoFim,
  onOpenDetails,
}: {
  demandas: Demanda[];
  periodoInicio: Date;
  periodoFim: Date;
  onOpenDetails: (demandaId: string) => void;
}) {
  const { projetos } = useDiretorioProjetos();

  if (demandas.length === 0) {
    return <EmptyState title="Nenhuma tarefa na pauta" description="Ajuste a busca ou os filtros para visualizar as tarefas do período." />;
  }

  const dias = listarDias(periodoInicio, periodoFim);
  const ordenadas = [...demandas].sort(compararPorAgenda);
  const hoje = new Date();
  const indiceHoje = hoje >= periodoInicio && hoje <= periodoFim ? indiceDoDia(hoje, dias) : null;

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="overflow-x-auto">
        <div className="min-w-[720px]">
          <div className="flex border-b border-zinc-100 dark:border-zinc-800">
            <div className="w-56 shrink-0 px-4 py-2.5 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400">Tarefa</div>
            <div className="grid flex-1" style={{ gridTemplateColumns: `repeat(${dias.length}, minmax(0, 1fr))` }}>
              {dias.map((dia, index) => (
                <div
                  key={dia.toISOString()}
                  className={clsx(
                    "border-l border-zinc-100 px-1 py-2.5 text-center text-xs font-medium text-zinc-400 dark:border-zinc-800",
                    index === indiceHoje && "bg-indigo-50/60 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400",
                  )}
                >
                  {formatDiaCurto.format(dia)}
                </div>
              ))}
            </div>
          </div>

          <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {ordenadas.map((demanda) => {
              const inicio = new Date(demanda.dataInicio ?? "");
              const fim = new Date(demanda.dataFimPrevista || demanda.prazoEtapaAtual || "");
              const inicioValido = !Number.isNaN(inicio.getTime());
              const fimValido = !Number.isNaN(fim.getTime());

              const colStart = inicioValido ? indiceDoDia(inicio, dias) + 1 : 1;
              const colEnd = fimValido ? indiceDoDia(fim, dias) + 2 : colStart + 1;

              return (
                <div key={demanda.id} className="flex items-center transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
                  <button
                    type="button"
                    onClick={() => onOpenDetails(demanda.id)}
                    className="w-56 shrink-0 px-4 py-3 text-left"
                  >
                    <span className="block truncate text-sm font-semibold text-zinc-950 transition hover:text-indigo-600 dark:text-zinc-50 dark:hover:text-indigo-400">
                      {demanda.nome}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-zinc-400">{resolverProjetoNome(demanda.projetoId, projetos)}</span>
                  </button>

                  <div
                    className="relative grid flex-1 items-center py-3"
                    style={{ gridTemplateColumns: `repeat(${dias.length}, minmax(0, 1fr))` }}
                  >
                    {indiceHoje !== null && (
                      <div
                        className="pointer-events-none absolute inset-y-0 w-px bg-indigo-400/60"
                        style={{ left: `${((indiceHoje + 0.5) / dias.length) * 100}%` }}
                      />
                    )}
                    <motion.div
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      transition={{ duration: 0.35, ease: "easeOut" }}
                      style={{ gridColumn: `${colStart} / ${colEnd}`, transformOrigin: "left" }}
                      className={clsx("h-2.5 rounded-full", toneClassNames[statusDemandaTone[demanda.status]])}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
