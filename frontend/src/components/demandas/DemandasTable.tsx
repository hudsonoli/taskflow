import { CalendarDays, Eye, Pencil } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  prioridadeDemandaLabels,
  resolveProjetoDemandaNome,
  resolveResponsaveisProjetoNomes,
  statusDemandaLabels,
} from "@/lib/demandas-mock";
import type { Demanda, DemandaPrioridade, DemandaStatus } from "@/types/demanda";

type DemandasTableProps = {
  demandas: Demanda[];
  onOpenDetails: (demandaId: string) => void;
  onEdit: (demandaId: string) => void;
};

const statusTone: Record<DemandaStatus, "neutral" | "blue" | "green" | "amber" | "red"> = {
  rascunho: "neutral",
  planejada: "blue",
  em_execucao: "green",
  pausada: "amber",
  bloqueada: "red",
  aguardando_cliente: "amber",
  concluida: "green",
  cancelada: "neutral",
};

const prioridadeClassName: Record<DemandaPrioridade, string> = {
  alta: "border-slate-300 bg-slate-50 text-slate-800",
  media: "border-sky-200 bg-sky-50 text-sky-700",
  baixa: "border-blue-100 bg-blue-50 text-blue-500",
};

function splitResolvedNames(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function CompactList({ items }: { items: string[] }) {
  const visibleItems = items.slice(0, 2);
  const extraItems = items.length - visibleItems.length;

  return (
    <div className="flex max-w-[220px] flex-wrap gap-1.5">
      {visibleItems.map((item) => (
        <span
          key={item}
          className="inline-flex max-w-[140px] items-center rounded-full bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-600"
          title={item}
        >
          <span className="truncate">{item}</span>
        </span>
      ))}
      {extraItems > 0 && (
        <span className="inline-flex items-center rounded-full bg-zinc-900 px-2 py-1 text-xs font-semibold text-white">
          +{extraItems}
        </span>
      )}
    </div>
  );
}

export function DemandasTable({
  demandas,
  onOpenDetails,
  onEdit,
}: DemandasTableProps) {
  if (demandas.length === 0) {
    return (
      <EmptyStateIllustration
        title="Nenhuma demanda encontrada"
        description="Ajuste a busca ou os filtros para visualizar as demandas cadastradas."
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-zinc-100 bg-white shadow-sm">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950">Fila operacional</h2>
          <p className="text-sm text-zinc-500">Demandas, prioridades, responsáveis e prazos da etapa atual.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
          {demandas.length} registro(s)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1040px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400">
            <tr>
              {[
                "Código",
                "Demanda",
                "Projeto",
                "Prioridade",
                "Responsáveis",
                "Status",
                "Prazo atual",
                "Ações",
              ].map((column) => (
                <th key={column} className="px-4 py-2.5">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {demandas.map((demanda) => {
              const responsaveis = splitResolvedNames(
                resolveResponsaveisProjetoNomes(demanda.usuarioResponsavelIds)
              );

              return (
                <tr
                  key={demanda.id}
                  className="group transition hover:bg-blue-50/30"
                >
                  <td className="px-4 py-3 font-semibold text-zinc-900">
                    {demanda.codigoInterno}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => onOpenDetails(demanda.id)}
                      className="max-w-[260px] text-left font-semibold text-zinc-950 transition hover:text-blue-700"
                    >
                      <span className="block truncate">{demanda.nome}</span>
                      <span className="mt-0.5 block truncate text-xs font-medium text-zinc-400">
                        {demanda.id}
                      </span>
                    </button>
                  </td>
                  <td className="px-4 py-3 text-zinc-600">
                    {resolveProjetoDemandaNome(demanda.projetoId)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${prioridadeClassName[demanda.prioridade]}`}
                    >
                      {prioridadeDemandaLabels[demanda.prioridade]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <CompactList items={responsaveis} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusPill tone={statusTone[demanda.status]}>
                      {statusDemandaLabels[demanda.status]}
                    </StatusPill>
                  </td>
                  <td className="px-4 py-3 text-zinc-600">
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-600">
                      <CalendarDays className="h-3.5 w-3.5" />
                      {demanda.prazoEtapaAtual}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => onOpenDetails(demanda.id)}
                      >
                        <Eye className="h-3.5 w-3.5" />
                        Abrir detalhes
                      </Button>
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => onEdit(demanda.id)}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Editar mock
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
