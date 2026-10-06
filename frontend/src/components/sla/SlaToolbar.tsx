"use client";

import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import type { SlaRegraStatus } from "@/types/sla";

export type FiltroStatus = "todos" | SlaRegraStatus;

const tabsFiltro: { id: FiltroStatus; label: string }[] = [
  { id: "todos", label: "Todos" },
  { id: "ativo", label: "Ativas" },
  { id: "inativo", label: "Inativas" },
  { id: "arquivado", label: "Arquivadas" },
];

export function SlaToolbar({
  query,
  onQueryChange,
  filtro,
  onFiltroChange,
  onNewRegra,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  filtro: FiltroStatus;
  onFiltroChange: (value: FiltroStatus) => void;
  onNewRegra: () => void;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <label className="block flex-1 text-sm sm:max-w-sm">
          <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Busca</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Buscar por nome ou descrição"
              className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
            />
          </span>
        </label>

        <Button onClick={onNewRegra}>
          <Plus className="h-4 w-4" />
          Nova regra de SLA
        </Button>
      </div>

      <div className="mt-4">
        <Tabs tabs={tabsFiltro} activeTab={filtro} onChange={(id) => onFiltroChange(id as FiltroStatus)} />
      </div>
    </div>
  );
}
