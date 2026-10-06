"use client";

import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { ProjetoStatus } from "@/types/projeto";

/** `arquivado` não entra aqui — arquivados têm um interruptor próprio. */
export type ProjetoStatusFiltro = Exclude<ProjetoStatus, "arquivado"> | "todos";

export function ProjetosToolbar({
  query,
  onQueryChange,
  statusFilter,
  onStatusFilterChange,
  onNewProject,
  mostrarArquivados,
  onMostrarArquivadosChange,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  statusFilter: ProjetoStatusFiltro;
  onStatusFilterChange: (value: ProjetoStatusFiltro) => void;
  onNewProject: () => void;
  mostrarArquivados: boolean;
  onMostrarArquivadosChange: (value: boolean) => void;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">Busca</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
              <input
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Buscar por projeto, cliente, campanha, responsável ou código"
                className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
              />
            </span>
          </label>

          <Select
            label="Status"
            value={statusFilter}
            onChange={(event) => onStatusFilterChange(event.target.value as ProjetoStatusFiltro)}
            options={[
              { value: "todos", label: "Todos" },
              { value: "planejamento", label: "Planejamento" },
              { value: "ativo", label: "Ativos" },
              { value: "pausado", label: "Pausados" },
              { value: "concluido", label: "Concluídos" },
            ]}
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-fg-muted">
          <input
            type="checkbox"
            checked={mostrarArquivados}
            onChange={(event) => onMostrarArquivadosChange(event.target.checked)}
            className="field-check h-4 w-4 rounded"
          />
          Ver arquivados
        </label>

        <Button onClick={onNewProject}>
          <Plus className="h-4 w-4" />
          Novo projeto
        </Button>
      </div>
    </div>
  );
}
