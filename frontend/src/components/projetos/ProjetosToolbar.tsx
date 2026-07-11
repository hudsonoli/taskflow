import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { WorkspaceToolbar } from "@/components/workspace/WorkspaceToolbar";
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
    <WorkspaceToolbar
      searchLabel="Busca"
      searchPlaceholder="Buscar por projeto, cliente, campanha, responsável ou código"
      searchValue={query}
      onSearchChange={onQueryChange}
      filters={
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
      }
      actions={<Button onClick={onNewProject}>Novo Projeto</Button>}
    />
  );
}
