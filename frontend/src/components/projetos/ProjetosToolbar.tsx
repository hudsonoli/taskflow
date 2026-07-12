import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { ToolbarCard } from "@/components/ui/ToolbarCard";
import type { ProjetoStatus } from "@/types/projeto";

export type ProjetoStatusFiltro = ProjetoStatus | "todos";

type ProjetosToolbarProps = {
  query: string;
  onQueryChange: (value: string) => void;
  statusFilter: ProjetoStatusFiltro;
  onStatusFilterChange: (value: ProjetoStatusFiltro) => void;
  onNewProject: () => void;
};

export function ProjetosToolbar({
  query,
  onQueryChange,
  statusFilter,
  onStatusFilterChange,
  onNewProject,
}: ProjetosToolbarProps) {
  return (
    <ToolbarCard>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-zinc-700">Busca</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <input
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Buscar por projeto, cliente, campanha, responsável ou código"
                className="w-full rounded-2xl border border-zinc-200 bg-zinc-50/70 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-zinc-300 focus:bg-white focus:shadow-sm"
              />
            </span>
          </label>

          <Select
            label="Status"
            value={statusFilter}
            onChange={(event) =>
              onStatusFilterChange(event.target.value as ProjetoStatusFiltro)
            }
            options={[
              { value: "todos", label: "Todos" },
              { value: "planejamento", label: "Planejamento" },
              { value: "ativo", label: "Ativos" },
              { value: "pausado", label: "Pausados" },
              { value: "concluido", label: "Concluídos" },
            ]}
          />
        </div>

        <Button
          onClick={onNewProject}
          className="inline-flex items-center justify-center gap-2 whitespace-nowrap"
        >
          <Plus className="h-4 w-4" />
          Novo Projeto
        </Button>
      </div>
    </ToolbarCard>
  );
}
