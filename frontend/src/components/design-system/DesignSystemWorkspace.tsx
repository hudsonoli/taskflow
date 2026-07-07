"use client";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { WorkspaceEmptyState } from "@/components/workspace/WorkspaceEmptyState";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";
import { WorkspaceStats } from "@/components/workspace/WorkspaceStats";
import { WorkspaceTable } from "@/components/workspace/WorkspaceTable";
import { WorkspaceToolbar } from "@/components/workspace/WorkspaceToolbar";

const statusOptions = [
  { value: "todos", label: "Todos" },
  { value: "ativo", label: "Ativos" },
  { value: "pausado", label: "Pausados" },
];

export function DesignSystemWorkspace() {
  return (
    <WorkspaceSection
      title="Workspace"
      description="Componentes base para páginas internas de operação."
    >
      <div className="space-y-6">
        <WorkspaceStats
          stats={[
            {
              label: "Total",
              value: "36",
              description: "Registros acompanhados",
            },
            {
              label: "Ativos",
              value: "28",
              description: "Em operação",
            },
            {
              label: "Pendentes",
              value: "8",
              description: "Aguardando ação",
            },
          ]}
        />

        <WorkspaceToolbar
          searchPlaceholder="Buscar registros"
          filters={
            <Select
              label="Status"
              defaultValue="todos"
              options={statusOptions}
            />
          }
          actions={<Button>Novo item</Button>}
        />

        <WorkspaceTable
          columns={["Nome", "Responsável", "Status", "Atualização"]}
        >
          <tr className="border-b border-zinc-100 last:border-0">
            <td className="px-6 py-4 font-medium text-zinc-900">
              Cliente ativo
            </td>
            <td className="px-6 py-4 text-zinc-500">Equipe Atendimento</td>
            <td className="px-6 py-4">
              <Badge>Ativo</Badge>
            </td>
            <td className="px-6 py-4 text-zinc-500">Hoje</td>
          </tr>

          <tr className="border-b border-zinc-100 last:border-0">
            <td className="px-6 py-4 font-medium text-zinc-900">
              Projeto em revisão
            </td>
            <td className="px-6 py-4 text-zinc-500">Equipe Operações</td>
            <td className="px-6 py-4">
              <Badge>Em revisão</Badge>
            </td>
            <td className="px-6 py-4 text-zinc-500">Ontem</td>
          </tr>
        </WorkspaceTable>

        <WorkspaceEmptyState
          title="Nenhum registro encontrado"
          description="Ajuste a busca ou os filtros para visualizar outros resultados."
        />
      </div>
    </WorkspaceSection>
  );
}
