"use client";

import { AlertTriangle, CalendarDays, Lock } from "lucide-react";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  formatPrazo,
  normalizarUsuarioId,
  prioridadeDemandaLabels,
  resolveProjetoDemandaNome,
  statusDemandaLabels,
  statusDemandaTone,
} from "@/lib/demandas-mock";
import { classificarTarefa } from "@/lib/escopo-operacional";
import { resolverUsuarioPorReferencia } from "@/lib/referencias";
import type { UsuarioDiretorioItem } from "@/lib/api-backend";
import type { Cliente } from "@/types/cliente";
import type { Demanda } from "@/types/demanda";

const prioridadeClassName: Record<Demanda["prioridade"], string> = {
  alta: "border-zinc-300 bg-zinc-50 text-zinc-800 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200",
  media: "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-400",
  baixa: "border-indigo-100 bg-indigo-50 text-indigo-600 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-400",
};

/** Lista compacta de tarefas reutilizável entre Meu Departamento e Minhas Demandas. */
export function TarefasLista({
  demandas,
  usuarios,
  clientes,
  onOpenDetails,
  emptyTitle = "Nenhuma tarefa encontrada",
  emptyDescription = "Ajuste os filtros para visualizar tarefas.",
}: {
  demandas: Demanda[];
  usuarios: UsuarioDiretorioItem[];
  clientes: Cliente[];
  onOpenDetails?: (demandaId: string) => void;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  if (demandas.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="overflow-x-auto">
        <table className="min-w-[900px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
            <tr>
              {["Tarefa", "Cliente", "Projeto", "Prioridade", "Responsáveis", "Status", "Prazo"].map((coluna) => (
                <th key={coluna} className="px-4 py-2.5">
                  {coluna}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {demandas.map((demanda) => {
              const classificacao = classificarTarefa(demanda);
              const cliente = clientes.find((item) => item.id === demanda.clienteId);
              const responsaveis = demanda.usuarioResponsavelIds
                .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
                .filter((usuario): usuario is UsuarioDiretorioItem => Boolean(usuario));

              return (
                <tr key={demanda.id} className="group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => onOpenDetails?.(demanda.id)}
                      disabled={!onOpenDetails}
                      className="max-w-[240px] text-left font-semibold text-zinc-950 transition hover:text-indigo-600 disabled:cursor-default disabled:hover:text-zinc-950 dark:text-zinc-50 dark:disabled:hover:text-zinc-50 dark:hover:text-indigo-400"
                    >
                      <span className="block truncate">{demanda.nome}</span>
                      <span className="mt-0.5 block truncate text-xs font-medium text-zinc-400">{demanda.codigoInterno}</span>
                    </button>
                  </td>
                  <td className="max-w-[160px] truncate px-4 py-3 text-zinc-600 dark:text-zinc-400">{cliente?.nome ?? "Sem cliente"}</td>
                  <td className="max-w-[160px] truncate px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    {resolveProjetoDemandaNome(demanda.projetoId)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${prioridadeClassName[demanda.prioridade]}`}>
                      {prioridadeDemandaLabels[demanda.prioridade]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <AvatarStack pessoas={responsaveis} max={3} size="h-7 w-7" />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
                      {demanda.status === "bloqueada" && (
                        <span title="Tarefa bloqueada" className="text-red-500">
                          <Lock className="h-3.5 w-3.5" />
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${
                        classificacao.atrasada
                          ? "bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400"
                          : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                      }`}
                    >
                      {classificacao.atrasada ? <AlertTriangle className="h-3.5 w-3.5" /> : <CalendarDays className="h-3.5 w-3.5" />}
                      {formatPrazo(demanda.prazoEtapaAtual)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
