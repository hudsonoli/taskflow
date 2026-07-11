import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { WorkspaceToolbar } from "@/components/workspace/WorkspaceToolbar";
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
    <WorkspaceToolbar
      searchLabel="Busca"
      searchPlaceholder="Buscar por nome, código, projeto, cliente ou responsáveis"
      searchValue={query}
      onSearchChange={onQueryChange}
      filters={
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
      }
      actions={<Button onClick={onNewDemand}>Nova Demanda</Button>}
    />
  );
}
