import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { ToolbarCard } from "@/components/ui/ToolbarCard";
import type { DemandaStatus } from "@/types/demanda";

export type DemandaStatusFiltro =
  | DemandaStatus
  | "todos"
  | "pausadas_bloqueadas";

type DemandasToolbarProps = {
  query: string;
  onQueryChange: (value: string) => void;
  statusFilter: DemandaStatusFiltro;
  onStatusFilterChange: (value: DemandaStatusFiltro) => void;
  onNewDemand: () => void;
};

export function DemandasToolbar({
  query,
  onQueryChange,
  statusFilter,
  onStatusFilterChange,
  onNewDemand,
}: DemandasToolbarProps) {
  return (
    <ToolbarCard>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-4 md:grid-cols-[minmax(0,1fr)_240px]">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-zinc-700">Busca</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <input
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Buscar por nome, código, projeto, cliente ou responsáveis"
                className="w-full rounded-2xl border border-zinc-200 bg-zinc-50/70 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-zinc-300 focus:bg-white focus:shadow-sm"
              />
            </span>
          </label>

          <Select
            label="Status"
            value={statusFilter}
            onChange={(event) =>
              onStatusFilterChange(event.target.value as DemandaStatusFiltro)
            }
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

        <Button
          onClick={onNewDemand}
          className="inline-flex items-center justify-center gap-2 whitespace-nowrap"
        >
          <Plus className="h-4 w-4" />
          Nova Demanda
        </Button>
      </div>
    </ToolbarCard>
  );
}
