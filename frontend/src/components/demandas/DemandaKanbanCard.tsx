import { CalendarDays } from "lucide-react";
import {
  prioridadeDemandaLabels,
  resolveProjetoDemandaNome,
  resolveResponsaveisProjetoNomes,
} from "@/lib/demandas-mock";
import type { Demanda, DemandaPrioridade } from "@/types/demanda";

type DemandaKanbanCardProps = {
  demanda: Demanda;
  onOpenDetails: (demandaId: string) => void;
};

const prioridadeClassNames: Record<DemandaPrioridade, string> = {
  alta: "border-slate-300 bg-slate-50 text-slate-800",
  media: "border-sky-200 bg-sky-50 text-sky-700",
  baixa: "border-blue-100 bg-blue-50 text-blue-500",
};

const prioridadeBorderClassNames: Record<DemandaPrioridade, string> = {
  alta: "border-l-slate-800",
  media: "border-l-sky-400",
  baixa: "border-l-blue-200",
};

function splitResolvedNames(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function CompactResponsaveis({ items }: { items: string[] }) {
  const visibleItems = items.slice(0, 2);
  const extraItems = items.length - visibleItems.length;

  if (items.length === 0) {
    return <span className="text-xs font-medium text-zinc-400">Sem responsável</span>;
  }

  return (
    <div className="flex min-w-0 flex-wrap gap-1.5">
      {visibleItems.map((item) => (
        <span
          key={item}
          title={item}
          className="inline-flex max-w-[118px] items-center rounded-full bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-600"
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

export function DemandaKanbanCard({
  demanda,
  onOpenDetails,
}: DemandaKanbanCardProps) {
  const responsaveis = splitResolvedNames(
    resolveResponsaveisProjetoNomes(demanda.usuarioResponsavelIds)
  );

  return (
    <button
      type="button"
      onClick={() => onOpenDetails(demanda.id)}
      className={`group w-full rounded-2xl border border-l-4 border-zinc-100 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-zinc-200 hover:shadow-md ${prioridadeBorderClassNames[demanda.prioridade]}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
            {demanda.codigoInterno}
          </span>
          <h3 className="mt-1 line-clamp-2 text-sm font-semibold leading-5 text-zinc-950 transition group-hover:text-blue-700">
            {demanda.nome}
          </h3>
        </div>

        <span
          className={`shrink-0 rounded-full border px-2 py-1 text-xs font-semibold ${prioridadeClassNames[demanda.prioridade]}`}
        >
          {prioridadeDemandaLabels[demanda.prioridade]}
        </span>
      </div>

      <p className="mt-3 truncate text-xs font-medium text-zinc-500">
        {resolveProjetoDemandaNome(demanda.projetoId)}
      </p>

      <div className="mt-4 flex items-center justify-between gap-3">
        <CompactResponsaveis items={responsaveis} />

        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-semibold text-zinc-600">
          <CalendarDays className="h-3.5 w-3.5" />
          {demanda.prazoEtapaAtual}
        </span>
      </div>
    </button>
  );
}
