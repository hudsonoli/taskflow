"use client";

import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { FornecedorStatus } from "@/types/fornecedor";

export type FornecedorStatusFiltro = FornecedorStatus | "todos";

export function FornecedoresToolbar({
  query,
  onQueryChange,
  statusFilter,
  onStatusFilterChange,
  onNewFornecedor,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  statusFilter: FornecedorStatusFiltro;
  onStatusFilterChange: (value: FornecedorStatusFiltro) => void;
  onNewFornecedor: () => void;
}) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-4 md:grid-cols-[minmax(0,1fr)_200px]">
          <label className="block text-sm">
            <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">Busca</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <input
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Buscar por nome, categoria, documento ou cidade"
                className="w-full rounded-xl border border-zinc-200/80 bg-zinc-50/70 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
              />
            </span>
          </label>

          <Select
            label="Status"
            value={statusFilter}
            onChange={(event) => onStatusFilterChange(event.target.value as FornecedorStatusFiltro)}
            options={[
              { value: "todos", label: "Todos" },
              { value: "ativo", label: "Ativos" },
              { value: "inativo", label: "Inativos" },
            ]}
          />
        </div>

        <Button onClick={onNewFornecedor}>
          <Plus className="h-4 w-4" />
          Novo fornecedor
        </Button>
      </div>
    </div>
  );
}
