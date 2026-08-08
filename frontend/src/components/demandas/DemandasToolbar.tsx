"use client";

import { Columns3, List, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { DemandaStatus } from "@/types/demanda";

export type DemandasViewMode = "lista" | "kanban";
export type DemandaStatusFiltro = DemandaStatus | "todos" | "pausadas_bloqueadas";

export function DemandasToolbar({
  query,
  onQueryChange,
  statusFilter,
  onStatusFilterChange,
  viewMode,
  onViewModeChange,
  onNewDemand,
  podeCriar,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  statusFilter: DemandaStatusFiltro;
  onStatusFilterChange: (value: DemandaStatusFiltro) => void;
  viewMode: DemandasViewMode;
  onViewModeChange: (value: DemandasViewMode) => void;
  onNewDemand: () => void;
  podeCriar: boolean;
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
                placeholder="Buscar por nome, código, PIT, projeto, cliente ou responsáveis"
                className="w-full rounded-xl border border-zinc-200 bg-zinc-50/70 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
              />
            </span>
          </label>

          <Select
            label="Status"
            value={statusFilter}
            onChange={(event) => onStatusFilterChange(event.target.value as DemandaStatusFiltro)}
            options={[
              { value: "todos", label: "Todos" },
              { value: "em_execucao", label: "Em execução" },
              { value: "pausada", label: "Pausadas" },
              { value: "bloqueada", label: "Bloqueadas" },
              { value: "aguardando_cliente", label: "Aguardando cliente" },
              { value: "concluida", label: "Concluídas" },
            ]}
          />
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="inline-flex rounded-xl border border-zinc-200 bg-zinc-50 p-1 dark:border-zinc-700 dark:bg-zinc-800">
            {[
              { value: "lista" as const, label: "Lista", icon: List },
              { value: "kanban" as const, label: "Kanban", icon: Columns3 },
            ].map((option) => {
              const Icon = option.icon;
              const isActive = viewMode === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onViewModeChange(option.value)}
                  className={
                    isActive
                      ? "inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-zinc-950 shadow-sm dark:bg-zinc-950 dark:text-zinc-50"
                      : "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200"
                  }
                >
                  <Icon className="h-4 w-4" />
                  {option.label}
                </button>
              );
            })}
          </div>

          <Button
            onClick={onNewDemand}
            disabled={!podeCriar}
            title={podeCriar ? undefined : "Apenas Gestão, líderes de departamento (heads) e o time de Atendimento podem cadastrar tarefas."}
          >
            <Plus className="h-4 w-4" />
            Nova tarefa
          </Button>
        </div>
      </div>
    </div>
  );
}
