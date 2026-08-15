"use client";

import { CalendarDays, Eye, Pencil } from "lucide-react";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatPrazo, normalizarUsuarioId, prioridadeDemandaLabels, resolveProjetoDemandaNome, statusDemandaLabels, statusDemandaTone } from "@/lib/demandas";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { resolverUsuarioPorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";
import type { Demanda, DemandaPrioridade } from "@/types/demanda";


const prioridadeClassName: Record<DemandaPrioridade, string> = {
  alta: "border-zinc-300 bg-zinc-50 text-zinc-800 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200",
  media: "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-400",
  baixa: "border-indigo-100 bg-indigo-50 text-indigo-600 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-400",
};

export function DemandasTable({
  demandas,
  onOpenDetails,
  onEdit,
}: {
  demandas: Demanda[];
  onOpenDetails: (demandaId: string) => void;
  onEdit: (demandaId: string) => void;
}) {
  const { usuarios } = useDiretorioUsuarios();

  if (demandas.length === 0) {
    return <EmptyState title="Nenhuma tarefa encontrada" description="Ajuste a busca ou os filtros." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Fila operacional</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Tarefas, prioridades, responsáveis e prazos da etapa atual.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
          {demandas.length} registro(s)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1040px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
            <tr>
              {["Código", "Tarefa", "PIT", "Projeto", "Prioridade", "Responsáveis", "Status", "Prazo atual", "Ações"].map((column) => (
                <th key={column} className="px-4 py-2.5">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {demandas.map((demanda) => {
              const responsaveis = demanda.usuarioResponsavelIds
                .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
                .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario));

              return (
                <tr key={demanda.id} className="group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
                  <td className="px-4 py-3 font-semibold text-zinc-900 dark:text-zinc-100">{rotuloDemanda(demanda)}</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => onOpenDetails(demanda.id)}
                      className="max-w-[260px] text-left font-semibold text-zinc-950 transition hover:text-indigo-600 dark:text-zinc-50 dark:hover:text-indigo-400"
                    >
                      <span className="block truncate">{demanda.nome}</span>
                      <span className="mt-0.5 block truncate text-xs font-medium text-zinc-400">{demanda.id}</span>
                    </button>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-500 dark:text-zinc-400">{demanda.pit ?? "—"}</td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{resolveProjetoDemandaNome(demanda.projetoId)}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${prioridadeClassName[demanda.prioridade]}`}>
                      {prioridadeDemandaLabels[demanda.prioridade]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <AvatarStack
                      pessoas={responsaveis.map((usuario) => ({
                        id: usuario.id,
                        nome: usuario.nome,
                        corIdentificacao: usuario.corIdentificacao,
                        fotoUrl: usuario.fotoUrl,
                      }))}
                      max={3}
                      size="h-7 w-7"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
                    {demanda.status === "aguardando_cliente" && demanda.prazoRetornoCliente && (
                      <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                        Retorno até {formatPrazo(demanda.prazoRetornoCliente)}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                      <CalendarDays className="h-3.5 w-3.5" />
                      {formatPrazo(demanda.prazoEtapaAtual)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button variant="secondary" onClick={() => onOpenDetails(demanda.id)} className="px-3 py-1.5 text-xs">
                        <Eye className="h-3.5 w-3.5" />
                        Detalhes
                      </Button>
                      <Button variant="secondary" onClick={() => onEdit(demanda.id)} className="px-3 py-1.5 text-xs">
                        <Pencil className="h-3.5 w-3.5" />
                        Editar
                      </Button>
                    </div>
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
