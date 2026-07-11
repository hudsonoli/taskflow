import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { WorkspaceEmptyState } from "@/components/workspace/WorkspaceEmptyState";
import { WorkspaceTable } from "@/components/workspace/WorkspaceTable";
import {
  prioridadeProjetoLabels,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
  statusProjetoLabels,
} from "@/lib/projetos-mock";
import type { Projeto } from "@/types/projeto";

type ProjetosTableProps = {
  projetos: Projeto[];
  onOpenDetails: (projetoId: string) => void;
  onEdit: (projetoId: string) => void;
};

export function ProjetosTable({
  projetos,
  onOpenDetails,
  onEdit,
}: ProjetosTableProps) {
  if (projetos.length === 0) {
    return (
      <WorkspaceEmptyState
        title="Nenhum projeto encontrado"
        description="Ajuste a busca ou os filtros para visualizar os projetos cadastrados."
      />
    );
  }

  return (
    <WorkspaceTable
      columns={[
        "Código",
        "Projeto",
        "Cliente",
        "Campanha",
        "Responsáveis",
        "Departamentos",
        "Status",
        "Prioridade",
        "Prazo",
        "Ações",
      ]}
    >
      {projetos.map((projeto) => (
        <tr
          key={projeto.id}
          className="border-b border-zinc-100 transition last:border-0 hover:bg-zinc-50"
        >
          <td className="px-6 py-4 font-medium text-zinc-900">
            {projeto.codigoInterno}
          </td>
          <td className="px-6 py-4">
            <button
              type="button"
              onClick={() => onOpenDetails(projeto.id)}
              className="text-left font-medium text-zinc-900 hover:text-zinc-600"
            >
              {projeto.nome}
            </button>
          </td>
          <td className="px-6 py-4 text-zinc-500">
            {resolveClienteProjetoNome(projeto.clienteId)}
          </td>
          <td className="px-6 py-4 text-zinc-500">{projeto.campanha}</td>
          <td className="px-6 py-4 text-zinc-500">
            {resolveResponsaveisProjetoNomes(projeto.responsavelIds)}
          </td>
          <td className="px-6 py-4 text-zinc-500">
            {resolveDepartamentosProjetoNomes(
              projeto.departamentoResponsavelIds
            )}
          </td>
          <td className="px-6 py-4">
            <Badge>{statusProjetoLabels[projeto.status]}</Badge>
          </td>
          <td className="px-6 py-4">
            <Badge>{prioridadeProjetoLabels[projeto.prioridade]}</Badge>
          </td>
          <td className="px-6 py-4 text-zinc-500">
            {projeto.dataFimPrevista}
          </td>
          <td className="px-6 py-4">
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => onOpenDetails(projeto.id)}
              >
                Abrir detalhes
              </Button>
              <Button variant="secondary" onClick={() => onEdit(projeto.id)}>
                Editar mock
              </Button>
            </div>
          </td>
        </tr>
      ))}
    </WorkspaceTable>
  );
}
