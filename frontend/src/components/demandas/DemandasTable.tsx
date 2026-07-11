import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { WorkspaceEmptyState } from "@/components/workspace/WorkspaceEmptyState";
import { WorkspaceTable } from "@/components/workspace/WorkspaceTable";
import {
  prioridadeDemandaLabels,
  resolveProjetoDemandaNome,
  resolveResponsaveisProjetoNomes,
  statusDemandaLabels,
} from "@/lib/demandas-mock";
import type { Demanda } from "@/types/demanda";

type DemandasTableProps = {
  demandas: Demanda[];
  onOpenDetails: (demandaId: string) => void;
  onEdit: (demandaId: string) => void;
};

export function DemandasTable({
  demandas,
  onOpenDetails,
  onEdit,
}: DemandasTableProps) {
  if (demandas.length === 0) {
    return (
      <WorkspaceEmptyState
        title="Nenhuma demanda encontrada"
        description="Ajuste a busca ou os filtros para visualizar as demandas cadastradas."
      />
    );
  }

  return (
    <WorkspaceTable
      columns={[
        "Código",
        "Demanda",
        "Projeto",
        "Prioridade",
        "Responsáveis",
        "Status",
        "Prazo atual",
        "Ações",
      ]}
    >
      {demandas.map((demanda) => (
        <tr
          key={demanda.id}
          className="border-b border-zinc-100 transition last:border-0 hover:bg-zinc-50"
        >
          <td className="px-6 py-4 font-medium text-zinc-900">
            {demanda.codigoInterno}
          </td>
          <td className="px-6 py-4">
            <button
              type="button"
              onClick={() => onOpenDetails(demanda.id)}
              className="text-left font-medium text-zinc-900 hover:text-zinc-600"
            >
              {demanda.nome}
            </button>
          </td>
          <td className="px-6 py-4 text-zinc-500">
            {resolveProjetoDemandaNome(demanda.projetoId)}
          </td>
          <td className="px-6 py-4">
            <Badge>{prioridadeDemandaLabels[demanda.prioridade]}</Badge>
          </td>
          <td className="px-6 py-4 text-zinc-500">
            {resolveResponsaveisProjetoNomes(demanda.usuarioResponsavelIds)}
          </td>
          <td className="px-6 py-4">
            <Badge>{statusDemandaLabels[demanda.status]}</Badge>
          </td>
          <td className="px-6 py-4 text-zinc-500">
            {demanda.prazoEtapaAtual}
          </td>
          <td className="px-6 py-4">
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => onOpenDetails(demanda.id)}
              >
                Abrir detalhes
              </Button>
              <Button variant="secondary" onClick={() => onEdit(demanda.id)}>
                Editar mock
              </Button>
            </div>
          </td>
        </tr>
      ))}
    </WorkspaceTable>
  );
}
