"use client";

import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";

export function PecasToolbar({
  query,
  onQueryChange,
  categoria,
  onCategoriaChange,
  categorias,
  onlyActive,
  onToggleOnlyActive,
  onNewPeca,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  categoria: string;
  onCategoriaChange: (value: string) => void;
  categorias: string[];
  onlyActive: boolean;
  onToggleOnlyActive: () => void;
  onNewPeca: () => void;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-4 md:grid-cols-[minmax(0,1fr)_200px_auto]">
          <label className="block text-sm">
            <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Busca</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
              <input
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Buscar por nome, categoria ou briefing"
                className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
              />
            </span>
          </label>

          <Select
            label="Categoria"
            value={categoria}
            onChange={(event) => onCategoriaChange(event.target.value)}
            options={[{ value: "", label: "Todas" }, ...categorias.map((item) => ({ value: item, label: item }))]}
          />

          <div className="flex items-end">
            <button
              type="button"
              onClick={onToggleOnlyActive}
              className={
                onlyActive
                  ? "rounded-full border border-line bg-surface px-3 py-2.5 text-xs font-medium text-zinc-600 shadow-sm dark:text-zinc-300"
                  : "bg-brand-gradient rounded-full px-3 py-2.5 text-xs font-semibold shadow-sm"
              }
            >
              {onlyActive ? "Só ativas" : "Incluindo inativas"}
            </button>
          </div>
        </div>

        <Button onClick={onNewPeca}>
          <Plus className="h-4 w-4" />
          Nova peça
        </Button>
      </div>
    </div>
  );
}
