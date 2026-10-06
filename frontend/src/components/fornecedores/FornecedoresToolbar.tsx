"use client";

import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { FornecedorStatus } from "@/types/fornecedor";

/** `arquivado` não entra aqui — arquivados têm um interruptor próprio. */
export type FornecedorStatusFiltro = Exclude<FornecedorStatus, "arquivado"> | "todos";

export function FornecedoresToolbar({
  query,
  onQueryChange,
  statusFilter,
  onStatusFilterChange,
  onNewFornecedor,
  mostrarArquivados,
  onMostrarArquivadosChange,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  statusFilter: FornecedorStatusFiltro;
  onStatusFilterChange: (value: FornecedorStatusFiltro) => void;
  onNewFornecedor: () => void;
  mostrarArquivados: boolean;
  onMostrarArquivadosChange: (value: boolean) => void;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-4 md:grid-cols-[minmax(0,1fr)_200px]">
          <label className="block text-sm">
            <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Busca</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
              <input
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Buscar por nome, documento ou código (F26000001)"
                className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
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

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-fg-muted">
            <input
              type="checkbox"
              checked={mostrarArquivados}
              onChange={(event) => onMostrarArquivadosChange(event.target.checked)}
              className="field-check h-4 w-4 rounded"
            />
            Ver arquivados
          </label>

          <Button onClick={onNewFornecedor}>
            <Plus className="h-4 w-4" />
            Novo fornecedor
          </Button>
        </div>
      </div>
    </div>
  );
}
