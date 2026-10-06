"use client";

import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function DepartamentosToolbar({
  query,
  onQueryChange,
  onNewDepartamento,
  mostrarArquivados,
  onMostrarArquivadosChange,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  onNewDepartamento: () => void;
  mostrarArquivados: boolean;
  onMostrarArquivadosChange: (value: boolean) => void;
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
              placeholder="Buscar por nome ou código (D26000001)"
              className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
            />
          </span>
        </label>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => onMostrarArquivadosChange(!mostrarArquivados)}
            className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            {mostrarArquivados ? "Ver ativos" : "Ver arquivados"}
          </button>
          <Button onClick={onNewDepartamento}>
            <Plus className="h-4 w-4" />
            Novo departamento
          </Button>
        </div>
      </div>
    </div>
  );
}
