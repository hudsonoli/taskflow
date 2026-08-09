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
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">Busca</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <input
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Buscar por projeto, cliente, campanha, responsável ou código"
                className="w-full rounded-xl border border-zinc-200 bg-zinc-50/70 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
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

        <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
          <input
            type="checkbox"
            checked={mostrarArquivados}
            onChange={(event) => onMostrarArquivadosChange(event.target.checked)}
            className="h-4 w-4 rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500 dark:border-zinc-600 dark:bg-zinc-800"
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
