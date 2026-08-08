"use client";

import { ClipboardList } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatPrazo, statusDemandaLabels } from "@/lib/demandas-mock";
import { useAppData } from "@/lib/AppDataContext";
import type { DemandaStatus } from "@/types/demanda";

const statusTone: Record<DemandaStatus, BadgeTone> = {
  rascunho: "neutral",
  planejada: "blue",
  em_execucao: "green",
  pausada: "amber",
  bloqueada: "red",
  aguardando_cliente: "amber",
  concluida: "green",
  cancelada: "neutral",
};

export function ProjetoDemandasSection({ projetoId }: { projetoId: string }) {
  const { demandas: todasDemandas } = useAppData();
  const demandas = todasDemandas.filter((demanda) => demanda.projetoId === projetoId);

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          <ClipboardList className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">Demandas do projeto</h3>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">Ativas, concluídas e demais status, todas em um lugar.</p>
        </div>
      </div>

      <div className="mt-4">
        {demandas.length === 0 ? (
          <EmptyState title="Nenhuma demanda vinculada" description="As demandas criadas para este projeto vão aparecer aqui." icon={<ClipboardList size={16} />} />
        ) : (
          <ul className="flex flex-col gap-2.5">
            {demandas.map((demanda) => (
              <li
                key={demanda.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-zinc-100 bg-zinc-50/60 px-3.5 py-2.5 dark:border-zinc-800 dark:bg-zinc-950/30"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">{demanda.nome}</p>
                  <p className="text-xs text-zinc-400">
                    {demanda.codigoInterno} · prazo {formatPrazo(demanda.prazoEtapaAtual)}
                  </p>
                </div>
                <Badge tone={statusTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
